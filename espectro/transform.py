"""Etapa TRANSFORM: calidad -> indicadores -> análisis de evidencia.

Lee únicamente artefactos/staging/ y persiste cada resultado intermedio en disco (Principio II).
La calidad corre primero: ningún indicador se calcula antes de que exista el reporte de calidad.
"""

import sys

from espectro import config
from espectro.utilidades import escribir_csv, escribir_json, leer_csv


def paso_calidad() -> None:
    """Paso 1: disposiciones, hallazgos, resumen de imputación y conjunto curado."""
    from espectro import calidad

    staging = leer_csv(config.DIR_STAGING / "capturas_crudas.csv")
    out = calidad.evaluar_calidad(staging)
    escribir_csv(out["reporte"], config.DIR_CALIDAD / "reporte_calidad.csv")
    escribir_csv(out["hallazgos"], config.DIR_CALIDAD / "hallazgos_calidad.csv")
    escribir_json(out["resumen"], config.DIR_CALIDAD / "resumen_imputacion.json")
    escribir_csv(out["telemetria"], config.DIR_CURADO / "telemetria.csv")
    escribir_csv(out["espectro"], config.DIR_CURADO / "espectro.csv")
    r = out["resumen"]
    print(f"Calidad: {r['n_por_disposicion']} | corregidos={r['total_corregidos']} "
          f"imputados={r['total_imputados']}")


def paso_indicadores() -> None:
    """Paso 2: potencia de Parseval por captura y canal, indicadores, extremos y recomendación."""
    from espectro import indicadores

    espectro = leer_csv(config.DIR_CURADO / "espectro.csv")
    telemetria = leer_csv(config.DIR_CURADO / "telemetria.csv")
    pcc = indicadores.potencia_canal_captura(espectro, telemetria)
    ind = indicadores.indicadores_canal(pcc)
    ppf = indicadores.potencia_por_frecuencia(espectro)
    ext = indicadores.frecuencias_extremas(ppf)
    rec = indicadores.recomendacion(ind)
    escribir_csv(pcc, config.DIR_INDICADORES / "potencia_canal_captura.csv")
    escribir_csv(ind, config.DIR_INDICADORES / "indicadores_canal.csv")
    escribir_csv(ppf, config.DIR_INDICADORES / "potencia_por_frecuencia.csv")
    escribir_json(ext, config.DIR_INDICADORES / "frecuencias_extremas.json")
    escribir_csv(rec, config.DIR_INDICADORES / "recomendacion.csv")
    for r in ind.itertuples():
        print(f"Canal {r.canal}: {r.potencia_media_dbm:.2f} dBm ({r.estado}, rango {r.rango})")


def paso_analisis() -> None:
    """Paso 3: evidencia del informe (ruta, temperatura, Nyquist, sensibilidad a saturación)."""
    from espectro import analisis

    staging = leer_csv(config.DIR_STAGING / "capturas_crudas.csv")
    disp = leer_csv(config.DIR_CALIDAD / "reporte_calidad.csv")
    telemetria = leer_csv(config.DIR_CURADO / "telemetria.csv")
    espectro = leer_csv(config.DIR_CURADO / "espectro.csv")
    escribir_json(analisis.describir_ruta(telemetria), config.DIR_INDICADORES / "ruta.json")
    temp = analisis.temperatura_vs_calidad(telemetria, disp)
    escribir_json(temp, config.DIR_INDICADORES / "temperatura_calidad.json")
    nyq = analisis.verificar_nyquist()
    escribir_json(nyq, config.DIR_INDICADORES / "nyquist.json")
    escribir_csv(analisis.sensibilidad_saturacion(staging, disp, espectro, telemetria),
                 config.DIR_INDICADORES / "sensibilidad_saturacion.csv")
    print(f"Análisis: Nyquist {nyq['veredicto']} (en el límite: {nyq['en_el_limite']}); "
          f"temperatura-piso rho parcial={temp['rho_parcial_orden']:.2f} p={temp['p_parcial']:.3f} "
          f"({temp['conclusion']})")


PASOS = [paso_calidad, paso_indicadores, paso_analisis]


def main() -> int:
    if not (config.DIR_STAGING / "capturas_crudas.csv").exists():
        print("ERROR: falta artefactos/staging/capturas_crudas.csv. Ejecute python -m espectro.extract")
        return 1
    for paso in PASOS:
        paso()
    return 0


if __name__ == "__main__":
    sys.exit(main())
