"""Pruebas de la física del análisis: eje de frecuencia, canales, Parseval y estadística."""

import numpy as np
import pytest

from espectro import config


def test_eje_y_canales():
    f = config.FRECUENCIAS_MHZ
    assert f[0] == pytest.approx(840.0)
    assert f[512] == pytest.approx(850.0)
    assert f[1023] == pytest.approx(859.98046875)
    esperados = {"A": 0, "B": 256, "C": 512, "D": 768}
    for canal, inicio in esperados.items():
        b = config.bins_canal(canal)
        assert len(b) == 256
        assert b[0] == inicio and b[-1] == inicio + 255
        assert np.all(np.diff(b) == 1)
    assert config.UMBRAL_CONTAMINACION_DBM == -60.0


def _espectro(valores_dbm):
    """Espectro curado sintético (una fila por captura) con columnas por frecuencia."""
    import pandas as pd

    cols = [config.columna_frecuencia(k) for k in range(config.N_BINS)]
    df = pd.DataFrame([list(v) for v in valores_dbm], columns=cols)
    df.insert(0, "id_captura", [f"{i + 1:03d}" for i in range(len(df))])
    return df


def _telemetria(ids):
    import pandas as pd

    return pd.DataFrame({"id_captura": ids, "latitud": 6.24, "longitud": -75.58, "estado_posicion": "medida"})


def test_parseval_suma_lineal():
    from espectro import indicadores

    esp = _espectro([np.full(config.N_BINS, -90.0)])
    pcc = indicadores.potencia_canal_captura(esp, _telemetria(["001"]))
    assert pcc["potencia_dbm"].iloc[0] == pytest.approx(-90 + 10 * np.log10(256), abs=1e-6)
    assert pcc["potencia_dbm"].iloc[0] == pytest.approx(-65.918, abs=1e-3)


def test_media_lineal_no_promedia_dbm():
    import pandas as pd

    from espectro import indicadores

    pcc = pd.DataFrame({"id_captura": ["001", "002"], "canal": "A", "potencia_dbm": [-50.0, -70.0],
                        "supera_umbral": [True, False]})
    ind = indicadores.indicadores_canal(pcc).set_index("canal")
    assert ind.at["A", "potencia_media_dbm"] == pytest.approx(-52.967, abs=1e-3)
    assert ind.at["B", "estado"] == "indeterminado"


def test_recomendacion_relativa():
    import pandas as pd

    from espectro import indicadores

    pcc = pd.DataFrame({"id_captura": "001", "canal": list("ABCD"), "potencia_dbm": [-40.0, -55.0, -30.0, -50.0],
                        "supera_umbral": True})
    rec = indicadores.recomendacion(indicadores.indicadores_canal(pcc)).set_index("canal")
    assert sorted(rec.index[rec["recomendacion"] == "usar"]) == ["B", "D"]
    assert (rec["recomendacion"] == "evitar").sum() == 2


def test_nyquist_en_el_limite():
    from espectro import analisis

    nyq = analisis.verificar_nyquist()
    assert nyq["veredicto"] == "cumple"
    assert nyq["en_el_limite"] is True


def test_spearman_parcial_elimina_confusor():
    from scipy import stats

    from espectro import analisis

    rng = np.random.default_rng(42)
    z = np.arange(200, dtype=float)
    x = z + rng.normal(0, 10, 200)
    y = z + rng.normal(0, 10, 200)
    rho, _ = stats.spearmanr(x, y)
    rho_p, _ = analisis.correlacion_parcial_spearman(x, y, z)
    assert abs(rho) > 0.7
    assert abs(rho_p) < 0.3
