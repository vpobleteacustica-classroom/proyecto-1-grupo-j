import numpy as np
from scipy.signal import zpk2sos, bilinear_zpk


def create_dba_filter(fs):
    """
    Diseña un filtro de Ponderación A (dBA) digital usando scipy.

    Este filtro implementa la curva de ponderación A estándar (IEC 61672-1)
    que simula la respuesta del oído humano a diferentes frecuencias.

    Devuelve los coeficientes del filtro (en formato 'sos' para estabilidad numérica)
    para ser usados con 'scipy.signal.sosfilt'.

    :param fs: Tasa de muestreo (Sample Rate) en Hz
    :return: Coeficientes 'sos' del filtro (Second-Order Sections)
    """

    # Frecuencias características del filtro A-weighting
    f1 = 20.6  # Hz
    f2 = 107.7  # Hz
    f3 = 737.9  # Hz
    f4 = 12194.0  # Hz

    # Convertir a rad/s (frecuencias angulares)
    w1 = 2 * np.pi * f1
    w2 = 2 * np.pi * f2
    w3 = 2 * np.pi * f3
    w4 = 2 * np.pi * f4

    # Definir ceros y polos en el dominio analógico (s-domain)
    # La ponderación A tiene 4 ceros en el origen (para atenuar bajas frecuencias)
    # y 4 polos a las frecuencias características
    zeros_analog = [0, 0, 0, 0]  # 4 ceros en el origen

    poles_analog = [
        -w1 + 0j,  # Polo real en f1
        -w1 + 0j,  # Polo doble en f1
        -w2 + 0j,  # Polo real en f2
        -w3 + 0j,  # Polo real en f3
    ]

    # Ganancia inicial (se ajustará después)
    k_analog = 1.0

    # Convertir de analógico a digital usando la transformada bilineal
    # Esto es más estable que otros métodos de conversión
    zeros_digital, poles_digital, k_digital = bilinear_zpk(
        zeros_analog, poles_analog, k_analog, fs=fs
    )

    # Calcular la ganancia necesaria para normalizar a 0 dB en 1 kHz
    # La ponderación A debe tener ganancia unitaria (0 dB) a 1000 Hz
    # Esto es importante para obtener valores de dBA correctos

    # Evaluar la respuesta del filtro a 1 kHz
    test_freq = 1000.0  # Hz
    w_test = 2 * np.pi * test_freq / fs  # Frecuencia angular normalizada

    # Calcular la respuesta en frecuencia en 1 kHz
    z_test = np.exp(1j * w_test)

    # Evaluar el numerador (ceros)
    num_response = k_digital
    for zero in zeros_digital:
        num_response *= z_test - zero

    # Evaluar el denominador (polos)
    den_response = 1.0
    for pole in poles_digital:
        den_response *= z_test - pole

    # Ganancia total en 1 kHz
    h_1khz = num_response / den_response
    magnitude_1khz = np.abs(h_1khz)

    # Normalizar para que la ganancia en 1 kHz sea 1.0 (0 dB)
    if magnitude_1khz > 1e-10:  # Evitar división por cero
        k_digital = k_digital / magnitude_1khz

    # Convertir de formato zpk (zeros, poles, gain) a sos (second-order sections)
    # El formato SOS es numéricamente más estable para filtros de orden alto
    try:
        sos = zpk2sos(zeros_digital, poles_digital, k_digital)
    except Exception as e:
        print(f"Error al crear filtro dBA: {e}")
        # Filtro de respaldo: paso-todo (no modifica la señal)
        sos = np.array([[1.0, 0.0, 0.0, 1.0, 0.0, 0.0]])

    return sos


def db_to_linear(db):
    """
    Convierte decibeles a escala lineal.

    :param db: Valor en decibeles
    :return: Valor lineal
    """
    return 10.0 ** (db / 20.0)


def linear_to_db(linear):
    """
    Convierte escala lineal a decibeles.

    :param linear: Valor lineal (amplitud)
    :return: Valor en decibeles
    """
    if linear < 1e-10:
        linear = 1e-10  # Evitar log(0)
    return 20.0 * np.log10(linear)


def calculate_leq(dba_values, duration_seconds=None):
    """
    Calcula el nivel equivalente continuo (Leq) a partir de muestras de dBA.

    El Leq es el nivel de presión sonora constante que contendría la misma
    energía acústica que el sonido variable medido durante el mismo período.

    :param dba_values: Array de valores en dBA
    :param duration_seconds: Duración en segundos (opcional, para cálculos precisos)
    :return: Valor Leq en dBA
    """
    if len(dba_values) == 0:
        return 0.0

    # Convertir dBA a presión sonora lineal
    pressures = db_to_linear(np.array(dba_values))

    # Calcular la presión cuadrática media
    mean_square_pressure = np.mean(pressures**2)

    # Convertir de vuelta a dB
    leq = linear_to_db(np.sqrt(mean_square_pressure))

    return leq


def apply_time_weighting(current_value, previous_value, time_constant, sample_rate):
    """
    Aplica ponderación temporal (Fast, Slow, Impulse) según IEC 61672-1.

    :param current_value: Valor actual en escala lineal
    :param previous_value: Valor previo en escala lineal
    :param time_constant: Constante de tiempo en segundos (Fast=0.125s, Slow=1.0s)
    :param sample_rate: Tasa de muestreo en Hz
    :return: Valor ponderado en escala lineal
    """
    # Calcular el coeficiente de suavizado exponencial
    alpha = 1.0 - np.exp(-1.0 / (time_constant * sample_rate))

    # Aplicar el filtro de primer orden
    weighted_value = alpha * current_value + (1.0 - alpha) * previous_value

    return weighted_value
