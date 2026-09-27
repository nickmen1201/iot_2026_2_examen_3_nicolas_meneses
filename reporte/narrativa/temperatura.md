La temperatura interna del sensor subió de forma casi continua durante la campaña, de **42,8 °C a
50,4 °C**. Es la temperatura del equipo, no la del aire, y está muy asociada al orden de adquisición
(ρ = 0,92) *(fuente: `artefactos/indicadores/temperatura_calidad.json`)*. Por eso no basta con comparar
temperatura y calidad directamente: el orden de captura también refleja el tiempo transcurrido, el
calentamiento del equipo y el cambio de lugar a lo largo de la ruta.

Como medida de calidad se usó el **piso de ruido** de cada captura (percentil 10 de sus 1024 bins),
porque el ruido térmico del receptor aumenta con la temperatura. Resultados, sin la captura 016, cuyo
espectro se descartó por saturación:

- La correlación directa entre temperatura y piso de ruido es débil y **no significativa**
  (ρ = 0,17; p = 0,19).
- Al controlar el orden de adquisición (correlación parcial de Spearman), la relación sigue siendo débil
  y **no significativa**. Además cambia de signo (ρ = −0,21; p = 0,11).

**Conclusión:** con estos datos **no se puede afirmar que la temperatura del sensor haya afectado la
calidad de las mediciones**. El resultado es *no concluyente*, no una prueba de que no haya efecto. La
figura de temperatura y piso de ruido *(fuente: `artefactos/figuras/temperatura_piso_ruido.png`)*
muestra por qué: el piso de ruido varía mucho de una captura a otra, sin seguir la subida lenta de la
temperatura. Esas variaciones se explican mejor por el entorno radioeléctrico de cada punto de la ruta
que por el calentamiento del equipo.

**Limitaciones:**

- Hay una sola ruta y 60 capturas. Con una sola ruta no se puede separar el efecto térmico del cambio de
  entorno.
- La temperatura solo varió unos 8 °C, lo que limita la capacidad de detectar un efecto.
- Una correlación, aunque fuera significativa, no demostraría causalidad.

Para responder la pregunta de forma definitiva haría falta repetir mediciones en un mismo punto con el
equipo a distintas temperaturas.
