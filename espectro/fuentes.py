"""BONUS (FR-027): estimación de la ubicación de la fuente de contaminación de cada canal.

Método: centroide de las posiciones ponderado por la potencia lineal del canal, usando solo las
capturas del cuartil superior de potencia. Incertidumbre: distancia estándar ponderada (m).
Es una ESTIMACIÓN, no una medición: si la geometría de las capturas fuertes es casi una línea
(no restringe la fuente en dos dimensiones) o hay muy pocas capturas, se marca "no_soportado".
Solo se ejecuta después de que las tres compuertas pasan (lo garantiza pipeline.py).
"""

import sys

import folium
import numpy as np
import pandas as pd

from espectro import config
from espectro.utilidades import RADIO_TIERRA_M, asegurar_dir, dbm_a_mw, escribir_csv, leer_csv

METODO = "centroide ponderado por potencia lineal (cuartil superior)"
MIN_CAPTURAS_SOBRE_MEDIANA = 5
MAX_RAZON_EJES = 10.0
COLORES = {"A": "#1f77b4", "B": "#ff7f0e", "C": "#d62728", "D": "#9467bd"}
# Desplazamiento de cada etiqueta (una esquina distinta) para que no se tapen si las estimaciones coinciden
ANCLAS = {"A": (100, 26), "B": (-6, -6), "C": (100, -6), "D": (-6, 26)}


def _proyectar(lat, lon, lat0, lon0):
    """Proyección equirectangular local a metros alrededor de (lat0, lon0)."""
    x = np.radians(lon - lon0) * np.cos(np.radians(lat0)) * RADIO_TIERRA_M
    y = np.radians(lat - lat0) * RADIO_TIERRA_M
    return x, y


def _desproyectar(x, y, lat0, lon0):
    lat = lat0 + np.degrees(y / RADIO_TIERRA_M)
    lon = lon0 + np.degrees(x / (RADIO_TIERRA_M * np.cos(np.radians(lat0))))
    return lat, lon


def estimar_canal(sub: pd.DataFrame, lat0: float, lon0: float) -> dict:
    """Estimación para un canal a partir de sus potencias por captura con posición utilizable."""
    p_lin = dbm_a_mw(sub["potencia_dbm"].to_numpy())
    n_sobre_mediana = int((p_lin > np.median(p_lin)).sum())
    fuerte = p_lin >= np.quantile(p_lin, 0.75)
    w = p_lin[fuerte] / p_lin[fuerte].sum()
    x, y = _proyectar(sub["latitud"].to_numpy()[fuerte], sub["longitud"].to_numpy()[fuerte], lat0, lon0)
    cx, cy = float(np.sum(w * x)), float(np.sum(w * y))
    incert = float(np.sqrt(np.sum(w * ((x - cx) ** 2 + (y - cy) ** 2))))
    # Forma de la nube de capturas fuertes: razón entre el eje mayor y el menor (covarianza ponderada)
    cov = np.cov(np.vstack([x, y]), aweights=w) if fuerte.sum() > 2 else np.eye(2)
    autovalores = np.sort(np.linalg.eigvalsh(cov))
    razon = float(np.sqrt(autovalores[1] / autovalores[0])) if autovalores[0] > 0 else np.inf
    fila = {"estado": "estimado", "latitud": np.nan, "longitud": np.nan, "incertidumbre_m": incert,
            "metodo": METODO, "n_capturas_usadas": int(fuerte.sum()), "razon_ejes": razon, "motivo": ""}
    if n_sobre_mediana < MIN_CAPTURAS_SOBRE_MEDIANA:
        fila.update(estado="no_soportado", motivo=f"menos de {MIN_CAPTURAS_SOBRE_MEDIANA} capturas sobre la mediana")
    elif razon > MAX_RAZON_EJES:
        fila.update(estado="no_soportado",
                    motivo=f"capturas fuertes casi alineadas (razón de ejes {razon:.1f} > {MAX_RAZON_EJES:.0f})")
    else:
        fila["latitud"], fila["longitud"] = _desproyectar(cx, cy, lat0, lon0)
    return fila


def estimar_fuentes(pcc: pd.DataFrame) -> pd.DataFrame:
    df = pcc[(pcc["estado_posicion"] != "excluida") & pcc["latitud"].notna()]
    lat0, lon0 = float(df["latitud"].mean()), float(df["longitud"].mean())
    filas = []
    for canal in config.CANALES:
        sub = df[df["canal"] == canal]
        fila = {"canal": canal}
        if len(sub) < MIN_CAPTURAS_SOBRE_MEDIANA:
            fila.update(estado="no_soportado", latitud=np.nan, longitud=np.nan, incertidumbre_m=np.nan,
                        metodo=METODO, n_capturas_usadas=len(sub), razon_ejes=np.nan, motivo="capturas insuficientes")
        else:
            fila.update(estimar_canal(sub, lat0, lon0))
        filas.append(fila)
    return pd.DataFrame(filas)


def mapa_fuentes(est: pd.DataFrame, tele: pd.DataFrame) -> None:
    """Mapa con la ruta como contexto y una estimación por canal con su círculo de incertidumbre."""
    ruta = tele[tele["estado_posicion"] != "excluida"].sort_values("orden")
    m = folium.Map(location=[ruta["latitud"].mean(), ruta["longitud"].mean()], zoom_start=13,
                   tiles="OpenStreetMap", control_scale=True)
    m.fit_bounds([[ruta["latitud"].min(), ruta["longitud"].min()], [ruta["latitud"].max(), ruta["longitud"].max()]])
    folium.PolyLine(ruta[["latitud", "longitud"]].to_numpy().tolist(), color="#555", weight=3, opacity=0.6,
                    tooltip="Ruta de la estación").add_to(m)
    for r in est[est["estado"] == "estimado"].itertuples():
        texto = (f"Estimación canal {r.canal}: {METODO}; incertidumbre ±{r.incertidumbre_m:.0f} m "
                 f"({r.n_capturas_usadas} capturas)")
        folium.Circle([r.latitud, r.longitud], radius=float(r.incertidumbre_m), color=COLORES[r.canal],
                      fill=True, fill_opacity=0.12, tooltip=texto).add_to(m)
        folium.Marker([r.latitud, r.longitud], tooltip=texto,
                      icon=folium.DivIcon(icon_anchor=ANCLAS[r.canal], html=f'<div style="background:{COLORES[r.canal]};color:white;'
                                               f'border-radius:4px;padding:2px 5px;font:bold 12px sans-serif;'
                                               f'white-space:nowrap">Estimación {r.canal}</div>')).add_to(m)
    items = "".join(f'<div><span style="color:{COLORES[r.canal]};font-weight:bold">●</span> Canal {r.canal}: '
                    + (f"±{r.incertidumbre_m:.0f} m" if r.estado == "estimado" else f"no soportado ({r.motivo})")
                    + "</div>" for r in est.itertuples())
    m.get_root().html.add_child(folium.Element(
        '<div style="position:fixed;top:10px;left:50px;z-index:9999;background:white;padding:4px 8px;'
        'border:1px solid #888;border-radius:4px;font:14px sans-serif;"><b>Estimación de fuente por canal '
        '(radio = incertidumbre, m)</b></div>'
        '<div style="position:fixed;bottom:30px;left:10px;z-index:9999;background:white;padding:6px;'
        f'border:1px solid #888;border-radius:4px;font:12px sans-serif;max-width:320px">{items}'
        f'<div style="margin-top:4px">Método: {METODO}. Son estimaciones, no mediciones.</div></div>'))
    m.save(str(asegurar_dir(config.DIR_MAPAS) / config.MAPA_FUENTES))


def main() -> int:
    ruta_pcc = config.DIR_INDICADORES / "potencia_canal_captura.csv"
    ruta_tele = config.DIR_CURADO / "telemetria.csv"
    for p in (ruta_pcc, ruta_tele):
        if not p.exists():
            print(f"ERROR: Falta artefacto: {p}")
            return 1
    est = estimar_fuentes(leer_csv(ruta_pcc))
    escribir_csv(est, config.DIR_INDICADORES / "fuentes_estimadas.csv")
    mapa_fuentes(est, leer_csv(ruta_tele))
    for r in est.itertuples():
        print(f"Fuente canal {r.canal}: {r.estado}" + (f" ±{r.incertidumbre_m:.0f} m" if r.estado == "estimado"
                                                      else f" ({r.motivo})"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
