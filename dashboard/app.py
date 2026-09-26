"""Dashboard de ocupación del espectro 840-860 MHz en Medellín (Streamlit).

Solo lee artefactos curados y mapas HTML ya generados por el pipeline. No importa ni reimplementa
la lógica de calidad, imputación o indicadores (Principio V, FR-019).
"""

import json
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# La raíz del repo se agrega al path para leer únicamente las rutas y el umbral de config
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from espectro import config  # noqa: E402

st.set_page_config(page_title="Espectro 840-860 MHz — Medellín", page_icon="📡", layout="wide")


def _faltante(ruta: Path) -> None:
    st.error(f"Falta artefacto: {ruta}. Ejecute python -m espectro.pipeline")
    st.stop()


@st.cache_data(ttl=60)
def _csv(ruta: str) -> pd.DataFrame:
    return pd.read_csv(ruta, dtype={"id_captura": str})


@st.cache_data(ttl=60)
def _json(ruta: str) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(ttl=60)
def _html(ruta: str) -> str:
    return Path(ruta).read_text(encoding="utf-8")


def cargar(ruta: Path):
    """Carga un artefacto según su extensión; si no existe, muestra el error y detiene la app."""
    if not ruta.exists():
        _faltante(ruta)
    return {".csv": _csv, ".json": _json, ".html": _html}[ruta.suffix](str(ruta))


ind = cargar(config.DIR_INDICADORES / "indicadores_canal.csv")
rec = cargar(config.DIR_INDICADORES / "recomendacion.csv")
ext = cargar(config.DIR_INDICADORES / "frecuencias_extremas.json")
umbral = config.UMBRAL_CONTAMINACION_DBM

# --- Encabezado: la decisión ---
st.title("Ocupación del espectro 840-860 MHz — Medellín")
st.caption(f"Umbral de contaminación: {umbral:.0f} dBm (potencia media del canal por Parseval). "
           "Datos: 61 capturas de una estación móvil de monitoreo.")

columnas = st.columns(4)
for col, r in zip(columnas, ind.itertuples()):
    if pd.isna(r.potencia_media_dbm):
        col.metric(f"Canal {r.canal} ({r.f_ini_mhz:.0f}-{r.f_fin_mhz:.0f} MHz)", "sin datos", "INDETERMINADO",
                   delta_color="off")
    else:
        col.metric(f"Canal {r.canal} ({r.f_ini_mhz:.0f}-{r.f_fin_mhz:.0f} MHz)", f"{r.potencia_media_dbm:.1f} dBm",
                   f"{r.potencia_media_dbm - umbral:+.1f} dB vs umbral · {r.estado.upper()}",
                   delta_color="inverse")

con_datos = ind.dropna(subset=["potencia_media_dbm"])
if not con_datos.empty:
    peor = con_datos.loc[con_datos["potencia_media_dbm"].idxmax()]
    mejor = con_datos.loc[con_datos["potencia_media_dbm"].idxmin()]
    fm, fl = ext["mas_contaminada"], ext["menos_contaminada"]
    st.markdown(
        f"**Canal más contaminado:** {peor.canal} ({peor.potencia_media_dbm:.1f} dBm) · "
        f"**Canal menos contaminado:** {mejor.canal} ({mejor.potencia_media_dbm:.1f} dBm)  \n"
        f"**Frecuencia más contaminada:** {fm['frecuencia_mhz']:.3f} MHz ({fm['potencia_dbm']:.1f} dBm) · "
        f"**Frecuencia menos contaminada:** {fl['frecuencia_mhz']:.3f} MHz ({fl['potencia_dbm']:.1f} dBm)")

st.subheader("Recomendación de bandas")
tabla = rec[["canal", "recomendacion", "estado", "indicador_base"]].rename(columns={
    "canal": "Canal", "recomendacion": "Recomendación", "estado": "Estado frente al umbral",
    "indicador_base": "Potencia media (dBm)"})
st.dataframe(tabla, hide_index=True, use_container_width=True)
st.caption("Regla relativa: se recomiendan los 2 canales de menor potencia media y se evitan los 2 de mayor, "
           "aunque los cuatro superen el umbral. El estado absoluto se muestra al lado.")

url_reporte = os.environ.get("ESPECTRO_URL_REPORTE")
if url_reporte:
    st.markdown(f"📄 [Informe técnico completo y mapas (copia estática en S3)]({url_reporte})")

with st.expander("Calidad de datos y Nyquist"):
    resumen = cargar(config.DIR_CALIDAD / "resumen_imputacion.json")
    reporte = cargar(config.DIR_CALIDAD / "reporte_calidad.csv")
    nyq = cargar(config.DIR_INDICADORES / "nyquist.json")
    st.markdown(f"- Valores corregidos: **{resumen['total_corregidos']}** · valores imputados: "
                f"**{resumen['total_imputados']}** (solo interpolación lineal)")
    st.markdown("- Capturas por disposición: " + ", ".join(
        f"{k}: {v}" for k, v in resumen["n_por_disposicion"].items()))
    descartadas = reporte[reporte["disposicion"] == "descartado"][["id_captura", "alcance", "motivo"]]
    if not descartadas.empty:
        st.dataframe(descartadas, hide_index=True, use_container_width=True)
    veredicto = "CUMPLE" if nyq["veredicto"] == "cumple" else "NO CUMPLE"
    st.markdown(f"- **Nyquist:** {veredicto}" + (" (exactamente en el límite)" if nyq["en_el_limite"] else "")
                + f" — f_s = {nyq['fs_hz'] / 1e6:.0f} MS/s, f_max = {nyq['f_max_hz'] / 1e6:.0f} MHz. "
                + nyq["implicaciones"])

# --- Mapas ---
st.subheader("Mapas interactivos")
pestanas = [
    ("Ubicaciones", "ubicaciones.html"),
    ("Ruta", "ruta.html"),
    ("Canal A", "canal_A.html"),
    ("Canal B", "canal_B.html"),
    ("Canal C", "canal_C.html"),
    ("Canal D", "canal_D.html"),
    ("Temperatura", "temperatura.html"),
    ("Frecuencia más contaminada", "frecuencia_mas_contaminada.html"),
    ("Fuentes (estimación)", config.MAPA_FUENTES),
]
for tab, (_, archivo) in zip(st.tabs([t for t, _ in pestanas]), pestanas):
    with tab:
        components.html(cargar(config.DIR_MAPAS / archivo), height=560)
        if archivo == config.MAPA_FUENTES:
            fuentes = cargar(config.DIR_INDICADORES / "fuentes_estimadas.csv")
            st.caption("Estimaciones, no mediciones: centroide de posiciones ponderado por potencia lineal "
                       "(cuartil superior); radio del círculo = incertidumbre.")
            st.dataframe(fuentes[["canal", "estado", "latitud", "longitud", "incertidumbre_m", "motivo"]],
                         hide_index=True, use_container_width=True)
