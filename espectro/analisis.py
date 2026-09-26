"""Evidencia para el informe: ruta, temperatura vs calidad, Nyquist y sensibilidad a saturación."""

import numpy as np
import pandas as pd
from scipy import stats

from espectro import config, indicadores
from espectro.utilidades import haversine_m

NIVEL_SIGNIFICANCIA = 0.05


def describir_ruta(telemetria: pd.DataFrame) -> dict:
    """Describe la ruta con las posiciones utilizables ordenadas por número de captura (FR-022)."""
    df = telemetria[telemetria["estado_posicion"] != "excluida"].sort_values("orden")
    lat, lon = df["latitud"].to_numpy(), df["longitud"].to_numpy()
    tramos = haversine_m(lat[:-1], lon[:-1], lat[1:], lon[1:])
    ini, fin = df.iloc[0], df.iloc[-1]
    return {
        "base_ordenamiento": config.BASE_ORDENAMIENTO,
        "inicio": {"id_captura": ini["id_captura"], "latitud": ini["latitud"], "longitud": ini["longitud"]},
        "fin": {"id_captura": fin["id_captura"], "latitud": fin["latitud"], "longitud": fin["longitud"]},
        "longitud_km": float(tramos.sum()) / 1000,
        "bbox": {"lat_min": lat.min(), "lat_max": lat.max(), "lon_min": lon.min(), "lon_max": lon.max()},
        "altitud_min_m": df["altitud_m"].min(),
        "altitud_max_m": df["altitud_m"].max(),
        "n_puntos": len(df),
        "n_imputados": int((df["estado_posicion"] == "imputada").sum()),
        "n_excluidos": int((telemetria["estado_posicion"] == "excluida").sum()),
        "pares_estacionarios": int((tramos == 0).sum()),
    }


def correlacion_parcial_spearman(x, y, z):
    """Spearman parcial de x e y controlando z: Pearson de los residuos de los rangos.

    Retorna (rho, p) con prueba t de n-3 grados de libertad, a dos colas.
    """
    rx, ry, rz = (stats.rankdata(v) for v in (x, y, z))

    def residuo(r):
        pendiente, intercepto = np.polyfit(rz, r, 1)
        return r - (pendiente * rz + intercepto)

    rho = float(np.corrcoef(residuo(rx), residuo(ry))[0, 1])
    n = len(rx)
    t = rho * np.sqrt((n - 3) / max(1 - rho**2, 1e-12))
    p = float(2 * stats.t.sf(abs(t), n - 3))
    return rho, p


def temperatura_vs_calidad(telemetria: pd.DataFrame, disposiciones: pd.DataFrame) -> dict:
    """Relación entre temperatura interna y piso de ruido, controlando el orden de adquisición (FR-023)."""
    util = set(disposiciones.loc[disposiciones["espectro_utilizable"], "id_captura"])
    df = telemetria[telemetria["id_captura"].isin(util)].sort_values("orden")
    temp, piso, orden = df["temperatura_c"], df["piso_ruido_dbm"], df["orden"]
    rho, p = stats.spearmanr(temp, piso)
    rho_to, p_to = stats.spearmanr(temp, orden)
    rho_po, _ = stats.spearmanr(piso, orden)
    rho_parc, p_parc = correlacion_parcial_spearman(temp, piso, orden)
    conclusion = "relación significativa" if p_parc < NIVEL_SIGNIFICANCIA else "no concluyente"
    return {
        "n": len(df),
        "variable_calidad": f"piso de ruido (percentil {config.PERCENTIL_PISO} de los 1024 bins, dBm)",
        "rho_spearman": float(rho),
        "p_spearman": float(p),
        "rho_temp_orden": float(rho_to),
        "p_temp_orden": float(p_to),
        "rho_piso_orden": float(rho_po),
        "rho_parcial_orden": rho_parc,
        "p_parcial": p_parc,
        "nivel_significancia": NIVEL_SIGNIFICANCIA,
        "conclusion": conclusion,
        "capturas_excluidas": sorted(set(telemetria["id_captura"]) - util),
        "limitacion": (
            "La temperatura sube con el orden de adquisición, así que el orden (tiempo, posición en la "
            "ruta, calentamiento del equipo) confunde cualquier relación directa; por eso se controla el "
            "orden con una correlación parcial. Aun así, una correlación no prueba causalidad: con una sola "
            "ruta no se pueden separar el efecto térmico del cambio de entorno radioeléctrico. La lectura es "
            "la temperatura interna del sensor, no la temperatura ambiente, y n es pequeño."),
    }


def verificar_nyquist() -> dict:
    """Criterio de Nyquist para el muestreo IQ complejo del receptor (FR-028). Nunca detiene el proceso."""
    cumple = config.FS_HZ >= 2 * config.F_MAX_HZ
    en_limite = bool(np.isclose(config.FS_HZ, 2 * config.F_MAX_HZ))
    implicaciones = (
        "El criterio se cumple exactamente en el límite (f_s = 2·f_max): no hay margen para la caída del "
        "filtro antialiasing. Los bins del borde inferior del canal A (cerca de 840 MHz) y del borde superior "
        "del canal D (cerca de 860 MHz) pueden estar atenuados o contener energía replegada (aliasing), por lo "
        "que las potencias de esos bordes son menos confiables que las del centro de la banda."
        if cumple else
        "El criterio NO se cumple: parte de la banda se repliega sobre sí misma y los indicadores de canal "
        "pueden mezclar energía de frecuencias distintas. Los resultados deben leerse con esa reserva."
    )
    return {"fs_hz": config.FS_HZ, "f_max_hz": config.F_MAX_HZ, "fs_minima_hz": 2 * config.F_MAX_HZ,
            "veredicto": "cumple" if cumple else "no_cumple", "en_el_limite": en_limite,
            "resolucion_khz": config.FS_HZ / config.N_BINS / 1e3, "implicaciones": implicaciones}


def sensibilidad_saturacion(staging: pd.DataFrame, disposiciones: pd.DataFrame, espectro: pd.DataFrame,
                            telemetria: pd.DataFrame) -> pd.DataFrame:
    """Compara los indicadores con y sin los espectros descartados por saturación (FR-030)."""
    motivo_sat = disposiciones["motivo"].fillna("").str.contains("saturación")
    ids_sat = disposiciones.loc[motivo_sat & ~disposiciones["espectro_utilizable"], "id_captura"].tolist()
    crudos = staging[staging["id_captura"].isin(ids_sat)]
    extra = pd.DataFrame(crudos[config.COLUMNAS_ESPECTRO].to_numpy(dtype=float),
                         columns=[config.columna_frecuencia(k) for k in range(config.N_BINS)])
    extra.insert(0, "id_captura", crudos["id_captura"].to_numpy())
    sin = indicadores.indicadores_canal(indicadores.potencia_canal_captura(espectro, telemetria))
    con = indicadores.indicadores_canal(indicadores.potencia_canal_captura(
        pd.concat([espectro, extra], ignore_index=True), telemetria))
    out = pd.DataFrame({
        "canal": sin["canal"],
        "potencia_media_dbm_sin_descartados": sin["potencia_media_dbm"],
        "potencia_media_dbm_con_descartados": con["potencia_media_dbm"],
    })
    out["delta_db"] = out["potencia_media_dbm_con_descartados"] - out["potencia_media_dbm_sin_descartados"]
    out["cambia_estado"] = sin["estado"].to_numpy() != con["estado"].to_numpy()
    out["cambia_rango"] = sin["rango"].to_numpy() != con["rango"].to_numpy()
    out["capturas_reincorporadas"] = ",".join(ids_sat)
    return out
