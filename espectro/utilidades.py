"""Utilidades compartidas: escritura determinista de artefactos y conversiones físicas."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

RADIO_TIERRA_M = 6_371_000.0


def asegurar_dir(p: Path) -> Path:
    """Crea el directorio (y sus padres) si no existe."""
    p.mkdir(parents=True, exist_ok=True)
    return p


def escribir_csv(df: pd.DataFrame, ruta: Path) -> None:
    """Escribe un CSV con formato fijo para que dos corridas produzcan bytes idénticos."""
    asegurar_dir(ruta.parent)
    df.to_csv(ruta, index=False, float_format="%.6f", lineterminator="\n", encoding="utf-8")


def _a_nativo(obj):
    # Convierte tipos de numpy a tipos nativos de Python para json
    if isinstance(obj, dict):
        return {str(k): _a_nativo(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_a_nativo(v) for v in obj]
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        v = float(obj)
        # NaN no es JSON válido: se representa como null
        return None if not np.isfinite(v) else round(v, 6)
    return obj


def escribir_json(obj, ruta: Path) -> None:
    """Escribe JSON ordenado y legible (claves ordenadas, UTF-8 sin escapar)."""
    asegurar_dir(ruta.parent)
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        json.dump(_a_nativo(obj), f, sort_keys=True, indent=2, ensure_ascii=False)
        f.write("\n")


def leer_csv(ruta: Path, **kwargs) -> pd.DataFrame:
    """Lee un artefacto CSV; falla con un mensaje claro si no existe."""
    if not ruta.exists():
        raise FileNotFoundError(f"Falta artefacto: {ruta}")
    return pd.read_csv(ruta, dtype={"id_captura": str}, **kwargs)


def leer_json(ruta: Path):
    """Lee un artefacto JSON; falla con un mensaje claro si no existe."""
    if not ruta.exists():
        raise FileNotFoundError(f"Falta artefacto: {ruta}")
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def haversine_m(lat1, lon1, lat2, lon2):
    """Distancia sobre la esfera terrestre en metros (acepta escalares o arreglos)."""
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * RADIO_TIERRA_M * np.arcsin(np.sqrt(a))


def dbm_a_mw(x):
    """Convierte dBm a potencia lineal en mW (antes de cualquier suma o promedio)."""
    return np.power(10.0, np.asarray(x, dtype=float) / 10.0)


def mw_a_dbm(x):
    """Convierte potencia lineal en mW a dBm."""
    return 10.0 * np.log10(np.asarray(x, dtype=float))


def ruta_relativa(ruta: Path) -> str:
    """Ruta del artefacto relativa a la raíz del repositorio (para citar en el informe)."""
    from espectro.config import RAIZ

    return Path(ruta).resolve().relative_to(RAIZ).as_posix()
