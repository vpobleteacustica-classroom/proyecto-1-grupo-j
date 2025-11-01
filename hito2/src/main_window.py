import sys
import json
import sounddevice as sd
from PyQt6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QLabel,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QPushButton,
)
from PyQt6.QtCore import QThread, pyqtSlot, Qt

from src.audio_worker import AudioWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TRABAJO ACUS220")
        self.resize(800, 600)
        self.config = {}
        self.load_config()

        # Variables para gestión del thread
        self.thread = None
        self.worker = None

        # Configurar widget central y layout
        self.central_widget = QWidget()
        self.main_layout = QVBoxLayout(self.central_widget)
        self.setCentralWidget(self.central_widget)

        # Crear selector de dispositivos de audio
        self.create_device_selector()

        # Crear la etiqueta para mostrar el valor dBA
        self.dba_label = QLabel("Iniciando...", self)
        self.dba_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dba_label.setStyleSheet("""
            font-size: 100px;
            font-weight: bold;
            color: #33A;
        """)
        self.main_layout.addWidget(self.dba_label)

        # Inicializar el hilo de audio
        self.setup_audio_thread()

    def load_config(self):
        """Carga el archivo JSON de configuración."""
        try:
            with open("config_zonas.json", "r", encoding="utf-8") as f:
                self.config = json.load(f)
            print("Configuración cargada exitosamente.")
        except Exception as e:
            print(f"Advertencia: No se pudo cargar 'config_zonas.json': {e}")
            # Configuración por defecto
            self.config = {
                "zonas_ds38": {},
                "horarios": {"inicio_diurno": "07:00", "inicio_nocturno": "21:00"},
            }

    def create_device_selector(self):
        """Crea el selector de dispositivos de audio."""
        # Layout horizontal para el selector
        device_layout = QHBoxLayout()

        # Etiqueta
        device_label = QLabel("Micrófono:")
        device_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        device_layout.addWidget(device_label)

        # ComboBox para seleccionar dispositivo
        self.device_combo = QComboBox()
        self.device_combo.setStyleSheet("font-size: 12px; padding: 5px;")
        self.populate_audio_devices()
        device_layout.addWidget(self.device_combo, 1)  # stretch factor 1

        # Botón para refrescar lista de dispositivos
        refresh_button = QPushButton("Refrescar")
        refresh_button.setStyleSheet("font-size: 12px; padding: 5px;")
        refresh_button.clicked.connect(self.refresh_audio_devices)
        device_layout.addWidget(refresh_button)

        # Botón para aplicar cambio de dispositivo
        apply_button = QPushButton("Cambiar Micrófono")
        apply_button.setStyleSheet(
            "font-size: 12px; padding: 5px; background-color: #4A90E2; color: white; font-weight: bold;"
        )
        apply_button.clicked.connect(self.change_audio_device)
        device_layout.addWidget(apply_button)

        # Agregar el layout al layout principal
        self.main_layout.addLayout(device_layout)

    def populate_audio_devices(self):
        """Llena el combo box con los dispositivos de audio disponibles."""
        self.device_combo.clear()

        try:
            # Obtener todos los dispositivos
            devices = sd.query_devices()

            # Obtener el dispositivo por defecto
            default_input = sd.default.device[0]

            # Contador de dispositivos de entrada
            input_device_count = 0

            # Iterar sobre todos los dispositivos
            for i, device in enumerate(devices):
                # Solo agregar dispositivos con canales de entrada
                if device["max_input_channels"] > 0:
                    # Crear texto descriptivo
                    device_text = f"{device['name']}"

                    # Agregar información adicional si es útil
                    if i == default_input:
                        device_text += " (Por defecto)"

                    # Agregar al combo box con el ID como dato
                    self.device_combo.addItem(device_text, i)
                    input_device_count += 1

            if input_device_count == 0:
                self.device_combo.addItem("No hay dispositivos de entrada", None)
                print("Advertencia: No se encontraron dispositivos de entrada")
            else:
                print(f"Se encontraron {input_device_count} dispositivos de entrada")

                # Seleccionar el dispositivo por defecto si existe
                for idx in range(self.device_combo.count()):
                    if self.device_combo.itemData(idx) == default_input:
                        self.device_combo.setCurrentIndex(idx)
                        break

        except Exception as e:
            print(f"Error al listar dispositivos de audio: {e}")
            self.device_combo.addItem("Error al cargar dispositivos", None)

    def refresh_audio_devices(self):
        """Refresca la lista de dispositivos de audio."""
        print("Refrescando lista de dispositivos...")
        self.populate_audio_devices()

    def change_audio_device(self):
        """Cambia el dispositivo de audio del worker."""
        # Obtener el ID del dispositivo seleccionado
        device_id = self.device_combo.currentData()

        if device_id is None:
            self.show_error_message("No se puede cambiar al dispositivo seleccionado.")
            return

        print(f"Cambiando a dispositivo ID: {device_id}")

        # Detener el worker actual
        if self.worker:
            self.worker.stop()

        # Esperar a que el thread termine
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            if not self.thread.wait(2000):
                print("Advertencia: El hilo no se detuvo a tiempo")
                self.thread.terminate()
                self.thread.wait()

        # Actualizar la etiqueta
        self.dba_label.setText("Cambiando micrófono...")
        self.dba_label.setStyleSheet("font-size: 60px; color: #F90;")

        # Crear nuevo worker con el dispositivo seleccionado
        self.setup_audio_thread(device_id=device_id)

    def setup_audio_thread(self, device_id=None):
        """Crea el AudioWorker y lo mueve a un QThread."""
        try:
            # Crear el hilo
            self.thread = QThread()

            # Crear el worker
            self.worker = AudioWorker()

            # Establecer el dispositivo si se especificó
            if device_id is not None:
                self.worker.set_device(device_id)

            # Mover el worker al hilo
            self.worker.moveToThread(self.thread)

            # Conectar señales y slots
            # Cuando el hilo inicie, ejecutar el método 'run' del worker
            self.thread.started.connect(self.worker.run)

            # Cuando el worker emita señales, actualizar UI
            self.worker.new_measurement_dba.connect(self.update_dba_label)
            self.worker.error_signal.connect(self.show_audio_error)

            # Limpieza automática cuando termine
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)

            # Iniciar el hilo
            self.thread.start()
            print("Hilo de audio iniciado correctamente.")

        except Exception as e:
            error_msg = f"Error al iniciar el hilo de audio: {e}"
            print(error_msg)
            self.show_error_message(error_msg)
            self.dba_label.setText("ERROR INIT")
            self.dba_label.setStyleSheet("font-size: 100px; color: red;")

    @pyqtSlot(float)
    def update_dba_label(self, dba_value):
        """Actualiza la etiqueta con el nuevo valor dBA."""
        # Formatear el valor a 1 decimal
        self.dba_label.setText(f"{dba_value:.1f} dBA")

        # Cambiar color según nivel con rango ampliado
        if dba_value < 30:
            color = "#666"  # Gris - muy bajo/silencio
        elif dba_value < 50:
            color = "#0A0"  # Verde - muy bajo
        elif dba_value < 60:
            color = "#33A"  # Azul - bajo
        elif dba_value < 70:
            color = "#0AA"  # Cian - moderado
        elif dba_value < 80:
            color = "#F90"  # Naranja - alto
        elif dba_value < 100:
            color = "#F33"  # Rojo - muy alto
        else:
            color = "#C0F"  # Magenta - extremo/impacto

        self.dba_label.setStyleSheet(f"""
            font-size: 100px;
            font-weight: bold;
            color: {color};
        """)

    @pyqtSlot(str)
    def show_audio_error(self, error_message):
        """Muestra un mensaje de error si el hilo de audio falla."""
        print(f"Error de audio: {error_message}")
        self.dba_label.setText("ERROR AUDIO")
        self.dba_label.setStyleSheet("font-size: 80px; color: red;")
        # No mostrar diálogo para evitar spam, solo en consola

    def show_error_message(self, message):
        """Muestra un diálogo de error."""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Error")
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()

    def closeEvent(self, event):
        """Asegura que el hilo se detenga limpiamente al cerrar la ventana."""
        print("Cerrando aplicación...")

        # Detener el worker si existe
        if self.worker:
            self.worker.stop()

        # Esperar a que el hilo termine
        if self.thread and self.thread.isRunning():
            self.thread.quit()

            # Esperar un máximo de 2 segundos
            if not self.thread.wait(2000):
                print(
                    "Advertencia: El hilo de audio no se detuvo a tiempo, forzando terminación."
                )
                self.thread.terminate()
                self.thread.wait()

        print("Aplicación cerrada correctamente.")
        event.accept()
