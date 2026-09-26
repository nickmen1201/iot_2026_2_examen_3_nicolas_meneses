"""Evaluación de calidad: una disposición por captura, hallazgos e imputación por interpolación.

Reglas (research R5): contrato de 1029 valores, bins no finitos o fuera de rango, saturación del
receptor por piso de ruido, fallas de posicionamiento, error de distancia y temperatura. Solo se
imputa por interpolación lineal (FR-029); nunca se rellena con cero, media o mediana.
"""

import numpy as np
import pandas as pd

from espectro import config
from espectro.utilidades import haversine_m

TECNICA_BINS = "interpolación lineal entre bins adyacentes de la misma captura"
TECNICA_POSICION = "interpolación lineal entre las capturas vecinas de la ruta"


def _hallazgo(id_captura, campo, regla, valor, limite, severidad, accion) -> dict:
    return {
        "id_captura": id_captura,
        "campo": campo,
        "regla": regla,
        "valor_observado": str(valor),
        "limite": str(limite),
        "severidad": severidad,
        "accion": accion,
    }


def _corridas(mascara: np.ndarray) -> list[tuple[int, int]]:
    """Devuelve las corridas [inicio, fin] (inclusive) de valores True consecutivos."""
    corridas, inicio = [], None
    for k, v in enumerate(mascara):
        if v and inicio is None:
            inicio = k
        elif not v and inicio is not None:
            corridas.append((inicio, k - 1))
            inicio = None
    if inicio is not None:
        corridas.append((inicio, len(mascara) - 1))
    return corridas


def reparar_espectro(valores, id_captura: str = ""):
    """Repara huecos cortos del espectro.

    Retorna (valores_reparados, hallazgos, n_corregidos, utilizable). Un bin es inválido si no es
    finito o sale de LIMITES["dbm"]. Corridas de hasta MAX_HUECO_BINS con vecinos válidos a ambos
    lados se interpolan linealmente; una corrida más larga o pegada a un borde invalida el espectro,
    porque una interpolación más ancha podría borrar una portadora de banda angosta.
    """
    v = np.asarray(valores, dtype=float).copy()
    lo, hi = config.LIMITES["dbm"]
    with np.errstate(invalid="ignore"):
        invalido = ~np.isfinite(v) | (v < lo) | (v > hi)
    hallazgos, n_corregidos, utilizable = [], 0, True
    ultimo = len(v) - 1
    for ini, fin in _corridas(invalido):
        largo = fin - ini + 1
        campo = f"espectro[{ini}-{fin}]"
        if largo <= config.MAX_HUECO_BINS and ini > 0 and fin < ultimo:
            k = np.arange(ini, fin + 1)
            v[k] = np.interp(k, [ini - 1, fin + 1], [v[ini - 1], v[fin + 1]])
            n_corregidos += largo
            hallazgos.append(_hallazgo(id_captura, campo, "bin_invalido", f"{largo} bins",
                                       f"<= {config.MAX_HUECO_BINS} bins", "advertencia",
                                       f"corregido por {TECNICA_BINS}"))
        else:
            utilizable = False
            hallazgos.append(_hallazgo(id_captura, campo, "hueco_espectral_largo", f"{largo} bins",
                                       f"<= {config.MAX_HUECO_BINS} bins con vecinos válidos",
                                       "critico", "espectro descartado"))
    return v, hallazgos, n_corregidos, utilizable


def evaluar_saturacion(df_estudio: pd.DataFrame) -> pd.DataFrame:
    """Piso de ruido (p10 de los 1024 bins crudos) y su distancia a la mediana del estudio."""
    espectros = df_estudio[config.COLUMNAS_ESPECTRO].to_numpy(dtype=float)
    piso = np.full(len(df_estudio), np.nan)
    ok = df_estudio["contrato_ok"].to_numpy(dtype=bool)
    piso[ok] = np.nanpercentile(espectros[ok], config.PERCENTIL_PISO, axis=1)
    mediana = float(np.nanmedian(piso))
    delta = piso - mediana
    return pd.DataFrame({
        "id_captura": df_estudio["id_captura"].to_numpy(),
        "piso_ruido_dbm": piso,
        "delta_piso_db": delta,
        "saturada": delta > config.UMBRAL_SATURACION_DB,
        "mediana_piso_dbm": mediana,
    })


def _posicion_valida(fila) -> bool:
    lon, lat, alt = fila["longitud"], fila["latitud"], fila["altitud_m"]
    if not all(np.isfinite([lon, lat, alt])):
        return False
    if lon == 0 and lat == 0 and alt == 0:
        return False
    L = config.LIMITES
    return (L["lon"][0] <= lon <= L["lon"][1] and L["lat"][0] <= lat <= L["lat"][1]
            and L["alt_m"][0] <= alt <= L["alt_m"][1])


def evaluar_posiciones(df_estudio: pd.DataFrame):
    """Clasifica cada posición (medida, imputada, baja_confianza, excluida) e imputa huecos de 1.

    Retorna (DataFrame de telemetría curada, lista de hallazgos). El orden de la ruta es el número
    de archivo, porque las capturas no tienen marca de tiempo.
    """
    df = df_estudio.copy()
    df["orden"] = df["id_captura"].astype(int)
    df = df.sort_values("orden").reset_index(drop=True)
    valida = np.array([bool(r["contrato_ok"]) and _posicion_valida(r) for _, r in df.iterrows()])
    hallazgos = []
    estado = np.where(valida, "medida", "excluida").astype(object)
    incert = np.where(valida, 0.0, np.nan)
    n_imp = np.zeros(len(df), dtype=int)
    lon, lat, alt = (df[c].to_numpy(dtype=float).copy() for c in ("longitud", "latitud", "altitud_m"))

    for ini, fin in _corridas(~valida):
        largo = fin - ini + 1
        vecinos_ok = ini > 0 and fin < len(df) - 1 and valida[ini - 1] and valida[fin + 1]
        for i in range(ini, fin + 1):
            idc = df.at[i, "id_captura"]
            observado = f"lon={df.at[i, 'longitud']}, lat={df.at[i, 'latitud']}, alt={df.at[i, 'altitud_m']}"
            if largo <= config.MAX_HUECO_CAPTURAS and vecinos_ok:
                a, b = ini - 1, fin + 1
                t = (i - a) / (b - a)
                lon[i] = lon[a] + t * (lon[b] - lon[a])
                lat[i] = lat[a] + t * (lat[b] - lat[a])
                alt[i] = alt[a] + t * (alt[b] - alt[a])
                estado[i] = "imputada"
                # Incertidumbre: media distancia entre los vecinos usados en la interpolación
                incert[i] = float(haversine_m(lat[a], lon[a], lat[b], lon[b])) / 2
                n_imp[i] = 3
                hallazgos.append(_hallazgo(idc, "posicion", "falla_posicionamiento", observado,
                                           "posición dentro del área metropolitana y no nula",
                                           "critico",
                                           f"imputada por {TECNICA_POSICION} "
                                           f"({df.at[a, 'id_captura']}-{df.at[b, 'id_captura']}), "
                                           f"incertidumbre ≈ {incert[i]:.0f} m"))
            else:
                lon[i] = lat[i] = alt[i] = np.nan
                hallazgos.append(_hallazgo(idc, "posicion", "falla_posicionamiento", observado,
                                           f"hueco <= {config.MAX_HUECO_CAPTURAS} captura con vecinos válidos",
                                           "critico", "excluida de las salidas espaciales"))

    # Error de distancia fuera de la línea base: se conserva la posición y se marca
    err = df["error_distancia"].to_numpy(dtype=float)
    lim_err = config.LIMITES["error_dist_max"]
    for i in np.flatnonzero((err > lim_err) & (estado == "medida")):
        estado[i] = "baja_confianza"
        hallazgos.append(_hallazgo(df.at[i, "id_captura"], "error_distancia", "posicion_baja_confianza",
                                   err[i], f"<= {lim_err}", "advertencia",
                                   "se conserva: coordenadas coherentes con sus vecinas"))

    # Temperatura interna del sensor: solo se marca, nunca se imputa
    lo, hi = config.LIMITES["temp_c"]
    temp = df["temperatura_c"].to_numpy(dtype=float)
    for i in np.flatnonzero(~((temp >= lo) & (temp <= hi))):
        hallazgos.append(_hallazgo(df.at[i, "id_captura"], "temperatura_c", "temperatura_fuera_de_rango",
                                   temp[i], f"[{lo}, {hi}] °C", "advertencia", "marcada, no imputada"))

    tele = pd.DataFrame({
        "id_captura": df["id_captura"],
        "orden": df["orden"],
        "temperatura_c": temp,
        "longitud": lon,
        "latitud": lat,
        "altitud_m": alt,
        "error_distancia": err,
        "estado_posicion": estado,
        "incertidumbre_posicion_m": incert,
        "n_posicion_imputados": n_imp,
    })
    return tele, hallazgos


def asignar_disposiciones(staging: pd.DataFrame, reparacion: dict, saturacion: pd.DataFrame,
                          telemetria: pd.DataFrame) -> pd.DataFrame:
    """Una disposición por archivo con precedencia descartado > imputado > corregido > aceptado."""
    sat = saturacion.set_index("id_captura")
    tele = telemetria.set_index("id_captura")
    filas = []
    for _, r in staging.iterrows():
        idc = r["id_captura"]
        if not r["es_estudio"]:
            filas.append({"id_captura": idc, "disposicion": "excluido_prueba", "alcance": "total",
                          "motivo": "captura de prueba de adquisición, fuera del conjunto de estudio (FR-007)",
                          "tecnica": "", "n_valores_modificados": 0,
                          "espectro_utilizable": False, "posicion_utilizable": False})
            continue
        if not r["contrato_ok"]:
            filas.append({"id_captura": idc, "disposicion": "descartado", "alcance": "total",
                          "motivo": f"no cumple el contrato de datos: {r['motivo_contrato']}",
                          "tecnica": "", "n_valores_modificados": 0,
                          "espectro_utilizable": False, "posicion_utilizable": False})
            continue
        _, _, n_corr, esp_ok = reparacion[idc]
        saturada = bool(sat.at[idc, "saturada"])
        estado_pos = tele.at[idc, "estado_posicion"]
        n_pos = int(tele.at[idc, "n_posicion_imputados"])
        esp_util = esp_ok and not saturada
        pos_util = estado_pos != "excluida"
        motivos, tecnicas = [], []
        if saturada:
            motivos.append(f"piso de ruido {sat.at[idc, 'delta_piso_db']:.1f} dB sobre la mediana del "
                           f"estudio (> {config.UMBRAL_SATURACION_DB:.0f} dB): posible saturación del receptor; "
                           "se conserva su telemetría")
        if not esp_ok:
            motivos.append("hueco espectral mayor al máximo interpolable")
        if estado_pos == "imputada":
            motivos.append(f"posición nula imputada (incertidumbre ≈ "
                           f"{tele.at[idc, 'incertidumbre_posicion_m']:.0f} m)")
            tecnicas.append(TECNICA_POSICION)
        if estado_pos == "excluida":
            motivos.append("posición inválida sin vecinos válidos: excluida de las salidas espaciales")
        if estado_pos == "baja_confianza":
            motivos.append(f"error de distancia {tele.at[idc, 'error_distancia']} fuera de la línea base; "
                           "posición conservada con baja confianza")
        if n_corr:
            motivos.append(f"{n_corr} bins espectrales inválidos corregidos")
            tecnicas.append(TECNICA_BINS)

        if not esp_util:
            disp, alcance = "descartado", ("total" if not pos_util else "espectro")
        elif not pos_util:
            disp, alcance = "descartado", "posicion"
        elif estado_pos == "imputada":
            disp, alcance = "imputado", "posicion"
        elif n_corr:
            disp, alcance = "corregido", "espectro"
        else:
            disp, alcance = "aceptado", "ninguno"
        filas.append({"id_captura": idc, "disposicion": disp, "alcance": alcance,
                      "motivo": "; ".join(motivos) if motivos else "cumple todas las reglas de calidad",
                      "tecnica": "; ".join(tecnicas), "n_valores_modificados": int(n_corr + n_pos),
                      "espectro_utilizable": bool(esp_util), "posicion_utilizable": bool(pos_util)})
    return pd.DataFrame(filas)


def resumen_imputacion(disposiciones: pd.DataFrame, reparacion: dict, telemetria: pd.DataFrame) -> dict:
    """Totales de valores corregidos e imputados, con técnica y justificación por campo."""
    n_bins = int(sum(v[2] for v in reparacion.values()))
    caps_bins = sorted(k for k, v in reparacion.items() if v[2] > 0)
    imp = telemetria[telemetria["estado_posicion"] == "imputada"]
    n_pos = int(imp["n_posicion_imputados"].sum())
    return {
        "total_corregidos": n_bins,
        "total_imputados": n_pos,
        "detalle": [
            {"campo": "espectro (dBm por bin)", "tecnica": TECNICA_BINS, "n_valores": n_bins,
             "capturas": caps_bins,
             "justificacion": f"huecos de hasta {config.MAX_HUECO_BINS} bins (≈39 kHz) son más angostos que "
                              "cualquier canal; interpolar más ancho podría borrar una portadora angosta"},
            {"campo": "longitud, latitud, altitud", "tecnica": TECNICA_POSICION, "n_valores": n_pos,
             "capturas": sorted(imp["id_captura"].tolist()),
             "incertidumbre_m": {r.id_captura: r.incertidumbre_posicion_m for r in imp.itertuples()},
             "justificacion": "la estación móvil recorre la ruta de forma continua; con un hueco de una "
                              "sola captura, el punto medio entre las vecinas es la mejor estimación "
                              "y su incertidumbre es la mitad de la distancia entre ellas"},
        ],
        "capturas_descartadas": sorted(disposiciones.loc[disposiciones["disposicion"] == "descartado",
                                                         "id_captura"].tolist()),
        "capturas_prueba_excluidas": sorted(disposiciones.loc[disposiciones["disposicion"] == "excluido_prueba",
                                                              "id_captura"].tolist()),
        "n_por_disposicion": disposiciones["disposicion"].value_counts().sort_index().to_dict(),
    }


def evaluar_calidad(staging: pd.DataFrame) -> dict:
    """Aplica todas las reglas y devuelve los artefactos de calidad y curados como DataFrames."""
    estudio = staging[staging["es_estudio"]].reset_index(drop=True)
    reparacion, hallazgos = {}, []
    for _, r in estudio.iterrows():
        if r["contrato_ok"]:
            res = reparar_espectro(r[config.COLUMNAS_ESPECTRO].to_numpy(dtype=float), r["id_captura"])
            reparacion[r["id_captura"]] = res
            hallazgos.extend(res[1])
        else:
            hallazgos.append(_hallazgo(r["id_captura"], "archivo", "contrato_datos", r["n_campos"],
                                       config.N_CAMPOS, "critico", "captura descartada"))

    saturacion = evaluar_saturacion(estudio)
    for s in saturacion[saturacion["saturada"]].itertuples():
        hallazgos.append(_hallazgo(s.id_captura, "espectro", "saturacion_receptor",
                                   f"{s.delta_piso_db:.1f} dB sobre la mediana",
                                   f"<= {config.UMBRAL_SATURACION_DB} dB", "critico",
                                   "espectro descartado; telemetría conservada"))

    telemetria, h_pos = evaluar_posiciones(estudio)
    hallazgos.extend(h_pos)
    disp = asignar_disposiciones(staging, reparacion, saturacion, telemetria)

    for p in disp[disp["disposicion"] == "excluido_prueba"].itertuples():
        hallazgos.append(_hallazgo(p.id_captura, "archivo", "captura_de_prueba", p.id_captura,
                                   config.PATRON_ESTUDIO, "info", "excluida del estudio"))

    telemetria = telemetria.merge(saturacion[["id_captura", "piso_ruido_dbm", "delta_piso_db"]],
                                  on="id_captura", how="left")

    # Espectro curado: solo capturas con espectro utilizable, columnas nombradas por frecuencia
    util = disp.loc[disp["espectro_utilizable"], "id_captura"].tolist()
    util = sorted(util, key=int)
    matriz = np.vstack([reparacion[i][0] for i in util]) if util else np.empty((0, config.N_BINS))
    espectro = pd.DataFrame(matriz, columns=[config.columna_frecuencia(k) for k in range(config.N_BINS)])
    espectro.insert(0, "id_captura", util)

    hall = pd.DataFrame(hallazgos, columns=["id_captura", "campo", "regla", "valor_observado", "limite",
                                            "severidad", "accion"])
    hall = hall.sort_values(["id_captura", "campo", "regla"], kind="stable").reset_index(drop=True)
    return {
        "reporte": disp,
        "hallazgos": hall,
        "resumen": resumen_imputacion(disp, reparacion, telemetria),
        "telemetria": telemetria.drop(columns=["n_posicion_imputados"]),
        "espectro": espectro,
    }
