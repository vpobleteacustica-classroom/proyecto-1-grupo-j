## Instalación

### Requisitos Previos

- Python 3.8 o superior
- Micrófono conectado y configurado
- Sistema operativo: Linux, Windows o macOS

### Instalación de Dependencias

```bash
# Clonar o descargar el repositorio
cd hito2

# Crear entorno virtual (recomendado)
python -m venv .venv

# Activar entorno virtual
# En Linux/macOS:
source .venv/bin/activate
# En Windows:
.venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### Dependencias Principales

```
PyQt6==6.10.0          # Interfaz gráfica
numpy==2.3.4           # Procesamiento numérico
scipy==1.16.3          # Filtros digitales
sounddevice==0.5.3     # Captura de audio
```

## Uso

### Ejecución Básica

```bash
python main.py
```
