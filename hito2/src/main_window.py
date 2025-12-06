import json
import sys
from datetime import datetime

import sounddevice as sd
from PyQt6.QtCore import Qt, QThread, pyqtSlot
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from src.audio_worker import AudioWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Monitor de Ruido Acústico")
        self.resize(1200, 800)
        self.config = {}
        self.tipos_locales = {}
        self.load_config()
        self.load_tipos_locales()

        # Variables para gestión del thread
        self.thread = None
        self.worker = None

        # Variables para logging
        self.log_file_path = ""
        self.log_data = []
        self.current_local_type = None

        # Aplicar estilo global moderno
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QWidget {
                font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
                font-size: 13px;
            }
        """)

        # Configurar widget central y layout
        self.central_widget = QWidget()
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setSpacing(15)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.setCentralWidget(self.central_widget)

        # Crear selector de dispositivos de audio
        self.create_device_selector()

        # Crear selector de tipo de local
        self.create_local_type_selector()

        # Crear selector de destino de registro histórico
        self.create_log_path_selector()

        # Layout horizontal para display y clasificación
        self.display_layout = QHBoxLayout()
        self.display_layout.setSpacing(15)
        self.main_layout.addLayout(self.display_layout)

        # Crear tarjeta del medidor de dBA
        self.create_dba_display()

        # Crear panel de clasificación
        self.create_classification_panel()

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

    def load_tipos_locales(self):
        """Carga el archivo JSON con tipos de locales."""
        try:
            with open("tipos_locales.json", "r", encoding="utf-8") as f:
                self.tipos_locales = json.load(f)
            print("Tipos de locales cargados exitosamente.")
        except Exception as e:
            print(f"Advertencia: No se pudo cargar 'tipos_locales.json': {e}")
            self.tipos_locales = {"tipos_locales": [], "clasificaciones": {}}

    def create_device_selector(self):
        """Crea el selector de dispositivos de audio."""
        # Grupo contenedor con estilo moderno
        device_group = QGroupBox("Dispositivo de Audio")
        device_group.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                margin-top: 12px;
                padding: 20px 15px 15px 15px;
                font-size: 14px;
                font-weight: 600;
                color: #333;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 15px;
                top: 8px;
                padding: 0 5px;
                background-color: white;
            }
        """)

        device_layout = QHBoxLayout()
        device_layout.setSpacing(12)

        # Etiqueta
        device_label = QLabel("Micrófono:")
        device_label.setStyleSheet("""
            font-size: 13px;
            font-weight: normal;
            color: #555;
        """)
        device_layout.addWidget(device_label)

        # ComboBox para seleccionar dispositivo
        self.device_combo = QComboBox()
        self.device_combo.setStyleSheet("""
            QComboBox {
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
                font-size: 13px;
                min-height: 25px;
                color: #333;
            }
            QComboBox:hover {
                border: 1px solid #4A90E2;
                background-color: #fafafa;
            }
            QComboBox:focus {
                border: 1px solid #4A90E2;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #666;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
                selection-background-color: #4A90E2;
                selection-color: white;
                padding: 4px;
            }
        """)
        self.populate_audio_devices()
        device_layout.addWidget(self.device_combo, 1)

        # Botón para refrescar lista de dispositivos
        refresh_button = QPushButton("Refrescar")
        refresh_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
                font-size: 13px;
                font-weight: 500;
                color: #555;
            }
            QPushButton:hover {
                background-color: #f8f8f8;
                border: 1px solid #bbb;
            }
            QPushButton:pressed {
                background-color: #e8e8e8;
                border: 1px solid #999;
            }
        """)
        refresh_button.clicked.connect(self.refresh_audio_devices)
        device_layout.addWidget(refresh_button)

        # Botón para aplicar cambio de dispositivo
        apply_button = QPushButton("Cambiar Micrófono")
        apply_button.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border: none;
                border-radius: 5px;
                background-color: #4A90E2;
                color: white;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
            QPushButton:pressed {
                background-color: #2868A8;
            }
        """)
        apply_button.clicked.connect(self.change_audio_device)
        device_layout.addWidget(apply_button)

        device_group.setLayout(device_layout)
        self.main_layout.addWidget(device_group)

    def create_local_type_selector(self):
        """Crea el selector de tipo de local."""
        # Grupo contenedor con estilo moderno
        local_group = QGroupBox("Configuración de Medición")
        local_group.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                margin-top: 12px;
                padding: 20px 15px 15px 15px;
                font-size: 14px;
                font-weight: 600;
                color: #333;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 15px;
                top: 8px;
                padding: 0 5px;
                background-color: white;
            }
        """)

        local_layout = QHBoxLayout()
        local_layout.setSpacing(12)

        # Etiqueta
        local_label = QLabel("Tipo de local:")
        local_label.setStyleSheet("""
            font-size: 13px;
            font-weight: normal;
            color: #555;
        """)
        local_layout.addWidget(local_label)

        # ComboBox para seleccionar tipo de local
        self.local_type_combo = QComboBox()
        self.local_type_combo.setStyleSheet("""
            QComboBox {
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
                font-size: 13px;
                min-height: 25px;
                color: #333;
            }
            QComboBox:hover {
                border: 1px solid #4A90E2;
                background-color: #fafafa;
            }
            QComboBox:focus {
                border: 1px solid #4A90E2;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #666;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
                selection-background-color: #4A90E2;
                selection-color: white;
                padding: 4px;
            }
        """)

        # Llenar con tipos de locales
        if "tipos_locales" in self.tipos_locales:
            for local in self.tipos_locales["tipos_locales"]:
                self.local_type_combo.addItem(local["nombre"], local)

        # Conectar señal de cambio
        self.local_type_combo.currentIndexChanged.connect(self.on_local_type_changed)

        local_layout.addWidget(self.local_type_combo, 1)

        local_group.setLayout(local_layout)
        self.main_layout.addWidget(local_group)

        # Inicializar current_local_type con el primer elemento
        if self.local_type_combo.count() > 0:
            self.current_local_type = self.local_type_combo.itemData(0)
            print(f"Tipo de local inicial: {self.current_local_type['nombre']}")

    def create_log_path_selector(self):
        """Crea el selector de ruta para el log."""
        # Grupo contenedor con estilo moderno
        log_group = QGroupBox("Registro Histórico")
        log_group.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                margin-top: 12px;
                padding: 20px 15px 15px 15px;
                font-size: 14px;
                font-weight: 600;
                color: #333;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 15px;
                top: 8px;
                padding: 0 5px;
                background-color: white;
            }
        """)

        log_layout = QHBoxLayout()
        log_layout.setSpacing(12)

        # Etiqueta
        log_label = QLabel("Destino del archivo:")
        log_label.setStyleSheet("""
            font-size: 13px;
            font-weight: normal;
            color: #555;
        """)
        log_layout.addWidget(log_label)

        # Campo de texto para mostrar la ruta
        self.log_path_input = QLineEdit()
        self.log_path_input.setPlaceholderText(
            "Seleccione una ruta para guardar el log..."
        )
        self.log_path_input.setReadOnly(True)
        self.log_path_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: #f9f9f9;
                font-size: 13px;
                color: #333;
            }
            QLineEdit:focus {
                border: 1px solid #4A90E2;
            }
        """)
        log_layout.addWidget(self.log_path_input, 1)

        # Botón para seleccionar ruta
        browse_button = QPushButton("Examinar")
        browse_button.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border: none;
                border-radius: 5px;
                background-color: #5CB85C;
                color: white;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #4FA84F;
            }
            QPushButton:pressed {
                background-color: #449544;
            }
        """)
        browse_button.clicked.connect(self.select_log_path)
        log_layout.addWidget(browse_button)

        log_group.setLayout(log_layout)
        self.main_layout.addWidget(log_group)

    def create_dba_display(self):
        """Crea la tarjeta del medidor de dBA."""
        # Grupo contenedor con estilo de tarjeta moderna
        dba_card = QGroupBox("Nivel de Ruido Actual")
        dba_card.setMinimumHeight(500)
        dba_card.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                margin-top: 12px;
                padding: 20px 15px 15px 15px;
                font-size: 13px;
                font-weight: 500;
                color: #666;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 15px;
                top: 8px;
                padding: 0 8px;
                background-color: white;
            }
        """)

        dba_layout = QVBoxLayout()
        dba_layout.setContentsMargins(30, 50, 30, 50)
        dba_layout.setSpacing(0)

        # Agregar stretch arriba para centrar
        dba_layout.addStretch(1)

        # Crear la etiqueta para mostrar el valor dBA
        self.dba_label = QLabel("--", self)
        self.dba_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dba_label.setStyleSheet("""
            font-size: 240px;
            font-weight: 300;
            color: #999;
            padding: 0px;
            margin: 0px;
            letter-spacing: -6px;
        """)

        dba_layout.addWidget(self.dba_label)

        # Agregar stretch abajo para centrar
        dba_layout.addStretch(1)

        dba_card.setLayout(dba_layout)

        self.display_layout.addWidget(dba_card, 3)

    def create_classification_panel(self):
        """Crea el panel de clasificación."""
        self.classification_group = QGroupBox("Clasificación Acústica")
        self.classification_group.setMinimumHeight(500)
        self.classification_group.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                margin-top: 12px;
                padding: 20px 15px 15px 15px;
                font-size: 14px;
                font-weight: 600;
                color: #333;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 15px;
                top: 8px;
                padding: 0 5px;
                background-color: white;
            }
        """)

        classification_layout = QVBoxLayout()
        classification_layout.setContentsMargins(20, 50, 20, 50)
        classification_layout.setSpacing(15)

        # Agregar stretch arriba para centrar verticalmente
        classification_layout.addStretch(1)

        # Label para mostrar la clasificación con letra muy grande
        self.classification_label = QLabel("--")
        self.classification_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.classification_label.setStyleSheet("""
            font-size: 300px;
            font-weight: bold;
            color: #999;
            padding: 0px;
            margin: 0px;
        """)
        classification_layout.addWidget(self.classification_label)

        # Label para descripción más prominente
        self.classification_desc_label = QLabel("")
        self.classification_desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.classification_desc_label.setStyleSheet("""
            font-size: 56px;
            font-weight: 600;
            color: #666;
            padding: 0px;
            margin-top: -30px;
        """)
        self.classification_desc_label.setWordWrap(True)
        classification_layout.addWidget(self.classification_desc_label)

        # Agregar stretch abajo para centrar verticalmente
        classification_layout.addStretch(1)

        # Añadir espaciado flexible
        classification_layout.addStretch()

        self.classification_group.setLayout(classification_layout)
        self.display_layout.addWidget(self.classification_group, 2)

    def on_local_type_changed(self, index):
        """Maneja el cambio de tipo de local."""
        if index >= 0:
            self.current_local_type = self.local_type_combo.itemData(index)
            print(f"Tipo de local seleccionado: {self.current_local_type['nombre']}")

    def select_log_path(self):
        """Abre un diálogo para seleccionar la ruta del archivo de log."""
        default_filename = (
            f"log_acustico_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Seleccionar ubicación del registro histórico",
            default_filename,
            "CSV Files (*.csv);;All Files (*)",
        )

        if file_path:
            self.log_file_path = file_path
            self.log_path_input.setText(file_path)
            print(f"Ruta de log seleccionada: {file_path}")
            # Inicializar archivo de log
            self.initialize_log_file()

    def initialize_log_file(self):
        """Inicializa el archivo de log con encabezados."""
        try:
            with open(self.log_file_path, "w", encoding="utf-8") as f:
                f.write("timestamp,nivel_dba,clasificacion,tipo_local\n")
            print("Archivo de log inicializado correctamente")
        except Exception as e:
            print(f"Error al inicializar archivo de log: {e}")
            self.show_error_message(f"No se pudo crear el archivo de log: {e}")

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
        self.dba_label.setStyleSheet("""
            font-size: 60px;
            color: #FF9800;
            padding: 20px;
        """)

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
            self.dba_label.setStyleSheet("""
                font-size: 100px;
                color: #F44336;
                padding: 20px;
            """)

    def get_classification(self, dba_value):
        """Determina la clasificación según el nivel dBA y el tipo de local."""
        if not self.current_local_type:
            print(f"[DEBUG] No hay tipo de local seleccionado, dBA={dba_value}")
            return None, ""

        clasificacion_base = self.current_local_type.get("clasificacion_base", "C")

        # Obtener información de clasificaciones
        clasificaciones = self.tipos_locales.get("clasificaciones", {})

        # Determinar clasificación basada en el nivel
        if dba_value <= clasificaciones.get("A", {}).get("nivel_max", 90):
            clasificacion = "A"
            descripcion = clasificaciones.get("A", {}).get("descripcion", "Tranquilo")
        elif dba_value <= clasificaciones.get("B", {}).get("nivel_max", 100):
            clasificacion = "B"
            descripcion = clasificaciones.get("B", {}).get("descripcion", "Ruidoso")
        else:
            clasificacion = "C"
            descripcion = clasificaciones.get("C", {}).get("descripcion", "Muy ruidoso")

        print(
            f"[DEBUG] dBA={dba_value:.1f} -> Clasificación={clasificacion} ({descripcion})"
        )
        return clasificacion, descripcion

    @pyqtSlot(float)
    def update_dba_label(self, dba_value):
        """Actualiza la etiqueta con el nuevo valor dBA."""
        # Formatear el valor a 1 decimal
        self.dba_label.setText(f"{dba_value:.1f} dBA")

        # Obtener clasificación
        clasificacion, descripcion = self.get_classification(dba_value)

        # Usar los mismos colores que la clasificación
        if clasificacion:
            clasificaciones = self.tipos_locales.get("clasificaciones", {})
            color = clasificaciones.get(clasificacion, {}).get("color", "#999")
        else:
            # Si no hay clasificación, usar gris
            color = "#999"

        self.dba_label.setStyleSheet(f"""
            font-size: 240px;
            font-weight: 300;
            color: {color};
            padding: 0px;
            margin: 0px;
            letter-spacing: -6px;
        """)

        # Actualizar clasificación
        if clasificacion:
            self.update_classification_display(clasificacion, descripcion)

            # Registrar en log si está configurado
            if self.log_file_path:
                self.log_measurement(dba_value, clasificacion)

    def update_classification_display(self, clasificacion, descripcion):
        """Actualiza el panel de clasificación."""
        self.classification_label.setText(clasificacion)
        self.classification_desc_label.setText(descripcion)

        # Obtener color de la clasificación
        clasificaciones = self.tipos_locales.get("clasificaciones", {})
        color = clasificaciones.get(clasificacion, {}).get("color", "#666")

        self.classification_label.setStyleSheet(f"""
            font-size: 300px;
            font-weight: bold;
            color: {color};
            padding: 0px;
            margin: 0px;
        """)
        self.classification_desc_label.setStyleSheet(f"""
            font-size: 56px;
            font-weight: 600;
            color: {color};
            padding: 0px;
            margin-top: -30px;
            padding: 10px;
        """)

    def log_measurement(self, dba_value, clasificacion):
        """Registra una medición en el archivo de log."""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            tipo_local = (
                self.current_local_type["nombre"]
                if self.current_local_type
                else "No especificado"
            )

            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(f"{timestamp},{dba_value:.1f},{clasificacion},{tipo_local}\n")
        except Exception as e:
            print(f"Error al escribir en el log: {e}")

    @pyqtSlot(str)
    def show_audio_error(self, error_message):
        """Muestra un mensaje de error si el hilo de audio falla."""
        print(f"Error de audio: {error_message}")
        self.dba_label.setText("ERROR AUDIO")
        self.dba_label.setStyleSheet("""
            font-size: 80px;
            color: #F44336;
            padding: 20px;
        """)
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
