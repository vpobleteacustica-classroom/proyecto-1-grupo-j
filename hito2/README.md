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

# Reporte 
Se trabajo en una interface dinamica para el usuario con el fin de que sea mas ilustrativa y comoda con la información a trabajar.

Se trabajo con librerias que permiten interpretar audio en valores rms a dBa para entendimiento del usuario final.

La interface muestra en decibeles y colores al usuario que es lo que esta sucediendo en el momento.

Se implemento un sistema de selección de dispositivo de audio de entrada. 

Las librerias que se usaron en este avance son: sounddevices, numpy, scipy, pyqt6. 

Para el hito 3 esperamos terminar por completo la interface con los siguientes puntos: 
1) Menú de selección de zona donde opera el dispositivo junto al horario
2) Que realice un guardado completo de la informacion recabada durante cada medicion junto con un menu para destinar el guardado de estos archivos
3) Realizar un menú para seleccionar el tipo de local en el cual se esta realizando la medición.

