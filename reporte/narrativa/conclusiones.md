1. **Los datos son confiables tras una limpieza mínima y documentada.** De 61 capturas, 59 se aceptaron
   sin cambios.
   - A la captura 008 se le imputó la posición por interpolación lineal: 3 valores, ±630 m.
   - El espectro de la captura 016 se descartó por posible saturación del receptor: su piso de ruido
     estaba 35,6 dB sobre la mediana. Su telemetría sí se conservó.
   - La captura 017 se conservó, marcada como posición de baja confianza.

   *(fuente: `artefactos/calidad/reporte_calidad.csv`, `artefactos/calidad/resumen_imputacion.json`)*

2. **Toda la banda 840-860 MHz está ocupada por encima de −60 dBm.** El canal **C (850-855 MHz)** es el
   más contaminado (−10,7 dBm) y el canal **A (840-845 MHz)** el menos contaminado (−33,9 dBm). Se
   recomienda usar A y D y evitar C y B.
   *(fuente: `artefactos/indicadores/indicadores_canal.csv`)*

3. **Los valores más altos aparecen en el sur de la ruta**, entre Itagüí y Envigado. La captura 024 es
   la más fuerte en los canales A, B y C, y entre 3 y 5 de las 10 capturas más fuertes de cada canal
   están en el tramo 022-028. Las estimaciones de fuente de los cuatro canales caen en el sur del
   recorrido, pero son **estimaciones con incertidumbre de 2,2 a 2,7 km**, no ubicaciones medidas.
   Además, un centroide solo puede caer dentro de la zona recorrida, así que una fuente fuera de la
   ruta no se podría ubicar con este método.
   *(fuente: `artefactos/indicadores/potencia_canal_captura.csv`, `artefactos/indicadores/fuentes_estimadas.csv`)*

4. **El muestreo cumple el criterio de Nyquist, exactamente en el límite** (f_s = 2·f_max = 20 MS/s).
   Los bordes de la banda, es decir el extremo inferior de A y el superior de D, son los resultados
   menos confiables. *(fuente: `artefactos/indicadores/nyquist.json`)*

5. **No se encontró evidencia de que la temperatura del sensor afectara la calidad de la medición.** Al
   controlar el orden de adquisición la relación no es significativa (ρ parcial = −0,21; p = 0,11), y el
   resultado es no concluyente. *(fuente: `artefactos/indicadores/temperatura_calidad.json`)*

6. **Limitaciones principales:**
   - Los niveles no están calibrados, y el espectro es el máximo retenido (max-hold) de 100 FFT. Eso
     sesga hacia arriba las potencias absolutas; la comparación entre canales se ve menos afectada.
   - La media de cada canal está dominada por unas pocas capturas muy fuertes. Por eso se reportan
     también la mediana y el porcentaje de capturas sobre el umbral.
   - Las capturas no tienen marca de tiempo.
