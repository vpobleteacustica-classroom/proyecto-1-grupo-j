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

## Uso

### Ejecución Básica

```bash
python main.py
```

# Reporte 
Se trabajó en una interface dinámica para el usuario con el fin de que sea mas ilustrativa y comoda con la información a trabajar.

Se trabajó con librerias que permiten interpretar audio en valores RMS a dBa para entendimiento del usuario final.

1) La interface muestra en decibeles y colores al usuario que es lo que esta sucediendo en el momento.

2) Se implemento un sistema de selección de dispositivo de audio de entrada, un selector de tipo recinto y un log para las mediciones.

3) Se implemtó un sistema de clasificación de ruido segun recinto.
 
4) Las librerias que se usaron en este avance son: sounddevices, numpy, scipy, pyqt6.


Para el hito 3 esperabamos terminar por completo la interface con el siguiente puntos: 
1) Menú de selección de zona donde opera el dispositivo junto al horario
lamentablemente no se pudo agregar debido a la falta de infromación respecto al material disponible ante este tema.

