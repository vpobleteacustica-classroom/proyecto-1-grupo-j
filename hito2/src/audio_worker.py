import queue
import sys
import threading

import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from scipy.signal import sosfilt, sosfilt_zi
from src.audio_utils import create_dba_filter


class AudioWorker(QObject):
    """
    Motor de audio optimizado con buffer thread-safe.
    El callback de audio es ultra-rápido (solo pone datos en cola).
    Un timer de Qt procesa los datos de forma segura.
    """

    # --- Señales ---
    new_measurement_dba = pyqtSignal(float)
    error_signal = pyqtSignal(str)
    finished = pyqtSignal()

    # --- Configuración Optimizada ---
    SAMPLE_RATE = 44100
    BLOCK_SIZE = 4096
    CALIBRATION_OFFSET_DB = 105.0
    UPDATE_INTERVAL_MS = 100
    QUEUE_MAX_SIZE = 100
    SILENCE_THRESHOLD_DB = -60
    TIME_WEIGHTING_FAST = 0.125
    TIME_WEIGHTING_SLOW = 1.0
    TIME_WEIGHTING_IMPULSE = 0.035

    # Configuración por defecto: Fast (recomendado para mediciones ambientales)
    TIME_WEIGHTING = TIME_WEIGHTING_FAST

    def __init__(self):
        super().__init__()

        self._running = False
        self.device_id = None
        self.stream = None

        # Cola thread-safe para comunicación entre callback y procesamiento
        self.audio_queue = queue.Queue(maxsize=self.QUEUE_MAX_SIZE)

        # Lock para acceso seguro a variables compartidas
        self.lock = threading.Lock()

        # Crear el filtro y su estado
        self.sos_filter = create_dba_filter(self.SAMPLE_RATE)
        self.filter_state = sosfilt_zi(self.sos_filter)

        # Timer para procesamiento periódico (se iniciará en el thread correcto)
        self.process_timer = None
        self.timer_started = False

        # Contador de overflows para debug
        self.overflow_count = 0
        self.total_blocks = 0

        # Variable para mantener último valor válido
        self.last_valid_dba = None

        self.weighted_rms = 0.0

    def set_device(self, device_id):
        """Establece el dispositivo de audio a usar."""
        self.device_id = device_id

    def stop(self):
        """Detiene el worker y libera recursos."""
        print("Deteniendo worker de audio...")
        self._running = False

        # Detener timer si existe
        if self.process_timer and self.process_timer.isActive():
            self.process_timer.stop()

        # Detener y cerrar stream
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                print(f"Error al detener stream: {e}", file=sys.stderr)
            finally:
                self.stream = None

        # Limpiar cola
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

        print(
            f"Estadísticas: {self.overflow_count} overflows de {self.total_blocks} bloques"
        )

    def audio_callback(self, indata, frames, time_info, status):
        """
        Callback de audio ULTRA-RÁPIDO.
        Solo copia datos a la cola, sin procesamiento.
        Se ejecuta en thread de alta prioridad de PortAudio.
        """
        if not self._running:
            return

        self.total_blocks += 1

        # Reportar problemas (sin spam)
        if status:
            if status.input_overflow:
                self.overflow_count += 1
                # Solo reportar cada 100 overflows
                if self.overflow_count % 100 == 0:
                    print(
                        f"Overflow detectado ({self.overflow_count} total)",
                        file=sys.stderr,
                    )

        # Intentar poner datos en la cola SIN BLOQUEAR
        try:
            # Copiar solo el canal mono
            audio_data = indata[:, 0].copy()
            self.audio_queue.put_nowait(audio_data)
        except queue.Full:
            # Si la cola está llena, descartar este bloque
            # Es mejor perder un bloque que bloquear el callback
            pass

    def process_audio(self):
        """
        Procesa datos de audio de la cola.
        Se ejecuta periódicamente en el thread de Qt (seguro para señales).
        """
        if not self._running:
            return

        # Procesar todos los bloques disponibles en la cola
        blocks_processed = 0
        accumulated_chunks = []

        # Extraer múltiples bloques si están disponibles
        while blocks_processed < 10:  # Procesar hasta 10 bloques por vez
            try:
                audio_data = self.audio_queue.get_nowait()
                accumulated_chunks.append(audio_data)
                blocks_processed += 1
            except queue.Empty:
                break

        if len(accumulated_chunks) == 0:
            # No hay datos para procesar
            return

        try:
            # Concatenar todos los bloques
            audio_chunk = np.concatenate(accumulated_chunks)

            # Aplicar el filtro dBA con thread-safety
            with self.lock:
                filtered_chunk, self.filter_state = sosfilt(
                    self.sos_filter, audio_chunk, zi=self.filter_state
                )

            # Detectar clipping (sobrecarga digital)
            if np.max(np.abs(filtered_chunk)) > 0.99:
                print(
                    "⚠️  ADVERTENCIA: Clipping detectado! Reducir ganancia del micrófono",
                    file=sys.stderr,
                )

            # Calcular RMS instantáneo del bloque actual
            rms_instantaneous = np.sqrt(np.mean(filtered_chunk**2))

            # Calcular alpha basado en el tiempo real procesado
            chunk_duration = len(audio_chunk) / self.SAMPLE_RATE

            # Fórmula: alpha = 1 - exp(-T/tau)
            # donde T = duración del chunk, tau = constante de tiempo
            alpha = 1.0 - np.exp(-chunk_duration / self.TIME_WEIGHTING)

            # Aplicar filtro exponencial (como un sonómetro real)
            # weighted_rms = alpha * rms_instant + (1 - alpha) * weighted_rms_anterior
            self.weighted_rms = (
                alpha * rms_instantaneous + (1.0 - alpha) * self.weighted_rms
            )

            # Usar el valor ponderado para el cálculo de dB
            rms = self.weighted_rms

            # Evitar log de cero
            if rms < 1e-10:
                rms = 1e-10

            # Convertir RMS ponderado a dBFS
            db_val = 20 * np.log10(rms)

            # Validar resultado
            if not np.isfinite(db_val):
                # Reiniciar filtro si hay valores inválidos
                print("Valor inválido detectado, reiniciando filtro", file=sys.stderr)
                with self.lock:
                    self.filter_state = sosfilt_zi(self.sos_filter)
                # Usar último valor válido si existe, sino retornar
                if self.last_valid_dba is not None:
                    self.new_measurement_dba.emit(self.last_valid_dba)
                return

            # Aplicar offset de calibración
            dba_level = db_val + self.CALIBRATION_OFFSET_DB

            # Detectar silencio real (micrófono muteado o sin señal)
            if db_val < self.SILENCE_THRESHOLD_DB:
                # Emitir un valor muy bajo para indicar silencio/mute
                dba_level = self.CALIBRATION_OFFSET_DB + self.SILENCE_THRESHOLD_DB
                # Asegurar que no sea menor a 0
                dba_level = max(dba_level, 0.0)
                self.new_measurement_dba.emit(dba_level)
                return

            # Clamp solo el límite superior, permitir valores bajos reales
            # Rango típico: cualquier valor bajo hasta 130 dBA
            dba_level = min(dba_level, 130.0)

            # Guardar como último valor válido
            self.last_valid_dba = dba_level

            # Emitir señal de forma segura
            self.new_measurement_dba.emit(dba_level)

        except Exception as e:
            print(f"Error procesando audio: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc()

    def start_processing_timer(self):
        """
        Inicia el timer de procesamiento.
        Debe ser llamado después de que el worker esté en su thread destino.
        """
        if self.timer_started:
            return

        self.process_timer = QTimer()
        self.process_timer.timeout.connect(self.process_audio)
        self.process_timer.start(self.UPDATE_INTERVAL_MS)
        self.timer_started = True
        print(f"Timer de procesamiento iniciado ({self.UPDATE_INTERVAL_MS}ms)")

    def run(self):
        """
        Inicializa y arranca el stream de audio.
        Se ejecuta en el QThread.
        """

        # Obtener dispositivo por defecto si no se especificó
        if self.device_id is None:
            try:
                self.device_id = sd.default.device[0]
                if self.device_id == -1:
                    raise sd.PortAudioError("No hay dispositivo de entrada por defecto")
            except Exception as e:
                error_msg = f"No se pudo encontrar micrófono: {e}"
                print(error_msg, file=sys.stderr)
                self.error_signal.emit(error_msg)
                self.finished.emit()
                return

        print(f"Iniciando worker en dispositivo: {self.device_id}")

        # Información del dispositivo para debug
        try:
            device_info = sd.query_devices(self.device_id, "input")
            print(f"  Nombre: {device_info['name']}")
            print(f"  Sample rate: {device_info['default_samplerate']} Hz")
            print(f"  Canales: {device_info['max_input_channels']}")
            print(
                f"  Latencia baja: {device_info['default_low_input_latency'] * 1000:.1f} ms"
            )
            print(
                f"  Latencia alta: {device_info['default_high_input_latency'] * 1000:.1f} ms"
            )
        except Exception as e:
            print(f"No se pudo obtener info del dispositivo: {e}")

        try:
            # Reiniciar estado
            with self.lock:
                self.filter_state = sosfilt_zi(self.sos_filter)

            # Limpiar cola
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    break

            self.overflow_count = 0
            self.total_blocks = 0

            # Reiniciar ponderación temporal
            self.weighted_rms = 0.0

            # Crear stream con configuración optimizada
            self.stream = sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                blocksize=self.BLOCK_SIZE,
                device=self.device_id,
                channels=1,
                dtype="float32",
                latency="high",  # Usar latencia alta para mayor estabilidad
                callback=self.audio_callback,
            )

            # Marcar como running ANTES de iniciar el stream
            self._running = True

            # Iniciar el stream
            self.stream.start()

            print("Stream de audio iniciado correctamente.")
            print(
                f"Configuración: {self.SAMPLE_RATE} Hz, block={self.BLOCK_SIZE} samples"
            )
            print(
                f"Latencia del bloque: {self.BLOCK_SIZE / self.SAMPLE_RATE * 1000:.1f} ms"
            )

            # Iniciar el timer de procesamiento
            self.start_processing_timer()

        except sd.PortAudioError as e:
            error_msg = f"Error de PortAudio: {e}"
            print(error_msg, file=sys.stderr)
            self.error_signal.emit(error_msg)
            self.finished.emit()
        except Exception as e:
            error_msg = f"Error inesperado: {e}"
            print(error_msg, file=sys.stderr)
            import traceback

            traceback.print_exc()
            self.error_signal.emit(error_msg)
            self.finished.emit()
