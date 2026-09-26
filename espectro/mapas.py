"""Mapas Folium autocontenidos (un HTML por vista) sobre OpenStreetMap de Medellín.

Cada mapa de calor tiene dos capas con la misma escala de color: HeatMap (vista de calor) y
puntos coloreados con el valor exacto en el tooltip. La leyenda indica unidad y escala (FR-020).
Las capturas con posición excluida nunca se dibujan; las imputadas llevan borde negro punteado.
"""

import folium
import numpy as np
import pandas as pd
from branca.colormap import LinearColormap, linear
from folium import plugins

from espectro import config
from espectro.config import UMBRAL_CONTAMINACION_DBM
from espectro.utilidades import asegurar_dir, leer_csv, leer_json

COLORES_ESTADO = {"medida": "#1f77b4", "imputada": "#ff7f0e", "baja_confianza": "#9467bd"}
ETIQUETAS_ESTADO = {"medida": "posición medida", "imputada": "posición imputada (borde punteado)",
                    "baja_confianza": "posición de baja confianza (error de distancia alto)"}


def _ubicables(df: pd.DataFrame) -> pd.DataFrame:
    """Descarta las capturas sin posición utilizable (FR-021)."""
    return df[(df["estado_posicion"] != "excluida") & df["latitud"].notna()].copy()


def mapa_base(df: pd.DataFrame, titulo: str) -> folium.Map:
    """Mapa centrado en el centroide de las posiciones, con título fijo."""
    centro = [float(df["latitud"].mean()), float(df["longitud"].mean())]
    m = folium.Map(location=centro, zoom_start=13, tiles="OpenStreetMap", control_scale=True)
    # Encuadre automático para que toda la ruta quede visible
    m.fit_bounds([[float(df["latitud"].min()), float(df["longitud"].min())],
                  [float(df["latitud"].max()), float(df["longitud"].max())]])
    m.get_root().html.add_child(folium.Element(
        f'<div style="position:fixed;top:10px;left:50px;z-index:9999;background:white;padding:4px 8px;'
        f'border:1px solid #888;border-radius:4px;font:14px sans-serif;"><b>{titulo}</b></div>'))
    return m


def leyenda_imputadas(m: folium.Map) -> None:
    """Leyenda de los mapas de valores: el color es el valor; el borde punteado marca la imputación."""
    m.get_root().html.add_child(folium.Element(
        '<div style="position:fixed;bottom:30px;left:10px;z-index:9999;background:white;padding:6px;'
        'border:1px solid #888;border-radius:4px;font:12px sans-serif;"><span style="display:inline-block;'
        'width:10px;height:10px;border-radius:5px;border:2px dashed black;margin-right:5px"></span>'
        'posición imputada (interpolada entre capturas vecinas)<br>Capturas sin posición utilizable: omitidas</div>'))


def leyenda_estados(m: folium.Map, texto_extra: str = "") -> None:
    """Leyenda fija que explica cómo se distinguen las posiciones medidas, imputadas y de baja confianza."""
    items = "".join(
        f'<div><span style="display:inline-block;width:10px;height:10px;border-radius:5px;'
        f'background:{c};margin-right:5px;{"border:2px dashed black;" if e == "imputada" else ""}"></span>'
        f'{ETIQUETAS_ESTADO[e]}</div>' for e, c in COLORES_ESTADO.items())
    extra = f'<div style="margin-top:4px;max-width:260px">{texto_extra}</div>' if texto_extra else ""
    m.get_root().html.add_child(folium.Element(
        f'<div style="position:fixed;bottom:30px;left:10px;z-index:9999;background:white;padding:6px;'
        f'border:1px solid #888;border-radius:4px;font:12px sans-serif;">{items}{extra}</div>'))


def _ticks(vmin: float, vmax: float, marcar_umbral: bool) -> list[float]:
    ticks = list(np.linspace(vmin, vmax, 6))
    if marcar_umbral and vmin < UMBRAL_CONTAMINACION_DBM < vmax:
        ticks.append(UMBRAL_CONTAMINACION_DBM)
    # float nativo: branca escribe los valores tal cual en el JavaScript del mapa
    return sorted(float(round(t, 1)) for t in ticks)


def capa_valores(m, df, columna, vmin, vmax, colores, leyenda, unidad, marcar_umbral=False) -> None:
    """Agrega la capa de calor y la capa de puntos con la misma escala de color y su leyenda."""
    cmap = LinearColormap(colores, vmin=vmin, vmax=vmax, caption=leyenda,
                          tick_labels=_ticks(vmin, vmax, marcar_umbral))
    peso = ((df[columna] - vmin) / (vmax - vmin)).clip(0, 1)
    gradiente = {round(float(x), 2): cmap.rgb_hex_str(vmin + x * (vmax - vmin)) for x in np.linspace(0, 1, 6)}
    calor = folium.FeatureGroup(name="Mapa de calor")
    plugins.HeatMap(np.column_stack([df["latitud"], df["longitud"], peso]).tolist(), radius=30, blur=20,
                    min_opacity=0.3, max_zoom=14, gradient=gradiente).add_to(calor)
    calor.add_to(m)
    puntos = folium.FeatureGroup(name="Capturas (valor exacto)")
    for r in df.sort_values("id_captura").itertuples():
        v = getattr(r, columna)
        imputada = r.estado_posicion == "imputada"
        folium.CircleMarker(
            location=[r.latitud, r.longitud], radius=7, fill=True, fill_opacity=0.9,
            fill_color=cmap(v), color="black" if imputada else cmap(v), weight=2 if imputada else 1,
            dash_array="5,5" if imputada else None,
            tooltip=f"Captura {r.id_captura}: {v:.2f} {unidad} — posición {r.estado_posicion}",
        ).add_to(puntos)
    puntos.add_to(m)
    cmap.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)


def _guardar(m: folium.Map, nombre: str) -> None:
    m.save(str(asegurar_dir(config.DIR_MAPAS) / nombre))


def mapa_ubicaciones(tele: pd.DataFrame) -> None:
    df = _ubicables(tele)
    m = mapa_base(df, "Ubicación de las mediciones")
    for r in df.sort_values("orden").itertuples():
        imputada = r.estado_posicion == "imputada"
        folium.CircleMarker(
            location=[r.latitud, r.longitud], radius=7, fill=True, fill_opacity=0.9,
            fill_color=COLORES_ESTADO[r.estado_posicion],
            color="black" if imputada else COLORES_ESTADO[r.estado_posicion],
            dash_array="5,5" if imputada else None,
            tooltip=f"Captura {r.id_captura} — posición {r.estado_posicion}"
                    + (f" (±{r.incertidumbre_posicion_m:.0f} m)" if imputada else ""),
        ).add_to(m)
    n_excl = int((tele["estado_posicion"] == "excluida").sum())
    leyenda_estados(m, f"Capturas sin posición utilizable omitidas: {n_excl}")
    _guardar(m, "ubicaciones.html")


def mapa_ruta(tele: pd.DataFrame) -> None:
    df = _ubicables(tele).sort_values("orden")
    m = mapa_base(df, "Ruta de la estación móvil")
    folium.PolyLine(df[["latitud", "longitud"]].to_numpy().tolist(), color="#d62728", weight=4,
                    opacity=0.8, tooltip="Ruta en orden de captura").add_to(m)
    ini, fin = df.iloc[0], df.iloc[-1]
    folium.Marker([ini.latitud, ini.longitud], tooltip=f"Inicio (captura {ini.id_captura})",
                  icon=folium.Icon(color="green", icon="play")).add_to(m)
    folium.Marker([fin.latitud, fin.longitud], tooltip=f"Fin (captura {fin.id_captura})",
                  icon=folium.Icon(color="red", icon="stop")).add_to(m)
    for r in df.itertuples():
        imputada = r.estado_posicion == "imputada"
        folium.CircleMarker([r.latitud, r.longitud], radius=5 if imputada else 3,
                            color="#ff7f0e" if imputada else "#333", fill=True,
                            dash_array="3,3" if imputada else None,
                            tooltip=f"Captura {r.id_captura}" + (" (posición imputada)" if imputada else "")
                            ).add_to(m)
    m.get_root().html.add_child(folium.Element(
        '<div style="position:fixed;bottom:30px;left:10px;z-index:9999;background:white;padding:6px;'
        'border:1px solid #888;border-radius:4px;font:12px sans-serif;max-width:280px">'
        '<span style="color:#d62728;font-weight:bold">━</span> recorrido de la estación móvil<br>'
        '● captura (naranja punteado: posición imputada)<br>'
        f'Orden de la ruta: {config.BASE_ORDENAMIENTO}.</div>'))
    _guardar(m, "ruta.html")


def mapas_canales(pcc: pd.DataFrame) -> None:
    df = _ubicables(pcc)
    # Escala común a los cuatro canales para que sean comparables entre sí
    vmin = float(np.floor(min(df["potencia_dbm"].min(), UMBRAL_CONTAMINACION_DBM)))
    vmax = float(np.ceil(df["potencia_dbm"].max()))
    for canal, (f_ini, f_fin) in config.CANALES.items():
        sub = df[df["canal"] == canal]
        m = mapa_base(sub, f"Canal {canal} ({f_ini:.0f}-{f_fin:.0f} MHz): potencia de Parseval por captura")
        capa_valores(m, sub, "potencia_dbm", vmin, vmax, linear.YlOrRd_09.colors,
                     f"Potencia canal {canal} (dBm) — umbral {UMBRAL_CONTAMINACION_DBM:.0f} dBm", "dBm",
                     marcar_umbral=True)
        leyenda_imputadas(m)
        _guardar(m, f"canal_{canal}.html")


def mapa_temperatura(tele: pd.DataFrame) -> None:
    df = _ubicables(tele)
    vmin, vmax = float(np.floor(df["temperatura_c"].min())), float(np.ceil(df["temperatura_c"].max()))
    m = mapa_base(df, "Temperatura interna del sensor a lo largo de la ruta")
    capa_valores(m, df, "temperatura_c", vmin, vmax, list(reversed(linear.RdBu_11.colors)),
                 "Temperatura interna del sensor (°C)", "°C")
    leyenda_imputadas(m)
    _guardar(m, "temperatura.html")


def mapa_frecuencia(espectro: pd.DataFrame, tele: pd.DataFrame, extremas: dict) -> None:
    f = extremas["mas_contaminada"]
    col = config.columna_frecuencia(f["bin"])
    df = _ubicables(espectro[["id_captura", col]].rename(columns={col: "potencia_dbm"})
                    .merge(tele, on="id_captura", how="left"))
    vmin = float(np.floor(min(df["potencia_dbm"].min(), UMBRAL_CONTAMINACION_DBM)))
    vmax = float(np.ceil(df["potencia_dbm"].max()))
    m = mapa_base(df, f"Frecuencia más contaminada: {f['frecuencia_mhz']:.3f} MHz")
    capa_valores(m, df, "potencia_dbm", vmin, vmax, linear.YlOrRd_09.colors,
                 f"Potencia a f* = {f['frecuencia_mhz']:.3f} MHz (dBm)", "dBm", marcar_umbral=True)
    leyenda_imputadas(m)
    _guardar(m, "frecuencia_mas_contaminada.html")


def generar_mapas() -> list:
    """Genera los 8 mapas requeridos a partir de los artefactos curados y de indicadores."""
    tele = leer_csv(config.DIR_CURADO / "telemetria.csv")
    espectro = leer_csv(config.DIR_CURADO / "espectro.csv")
    pcc = leer_csv(config.DIR_INDICADORES / "potencia_canal_captura.csv")
    extremas = leer_json(config.DIR_INDICADORES / "frecuencias_extremas.json")
    mapa_ubicaciones(tele)
    mapa_ruta(tele)
    mapas_canales(pcc)
    mapa_temperatura(tele)
    mapa_frecuencia(espectro, tele, extremas)
    return [config.DIR_MAPAS / n for n in config.MAPAS_REQUERIDOS]
