**Recomendación a la ANE:**

- **Usar de preferencia el canal A (840-845 MHz) y el canal D (855-860 MHz).**
- **Evitar el canal C (850-855 MHz) y el canal B (845-850 MHz).**

*(fuente: `artefactos/indicadores/recomendacion.csv`)*

Los cuatro canales superan el umbral de −60 dBm: los cuatro están contaminados en términos absolutos.
Por eso la recomendación es **relativa**. "Usar" significa "la mejor opción disponible en la banda", no
"canal libre".

Justificación, a partir de los indicadores *(fuente: `artefactos/indicadores/indicadores_canal.csv`)*:

| Canal | Potencia media | Mediana | Capturas sobre el umbral |
|---|---|---|---|
| C | −10,7 dBm | −21,9 dBm | 100 % |
| B | −13,5 dBm | −39,9 dBm | 87 % |
| D | −24,8 dBm | −42,4 dBm | 85 % |
| A | −33,9 dBm | −44,1 dBm | 90 % |

- **C** es el más contaminado por los tres criterios: superó el umbral en todas las capturas.
- **B** contiene la frecuencia más contaminada de todo el sistema: **846,992 MHz**, con una media de
  −25,7 dBm *(fuente: `artefactos/indicadores/frecuencias_extremas.json`)*.
- **A** es el menos contaminado. Contiene la frecuencia menos contaminada, **843,496 MHz**
  (−60,5 dBm), la única cuya media queda por debajo del umbral.

**El orden de los canales es robusto.** Por potencia media y por mediana sale el mismo orden
(C > B > D > A), y reincorporar el espectro descartado de la captura 016 tampoco lo cambia
*(fuente: `artefactos/indicadores/sensibilidad_saturacion.csv`)*.

**Advertencia:** los dos canales recomendados están en los bordes de la banda. Allí el muestreo está
exactamente en el límite de Nyquist y el filtro antialiasing puede atenuar la señal (sección 3). Esto
puede **subestimar** la potencia de A y de D. Antes de asignar estos canales convendría confirmarlos con
una medición centrada en cada uno de ellos.
