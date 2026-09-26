"""Constantes del estudio: rutas, eje de frecuencia, canales, umbral y límites de plausibilidad.

Este módulo es la única fuente de verdad para cualquier número fijo del análisis.
"""

from pathlib import Path

import numpy as np

# --- Rutas (relativas a la raíz del repositorio, sin depender del directorio de trabajo) ---
RAIZ = Path(__file__).resolve().parents[1]
DIR_MEDIDAS = RAIZ / "medidas_2026_20"
DIR_ARTEFACTOS = RAIZ / "artefactos"
DIR_STAGING = DIR_ARTEFACTOS / "staging"
DIR_CALIDAD = DIR_ARTEFACTOS / "calidad"
DIR_CURADO = DIR_ARTEFACTOS / "curado"
DIR_INDICADORES = DIR_ARTEFACTOS / "indicadores"
DIR_FIGURAS = DIR_ARTEFACTOS / "figuras"
DIR_SITIO = DIR_ARTEFACTOS / "sitio"
DIR_MAPAS = DIR_SITIO / "mapas"
DIR_NARRATIVA = RAIZ / "reporte" / "narrativa"
DIR_PLANTILLAS = Path(__file__).resolve().parent / "plantillas"

# --- Contrato de datos del instrumento ---
N_BINS = 1024
N_CAMPOS = N_BINS + 5  # espectro + temperatura, longitud, latitud, altitud, error de distancia
CAMPOS_TELEMETRIA = ["temperatura_c", "longitud", "latitud", "altitud_m", "error_distancia"]
COLUMNAS_ESPECTRO = [f"p_{k:04d}" for k in range(N_BINS)]
PATRON_ESTUDIO = r"^\d{3}\.txt$"
N_CAPTURAS_TOTAL = 63
N_CAPTURAS_ESTUDIO = 61

# --- Adquisición: IQ complejo a 20 MS/s centrado en 850 MHz (medir_celular.py) ---
FC_HZ = 850e6
FS_HZ = 20e6
F_MAX_HZ = 10e6  # medio ancho de banda en banda base

# Eje de frecuencia: el script aplica fftshift, así que el bin 512 corresponde a fc.
FRECUENCIAS_MHZ = FC_HZ / 1e6 + (np.arange(N_BINS) - N_BINS // 2) * (FS_HZ / 1e6) / N_BINS

# Canales A-D: cuatro bloques consecutivos de 5 MHz en orden ascendente [f_ini, f_fin)
CANALES = {
    "A": (840.0, 845.0),
    "B": (845.0, 850.0),
    "C": (850.0, 855.0),
    "D": (855.0, 860.0),
}


def bins_canal(canal: str) -> np.ndarray:
    """Índices de los bins cuya frecuencia cae dentro del canal (derivados de los bordes)."""
    f_ini, f_fin = CANALES[canal]
    return np.flatnonzero((FRECUENCIAS_MHZ >= f_ini) & (FRECUENCIAS_MHZ < f_fin))


def columna_frecuencia(k: int) -> str:
    """Nombre de columna del espectro curado para el bin k (frecuencia en MHz)."""
    return f"f_{FRECUENCIAS_MHZ[k]:.6f}"


# --- Umbral de contaminación: ÚNICA definición en todo el código ---
UMBRAL_CONTAMINACION_DBM = -60.0

# --- Límites de plausibilidad (área metropolitana de Medellín y sensor interno) ---
LIMITES = {
    "lat": (6.0, 6.5),
    "lon": (-75.8, -75.4),
    "alt_m": (1300.0, 2800.0),
    "temp_c": (-10.0, 85.0),
    "dbm": (-160.0, 30.0),
    "error_dist_max": 5.0,
}

# --- Reglas de imputación (solo interpolación lineal) ---
MAX_HUECO_BINS = 2
MAX_HUECO_CAPTURAS = 1

# --- Saturación del receptor: piso de ruido (p10) sobre la mediana del estudio ---
PERCENTIL_PISO = 10
UMBRAL_SATURACION_DB = 30.0

# --- Mapas ---
MAPAS_REQUERIDOS = [
    "ubicaciones.html",
    "ruta.html",
    "canal_A.html",
    "canal_B.html",
    "canal_C.html",
    "canal_D.html",
    "temperatura.html",
    "frecuencia_mas_contaminada.html",
]
MAPA_FUENTES = "fuentes.html"

BASE_ORDENAMIENTO = "número de archivo; las capturas no tienen marca de tiempo"
