# Guía de Instalación - Monitor de Ruido Acústico

## Requisitos del Sistema

### 1. Instalar PortAudio (Biblioteca de audio)

#### En Debian/Ubuntu:
```bash
sudo apt-get update
sudo apt-get install portaudio19-dev python3-pyaudio
```

#### En Fedora/RHEL/CentOS:
```bash
sudo dnf install portaudio-devel
```

#### En Arch Linux:
```bash
sudo pacman -S portaudio
```

#### En macOS (con Homebrew):
```bash
brew install portaudio
```

#### En Windows:
PortAudio se instala automáticamente con `sounddevice`.
Solo necesitas instalar los paquetes Python.

### 2. Instalar Dependencias Python

```bash
cd /home/basty/tmp/proyecto-1-grupo-j/hito2
pip install -r requirements.txt
```

O instalar manualmente:
```bash
pip install PyQt6 numpy scipy sounddevice
```

### 3. Verificar la Instalación

Ejecuta el script de prueba para verificar que PortAudio funciona:

```bash
python3 -c "import sounddevice as sd; print(sd.query_devices())"
```

Deberías ver una lista de tus dispositivos de audio.

## Ejecutar la Aplicación

```bash
python3 main.py
```

## Solución de Problemas Comunes

### Error: "PortAudio library not found"
- **Solución**: Instalar portaudio19-dev (ver arriba)

### Error: "No module named 'PyQt6'"
- **Solución**: `pip install PyQt6`

### Error: "No audio devices found"
- **Solución**: 
  - Verifica que tu micrófono esté conectado
  - En Linux, verifica permisos: `sudo usermod -a -G audio $USER`
  - Reinicia la sesión

### Error: "Permission denied" al acceder al micrófono
- **Solución en Linux**:
  ```bash
  sudo usermod -a -G audio $USER
  # Luego cerrar sesión y volver a entrar
  ```

### El nivel de dBA parece incorrecto
- **Solución**: 
  - Ajusta `CALIBRATION_OFFSET_DB` en `src/audio_worker.py` (línea ~20)
  - Usa un calibrador acústico o app de referencia para comparar

## Instalación Rápida (Debian/Ubuntu)

```bash
# 1. Instalar PortAudio
sudo apt-get update
sudo apt-get install -y portaudio19-dev python3-pip

# 2. Instalar dependencias Python
cd /home/basty/tmp/proyecto-1-grupo-j/hito2
pip install -r requirements.txt

# 3. Ejecutar
python3 main.py
```

## Dependencias Completas

- Python 3.7+
- PyQt6
- numpy
- scipy
- sounddevice
- PortAudio (biblioteca del sistema)
