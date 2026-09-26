"""Pruebas de las reglas de calidad e imputación sobre datos sintéticos."""

import numpy as np
import pandas as pd

from espectro import calidad, config


def _staging(n=5, piso=-80.0):
    """Construye un staging sintético de n capturas de estudio en una línea recta de Medellín."""
    filas = []
    for i in range(1, n + 1):
        fila = {"id_captura": f"{i:03d}", "archivo": f"{i:03d}.txt", "es_estudio": True,
                "n_campos": config.N_CAMPOS, "contrato_ok": True, "motivo_contrato": ""}
        fila.update({c: piso for c in config.COLUMNAS_ESPECTRO})
        fila.update({"temperatura_c": 45.0, "longitud": -75.58 + 0.001 * i, "latitud": 6.24,
                     "altitud_m": 1500.0, "error_distancia": 1.0})
        filas.append(fila)
    return pd.DataFrame(filas)


def test_hueco_de_dos_bins_se_interpola():
    v = np.full(config.N_BINS, -80.0)
    v[10], v[11] = np.nan, np.nan
    rep, _, n, ok = calidad.reparar_espectro(v)
    assert ok and n == 2 and np.allclose(rep[10:12], -80.0)
    st = _staging()
    st.loc[2, ["p_0010", "p_0011"]] = np.nan
    r = calidad.evaluar_calidad(st)["reporte"].set_index("id_captura")
    assert r.at["003", "disposicion"] == "corregido"


def test_hueco_de_tres_bins_descarta_espectro():
    v = np.full(config.N_BINS, -80.0)
    v[10:13] = np.nan
    _, _, _, ok = calidad.reparar_espectro(v)
    assert not ok


def test_posicion_nula_entre_vecinos_validos_se_imputa():
    st = _staging()
    st.loc[2, ["longitud", "latitud", "altitud_m"]] = 0.0
    out = calidad.evaluar_calidad(st)
    t = out["telemetria"].set_index("id_captura")
    assert t.at["003", "estado_posicion"] == "imputada"
    assert np.isclose(t.at["003", "longitud"], (t.at["002", "longitud"] + t.at["004", "longitud"]) / 2)
    assert t.at["003", "incertidumbre_posicion_m"] > 0
    assert out["reporte"].set_index("id_captura").at["003", "disposicion"] == "imputado"


def test_dos_posiciones_nulas_consecutivas_se_excluyen():
    st = _staging()
    st.loc[[1, 2], ["longitud", "latitud", "altitud_m"]] = 0.0
    t = calidad.evaluar_calidad(st)["telemetria"].set_index("id_captura")
    assert t.at["002", "estado_posicion"] == "excluida"
    assert t.at["003", "estado_posicion"] == "excluida"


def test_piso_elevado_descarta_espectro_y_conserva_telemetria():
    st = _staging()
    st.loc[2, config.COLUMNAS_ESPECTRO] = -80.0 + 31.0
    r = calidad.evaluar_calidad(st)["reporte"].set_index("id_captura")
    assert r.at["003", "disposicion"] == "descartado"
    assert r.at["003", "alcance"] == "espectro"
    assert bool(r.at["003", "posicion_utilizable"])


def test_archivo_de_prueba_se_excluye():
    st = _staging()
    prueba = st.iloc[[0]].copy()
    prueba["id_captura"], prueba["archivo"], prueba["es_estudio"] = "medidaprueba", "medidaprueba.txt", False
    st = pd.concat([st, prueba], ignore_index=True)
    r = calidad.evaluar_calidad(st)["reporte"].set_index("id_captura")
    assert r.at["medidaprueba", "disposicion"] == "excluido_prueba"
