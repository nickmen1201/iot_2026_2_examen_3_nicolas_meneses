"""Etapa EXTRACT: lee las capturas crudas y valida el contrato de 1029 valores.

Los archivos de medidas_2026_20/ son inmutables: solo se leen. Un archivo que no cumple el
contrato se marca (contrato_ok = False) y sus valores quedan vacíos; nunca se reacomoda.
"""

import re
import sys

import numpy as np
import pandas as pd

from espectro import config
from espectro.utilidades import escribir_csv

COLUMNAS_VALORES = config.COLUMNAS_ESPECTRO + config.CAMPOS_TELEMETRIA


def leer_captura(ruta) -> dict:
    """Parsea un archivo de captura y devuelve una fila con su diagnóstico de contrato."""
    texto = ruta.read_text(encoding="utf-8", errors="replace").strip()
    campos = [c.strip() for c in texto.split(",")] if texto else []
    fila = {
        "id_captura": ruta.stem,
        "archivo": ruta.name,
        "es_estudio": bool(re.match(config.PATRON_ESTUDIO, ruta.name)),
        "n_campos": len(campos),
        "contrato_ok": False,
        "motivo_contrato": "",
    }
    valores = [np.nan] * config.N_CAMPOS
    if len(campos) != config.N_CAMPOS:
        fila["motivo_contrato"] = f"se esperaban {config.N_CAMPOS} campos y hay {len(campos)}"
    else:
        try:
            # nan/inf se aceptan aquí; la finitud se revisa bin a bin en calidad.py
            valores = [float(c) for c in campos]
            fila["contrato_ok"] = True
        except ValueError as e:
            fila["motivo_contrato"] = f"campo no numérico: {e}"
    fila.update(dict(zip(COLUMNAS_VALORES, valores)))
    return fila


def main() -> int:
    if not config.DIR_MEDIDAS.is_dir():
        print(f"ERROR: no existe la carpeta de medidas {config.DIR_MEDIDAS}")
        return 1
    archivos = sorted(config.DIR_MEDIDAS.glob("*.txt"))
    filas = [leer_captura(r) for r in archivos]
    df = pd.DataFrame(filas)
    if df.empty or not df["es_estudio"].any():
        print("ERROR: no se encontraron capturas del estudio (NNN.txt)")
        return 1
    escribir_csv(df, config.DIR_STAGING / "capturas_crudas.csv")
    n_mal = int((~df["contrato_ok"]).sum())
    print(f"Extract: {len(df)} archivos leídos ({int(df['es_estudio'].sum())} del estudio), "
          f"{n_mal} sin cumplir contrato -> {config.DIR_STAGING / 'capturas_crudas.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
