"""Informe técnico en HTML (español): figuras matplotlib y tablas insertadas desde artefactos.

Cada bloque del informe cita el artefacto que lo respalda (Principio IV). El texto interpretativo
lo escribe el analista en reporte/narrativa/*.md; si falta, el informe lo muestra como PENDIENTE.
"""

import base64

import matplotlib

matplotlib.use("Agg")
import markdown  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from jinja2 import Environment, FileSystemLoader, select_autoescape  # noqa: E402

from espectro import config  # noqa: E402
from espectro.config import UMBRAL_CONTAMINACION_DBM  # noqa: E402
from espectro.utilidades import asegurar_dir, leer_csv, leer_json, ruta_relativa  # noqa: E402

SECCIONES_NARRATIVA = ["ruta", "temperatura", "recomendacion", "conclusiones"]
COLOR_ESTADO = {"contaminado": "#d62728", "libre": "#2ca02c", "indeterminado": "#7f7f7f"}


def _guardar_fig(fig, nombre: str):
    ruta = asegurar_dir(config.DIR_FIGURAS) / nombre
    fig.tight_layout()
    # Sin metadatos de software para que la imagen sea reproducible byte a byte
    fig.savefig(ruta, dpi=120, metadata={"Software": None})
    plt.close(fig)
    return ruta


def _serie_bin(espectro: pd.DataFrame, tele: pd.DataFrame, k: int) -> pd.DataFrame:
    col = config.columna_frecuencia(k)
    return espectro[["id_captura", col]].merge(tele[["id_captura", "orden"]], on="id_captura").sort_values("orden")


def generar_figuras() -> dict:
    """Genera las 4 figuras del informe y devuelve {nombre: ruta}."""
    ppf = leer_csv(config.DIR_INDICADORES / "potencia_por_frecuencia.csv")
    ext = leer_json(config.DIR_INDICADORES / "frecuencias_extremas.json")
    ind = leer_csv(config.DIR_INDICADORES / "indicadores_canal.csv")
    esp = leer_csv(config.DIR_CURADO / "espectro.csv")
    tele = leer_csv(config.DIR_CURADO / "telemetria.csv")
    disp = leer_csv(config.DIR_CALIDAD / "reporte_calidad.csv")
    figs = {}

    # (1) Espectro medio con umbral, canales y extremos
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.plot(ppf["frecuencia_mhz"], ppf["potencia_media_dbm"], lw=0.9, color="#1f77b4",
            label="Potencia media por bin (media lineal)")
    ax.axhline(UMBRAL_CONTAMINACION_DBM, color="k", ls="--", lw=1, label=f"Umbral {UMBRAL_CONTAMINACION_DBM:.0f} dBm")
    for canal, (f_ini, f_fin) in config.CANALES.items():
        ax.axvline(f_ini, color="gray", lw=0.6)
        ax.text((f_ini + f_fin) / 2, ax.get_ylim()[1], f"Canal {canal}", ha="center", va="bottom", fontsize=9)
    for clave, color, texto in (("mas_contaminada", "#d62728", "más contaminada"),
                                ("menos_contaminada", "#2ca02c", "menos contaminada")):
        f = ext[clave]
        ax.plot(f["frecuencia_mhz"], f["potencia_dbm"], "o", color=color,
                label=f"Frecuencia {texto}: {f['frecuencia_mhz']:.3f} MHz ({f['potencia_dbm']:.1f} dBm)")
    ax.set_xlabel("Frecuencia (MHz)")
    ax.set_ylabel("Potencia (dBm)")
    ax.set_xlim(840, 860)
    ax.legend(fontsize=8, loc="lower right")
    figs["espectro_medio"] = _guardar_fig(fig, "espectro_medio.png")

    # (2) Potencia por captura en la frecuencia más y menos contaminada (FR-013)
    fig, axes = plt.subplots(2, 1, figsize=(10, 5.5), sharex=True)
    for ax, (clave, color, texto) in zip(axes, (("mas_contaminada", "#d62728", "más contaminada"),
                                                 ("menos_contaminada", "#2ca02c", "menos contaminada"))):
        f = ext[clave]
        s = _serie_bin(esp, tele, f["bin"])
        ax.plot(s["orden"], s[config.columna_frecuencia(f["bin"])], "o-", ms=3, color=color)
        ax.axhline(UMBRAL_CONTAMINACION_DBM, color="k", ls="--", lw=1)
        ax.set_title(f"Frecuencia {texto}: {f['frecuencia_mhz']:.3f} MHz (media {f['potencia_dbm']:.1f} dBm)",
                     fontsize=10)
        ax.set_ylabel("Potencia (dBm)")
    axes[-1].set_xlabel("Orden de captura (número de archivo)")
    figs["frecuencias_extremas"] = _guardar_fig(fig, "frecuencias_extremas.png")

    # (3) Temperatura interna y piso de ruido frente al orden de adquisición
    t = tele.sort_values("orden")
    fig, ax1 = plt.subplots(figsize=(10, 4))
    ax1.plot(t["orden"], t["temperatura_c"], "o-", ms=3, color="#d62728", label="Temperatura interna")
    ax1.set_xlabel("Orden de captura (número de archivo)")
    ax1.set_ylabel("Temperatura interna del sensor (°C)", color="#d62728")
    ax2 = ax1.twinx()
    ax2.plot(t["orden"], t["piso_ruido_dbm"], "s-", ms=3, color="#1f77b4", label="Piso de ruido (p10)")
    ax2.set_ylabel("Piso de ruido, percentil 10 (dBm)", color="#1f77b4")
    descartadas = t[t["id_captura"].isin(disp.loc[~disp["espectro_utilizable"], "id_captura"])]
    ax2.plot(descartadas["orden"], descartadas["piso_ruido_dbm"], "x", ms=10, mew=2, color="k",
             label="Espectro descartado (saturación)")
    for r in descartadas.itertuples():
        ax2.annotate(r.id_captura, (r.orden, r.piso_ruido_dbm), textcoords="offset points", xytext=(6, -4))
    fig.legend(loc="upper left", fontsize=8, bbox_to_anchor=(0.07, 0.93))
    figs["temperatura_piso_ruido"] = _guardar_fig(fig, "temperatura_piso_ruido.png")

    # (4) Potencia media por canal frente al umbral
    fig, ax = plt.subplots(figsize=(7, 4))
    datos = ind.dropna(subset=["potencia_media_dbm"])
    base = min(datos["potencia_media_dbm"].min(), UMBRAL_CONTAMINACION_DBM) - 10
    ax.bar(datos["canal"], datos["potencia_media_dbm"] - base, bottom=base,
           color=[COLOR_ESTADO[e] for e in datos["estado"]])
    for r in datos.itertuples():
        ax.text(r.canal, r.potencia_media_dbm + 0.5, f"{r.potencia_media_dbm:.1f}", ha="center", va="bottom")
    ax.axhline(UMBRAL_CONTAMINACION_DBM, color="k", ls="--", lw=1, label=f"Umbral {UMBRAL_CONTAMINACION_DBM:.0f} dBm")
    ax.set_ylim(base, datos["potencia_media_dbm"].max() + 6)  # margen para las etiquetas
    ax.set_xlabel("Canal (5 MHz)")
    ax.set_ylabel("Potencia media del canal (dBm)")
    ax.legend(fontsize=8)
    figs["potencia_canales"] = _guardar_fig(fig, "potencia_canales.png")
    return figs


def _img_base64(ruta) -> str:
    return "data:image/png;base64," + base64.b64encode(ruta.read_bytes()).decode("ascii")


def _narrativa(nombre: str) -> dict:
    """Convierte la narrativa del analista a HTML; marca PENDIENTE si falta o no se ha redactado."""
    ruta = config.DIR_NARRATIVA / f"{nombre}.md"
    if not ruta.exists():
        return {"html": "", "pendiente": True}
    texto = ruta.read_text(encoding="utf-8")
    return {"html": markdown.markdown(texto, extensions=["tables"]),
            "pendiente": texto.lstrip().startswith("PENDIENTE")}


def _tabla(df: pd.DataFrame, **kwargs) -> str:
    return df.to_html(index=False, classes="tabla", border=0, na_rep="—", float_format=lambda x: f"{x:.2f}",
                      **kwargs)


def generar_reporte() -> list[str]:
    """Genera artefactos/sitio/index.html y devuelve las rutas de artefactos citadas en él."""
    figs = generar_figuras()
    A = {  # artefactos citados, por clave
        "reporte_calidad": config.DIR_CALIDAD / "reporte_calidad.csv",
        "hallazgos": config.DIR_CALIDAD / "hallazgos_calidad.csv",
        "resumen": config.DIR_CALIDAD / "resumen_imputacion.json",
        "nyquist": config.DIR_INDICADORES / "nyquist.json",
        "indicadores": config.DIR_INDICADORES / "indicadores_canal.csv",
        "pcc": config.DIR_INDICADORES / "potencia_canal_captura.csv",
        "extremas": config.DIR_INDICADORES / "frecuencias_extremas.json",
        "ppf": config.DIR_INDICADORES / "potencia_por_frecuencia.csv",
        "sensibilidad": config.DIR_INDICADORES / "sensibilidad_saturacion.csv",
        "ruta": config.DIR_INDICADORES / "ruta.json",
        "temperatura": config.DIR_INDICADORES / "temperatura_calidad.json",
        "recomendacion": config.DIR_INDICADORES / "recomendacion.csv",
        "telemetria": config.DIR_CURADO / "telemetria.csv",
        "fuentes": config.DIR_INDICADORES / "fuentes_estimadas.csv",
    }
    A.update({f"fig_{k}": v for k, v in figs.items()})

    disp = leer_csv(A["reporte_calidad"])
    hall = leer_csv(A["hallazgos"])
    ind = leer_csv(A["indicadores"])
    rec = leer_csv(A["recomendacion"])
    sens = leer_csv(A["sensibilidad"])
    fuentes = leer_csv(A["fuentes"]) if A["fuentes"].exists() else None

    no_aceptadas = disp[disp["disposicion"] != "aceptado"][["id_captura", "disposicion", "alcance", "motivo",
                                                             "tecnica", "n_valores_modificados"]]
    hall_rel = hall[hall["severidad"] != "info"]
    ind_tabla = ind[["canal", "f_ini_mhz", "f_fin_mhz", "n_capturas", "potencia_media_dbm", "potencia_mediana_dbm",
                     "pct_capturas_sobre_umbral", "estado", "rango"]].rename(columns={
        "canal": "Canal", "f_ini_mhz": "Desde (MHz)", "f_fin_mhz": "Hasta (MHz)", "n_capturas": "Capturas",
        "potencia_media_dbm": "Potencia media (dBm)", "potencia_mediana_dbm": "Mediana (dBm)",
        "pct_capturas_sobre_umbral": "% capturas > umbral", "estado": "Estado", "rango": "Rango"})
    rec_tabla = rec[["canal", "recomendacion", "estado", "rango", "indicador_base"]].rename(columns={
        "canal": "Canal", "recomendacion": "Recomendación", "estado": "Estado frente al umbral",
        "rango": "Rango (1 = más contaminado)", "indicador_base": "Potencia media (dBm)"})
    con_datos = ind.dropna(subset=["potencia_media_dbm"])

    ctx = {
        "umbral": UMBRAL_CONTAMINACION_DBM,
        "n_estudio": config.N_CAPTURAS_ESTUDIO,
        "fuente": {k: ruta_relativa(v) for k, v in A.items()},
        "fig": {k: _img_base64(v) for k, v in figs.items()},
        "resumen": leer_json(A["resumen"]),
        "nyquist": leer_json(A["nyquist"]),
        "extremas": leer_json(A["extremas"]),
        "ruta": leer_json(A["ruta"]),
        "temp": leer_json(A["temperatura"]),
        "peor": con_datos.loc[con_datos["potencia_media_dbm"].idxmax()].to_dict() if len(con_datos) else None,
        "mejor": con_datos.loc[con_datos["potencia_media_dbm"].idxmin()].to_dict() if len(con_datos) else None,
        "usar": rec.loc[rec["recomendacion"] == "usar", "canal"].tolist(),
        "evitar": rec.loc[rec["recomendacion"] == "evitar", "canal"].tolist(),
        "tabla_disposiciones": _tabla(no_aceptadas),
        "tabla_hallazgos": _tabla(hall_rel),
        "tabla_indicadores": _tabla(ind_tabla),
        "tabla_recomendacion": _tabla(rec_tabla),
        "tabla_sensibilidad": _tabla(sens.drop(columns=["capturas_reincorporadas"])),
        "sensibilidad": sens.to_dict("records"),
        "tabla_fuentes": _tabla(fuentes) if fuentes is not None else None,
        "narrativa": {n: _narrativa(n) for n in SECCIONES_NARRATIVA},
        "mapas": [("Ubicación de las mediciones", "ubicaciones.html"), ("Ruta de la estación", "ruta.html"),
                  *[(f"Mapa de calor canal {c}", f"canal_{c}.html") for c in config.CANALES],
                  ("Temperatura interna del sensor", "temperatura.html"),
                  ("Frecuencia más contaminada", "frecuencia_mas_contaminada.html")]
                 + ([("Estimación de fuentes", config.MAPA_FUENTES)] if fuentes is not None else []),
    }
    env = Environment(loader=FileSystemLoader(config.DIR_PLANTILLAS), autoescape=select_autoescape(["html"]))
    html = env.get_template("reporte.html.j2").render(**ctx)
    salida = asegurar_dir(config.DIR_SITIO) / "index.html"
    salida.write_text(html, encoding="utf-8", newline="\n")
    # Rutas citadas con "Fuente:" en el informe (para la compuerta de presentación)
    citadas = [ruta for clave, ruta in A.items() if clave != "fuentes" or fuentes is not None]
    return [ruta_relativa(r) for r in citadas]
