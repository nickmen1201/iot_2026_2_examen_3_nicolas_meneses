"""Reconstrucción completa desde los datos crudos: un solo comando (FR-016).

Orden: extract -> transform -> presentacion -> compuertas -> fuentes (bonus) -> load.
Cada etapa lee solo lo que la anterior dejó en disco. Si una compuerta falla, el proceso termina
con código 2 y los artefactos quedan en disco para inspeccionarlos.
"""

import argparse
import importlib.util
import json
import re
import sys

from espectro import config, extract, load, presentacion, transform


def gate_calidad() -> tuple[bool, str]:
    """Compuerta 1: 63 disposiciones (una por archivo) y totales de imputación presentes."""
    import pandas as pd

    ruta = config.DIR_CALIDAD / "reporte_calidad.csv"
    resumen = config.DIR_CALIDAD / "resumen_imputacion.json"
    if not ruta.exists() or not resumen.exists():
        return False, "faltan reporte_calidad.csv o resumen_imputacion.json"
    r = pd.read_csv(ruta, dtype={"id_captura": str})
    totales = json.loads(resumen.read_text(encoding="utf-8"))
    ok = (len(r) == config.N_CAPTURAS_TOTAL and r["id_captura"].is_unique
          and r["disposicion"].notna().all() and r["motivo"].notna().all()
          and "total_corregidos" in totales and "total_imputados" in totales)
    return ok, f"{len(r)} disposiciones; corregidos={totales.get('total_corregidos')} imputados={totales.get('total_imputados')}"


def gate_indicadores() -> tuple[bool, str]:
    """Compuerta 2: 4 canales A-D con rango 1 y 4 asignados, o marcados como indeterminados."""
    import pandas as pd

    ruta = config.DIR_INDICADORES / "indicadores_canal.csv"
    if not ruta.exists():
        return False, "falta indicadores_canal.csv"
    ind = pd.read_csv(ruta)
    rangos = set(ind["rango"].dropna().astype(int))
    todos_indet = (ind["estado"] == "indeterminado").all()
    ok = list(ind["canal"]) == list(config.CANALES) and ({1, len(rangos)} <= rangos or todos_indet)
    peor = ind.loc[ind["rango"] == 1, "canal"].tolist()
    mejor = ind.loc[ind["rango"] == ind["rango"].max(), "canal"].tolist()
    return ok, f"más contaminado={peor} menos contaminado={mejor}"


def gate_presentacion() -> tuple[bool, str]:
    """Compuerta 3: los 8 mapas requeridos, el informe y todas las fuentes citadas existen."""
    faltan = [n for n in config.MAPAS_REQUERIDOS if not (config.DIR_MAPAS / n).exists()]
    informe = config.DIR_SITIO / "index.html"
    if not informe.exists():
        return False, "falta artefactos/sitio/index.html"
    citadas = set(re.findall(r"Fuente:.*?</p>", informe.read_text(encoding="utf-8")))
    rutas = {c for bloque in citadas for c in re.findall(r"<code>([^<]+)</code>", bloque)}
    rotas = sorted(r for r in rutas if not (config.RAIZ / r).exists())
    ok = not faltan and not rotas and bool(rutas)
    return ok, f"mapas faltantes={faltan} fuentes rotas={rotas} ({len(rutas)} fuentes citadas)"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Reconstruye todo el análisis desde medidas_2026_20/")
    parser.add_argument("--sin-carga", action="store_true", help="no ejecutar la etapa load (S3)")
    args = parser.parse_args(argv)

    for nombre, etapa in (("extract", extract.main), ("transform", transform.main),
                          ("presentacion", presentacion.main)):
        print(f"== {nombre} ==")
        codigo = etapa()
        if codigo:
            print(f"ERROR: la etapa {nombre} terminó con código {codigo}")
            return codigo

    print("== compuertas ==")
    todas = True
    for nombre, gate in (("calidad", gate_calidad), ("indicadores", gate_indicadores),
                         ("presentacion", gate_presentacion)):
        ok, detalle = gate()
        todas &= ok
        print(f"Compuerta de {nombre}: {'PASA' if ok else 'FALLA'} — {detalle}")
    if not todas:
        print("Una compuerta falló: no se ejecutan la estimación de fuentes ni la carga.")
        return 2

    # Bonus (FR-027): solo después de que las tres compuertas pasan
    if importlib.util.find_spec("espectro.fuentes") is not None:
        from espectro import fuentes, reporte

        print("== fuentes (bonus) ==")
        codigo = fuentes.main()
        if codigo:
            return codigo
        # El informe se regenera para incluir la sección de estimación de fuentes
        reporte.generar_reporte()

    if args.sin_carga:
        print("Carga omitida (--sin-carga)")
        return 0
    print("== load ==")
    return load.main()


if __name__ == "__main__":
    sys.exit(main())
