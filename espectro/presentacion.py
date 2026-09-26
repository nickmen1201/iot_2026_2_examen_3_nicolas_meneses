"""Etapa de presentación: mapas HTML e informe, generados solo a partir de artefactos en disco."""

import sys

from espectro import config

ENTRADAS = [
    config.DIR_CALIDAD / "reporte_calidad.csv",
    config.DIR_CURADO / "telemetria.csv",
    config.DIR_CURADO / "espectro.csv",
    config.DIR_INDICADORES / "potencia_canal_captura.csv",
    config.DIR_INDICADORES / "indicadores_canal.csv",
    config.DIR_INDICADORES / "frecuencias_extremas.json",
    config.DIR_INDICADORES / "potencia_por_frecuencia.csv",
    config.DIR_INDICADORES / "recomendacion.csv",
    config.DIR_INDICADORES / "sensibilidad_saturacion.csv",
    config.DIR_INDICADORES / "ruta.json",
    config.DIR_INDICADORES / "temperatura_calidad.json",
    config.DIR_INDICADORES / "nyquist.json",
    config.DIR_CALIDAD / "resumen_imputacion.json",
    config.DIR_CALIDAD / "hallazgos_calidad.csv",
]


def main() -> int:
    faltan = [p for p in ENTRADAS if not p.exists()]
    if faltan:
        for p in faltan:
            print(f"ERROR: Falta artefacto: {p}. Ejecute python -m espectro.transform")
        return 1
    from espectro import mapas, reporte

    rutas = mapas.generar_mapas()
    citadas = reporte.generar_reporte()
    print(f"Presentación: {len(rutas)} mapas en {config.DIR_MAPAS}; informe con {len(citadas)} fuentes citadas "
          f"-> {config.DIR_SITIO / 'index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
