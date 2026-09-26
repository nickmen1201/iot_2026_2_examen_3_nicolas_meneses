"""Indicadores de ocupación por canal (Parseval), frecuencias extremas y recomendación de bandas.

Toda suma o promedio se hace en potencia lineal (mW); solo el resultado se convierte a dBm.
El umbral de contaminación se importa de config: no se define aquí.
"""

import numpy as np
import pandas as pd

from espectro import config
from espectro.config import UMBRAL_CONTAMINACION_DBM
from espectro.utilidades import dbm_a_mw, mw_a_dbm

REGLA_RECOMENDACION = "relativa: los 2 canales de menor potencia media → usar; los 2 de mayor → evitar"


def matriz_espectro(espectro: pd.DataFrame) -> np.ndarray:
    """Matriz (capturas × 1024 bins) en dBm a partir del espectro curado."""
    cols = [config.columna_frecuencia(k) for k in range(config.N_BINS)]
    return espectro[cols].to_numpy(dtype=float)


def potencia_canal_captura(espectro: pd.DataFrame, telemetria: pd.DataFrame) -> pd.DataFrame:
    """Potencia de cada canal en cada captura: suma de Parseval de la potencia lineal de sus bins."""
    m = matriz_espectro(espectro)
    filas = []
    for canal in config.CANALES:
        p_mw = dbm_a_mw(m[:, config.bins_canal(canal)]).sum(axis=1)
        p_dbm = mw_a_dbm(p_mw)
        for idc, p in zip(espectro["id_captura"], p_dbm):
            filas.append({"id_captura": idc, "canal": canal, "potencia_dbm": p,
                          "supera_umbral": bool(p > UMBRAL_CONTAMINACION_DBM)})
    pcc = pd.DataFrame(filas, columns=["id_captura", "canal", "potencia_dbm", "supera_umbral"])
    tele = telemetria[["id_captura", "latitud", "longitud", "estado_posicion"]]
    return pcc.merge(tele, on="id_captura", how="left")


def indicadores_canal(pcc: pd.DataFrame) -> pd.DataFrame:
    """Indicador por canal: media lineal (titular), mediana, % sobre umbral, estado y rango."""
    filas = []
    for canal, (f_ini, f_fin) in config.CANALES.items():
        sub = pcc[pcc["canal"] == canal]
        n = len(sub)
        fila = {"canal": canal, "f_ini_mhz": f_ini, "f_fin_mhz": f_fin, "n_capturas": n,
                "potencia_media_dbm": np.nan, "potencia_mediana_dbm": np.nan,
                "pct_capturas_sobre_umbral": np.nan, "estado": "indeterminado"}
        if n:
            media = float(mw_a_dbm(dbm_a_mw(sub["potencia_dbm"]).mean()))
            fila.update({
                "potencia_media_dbm": media,
                "potencia_mediana_dbm": float(sub["potencia_dbm"].median()),
                "pct_capturas_sobre_umbral": 100.0 * float(sub["supera_umbral"].mean()),
                "estado": "contaminado" if media > UMBRAL_CONTAMINACION_DBM else "libre",
            })
        filas.append(fila)
    ind = pd.DataFrame(filas)
    # Rango 1 = el más contaminado; los canales sin datos no reciben rango
    ind["rango"] = ind["potencia_media_dbm"].rank(ascending=False, method="first").astype("Int64")
    return ind


def potencia_por_frecuencia(espectro: pd.DataFrame) -> pd.DataFrame:
    """Potencia media (lineal → dBm) de cada bin sobre las capturas con espectro utilizable."""
    m = matriz_espectro(espectro)
    media = mw_a_dbm(dbm_a_mw(m).mean(axis=0))
    return pd.DataFrame({"bin": np.arange(config.N_BINS), "frecuencia_mhz": config.FRECUENCIAS_MHZ,
                         "potencia_media_dbm": media})


def frecuencias_extremas(ppf: pd.DataFrame) -> dict:
    """Frecuencia más y menos contaminada de todo el sistema."""
    def fila(i):
        r = ppf.iloc[i]
        return {"bin": int(r["bin"]), "frecuencia_mhz": float(r["frecuencia_mhz"]),
                "potencia_dbm": float(r["potencia_media_dbm"])}

    return {"mas_contaminada": fila(int(ppf["potencia_media_dbm"].idxmax())),
            "menos_contaminada": fila(int(ppf["potencia_media_dbm"].idxmin()))}


def recomendacion(ind: pd.DataFrame) -> pd.DataFrame:
    """Regla relativa (FR-025): la mitad menos contaminada se usa, la mitad más contaminada se evita."""
    con_datos = ind.dropna(subset=["potencia_media_dbm"]).sort_values("potencia_media_dbm")
    mitad = len(con_datos) // 2
    usar = set(con_datos["canal"].iloc[:mitad])
    filas = []
    for r in ind.itertuples():
        if pd.isna(r.potencia_media_dbm):
            rec = "sin_datos"
        else:
            rec = "usar" if r.canal in usar else "evitar"
        filas.append({"canal": r.canal, "recomendacion": rec, "estado": r.estado, "rango": r.rango,
                      "indicador_base": r.potencia_media_dbm, "regla": REGLA_RECOMENDACION})
    return pd.DataFrame(filas)
