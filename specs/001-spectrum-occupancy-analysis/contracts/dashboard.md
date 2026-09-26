# Contract: Dashboard views (Streamlit, port 8050)

This is a single page. Every label is in Spanish (FR-026). The page reads only the artifacts
listed in [artefactos.md](artefactos.md).

## Header: the decision (always visible, SC-004)

- Title: "Ocupación del espectro 840-860 MHz — Medellín".
- One `st.metric` per channel A-D showing `potencia_media_dbm` and the delta against −60 dBm. The
  label reads `CONTAMINADO`, `LIBRE` or `INDETERMINADO`. The metrics are laid out in columns and
  stack on a phone.
- A line naming the most and the least contaminated channel with their dBm values, and the most
  and least contaminated frequency (MHz, dBm).
- A recommendation table (canal, recomendación, estado, potencia media dBm), taken from `recomendacion.csv`.
  A note states that the rule is relative (the 2 least contaminated channels → usar).
- A collapsible "Calidad de datos y Nyquist" section: the totals of corrected and imputed values,
  the discarded captures and the Nyquist verdict.
- A link to the static report on S3, when `ESPECTRO_URL_REPORTE` is set.

## Map tabs (`st.tabs`, each embedding `sitio/mapas/<file>.html` at height 560)

| Tab | File | Value shown | Unit / legend caption | Colour scale |
|---|---|---|---|---|
| Ubicaciones | `ubicaciones.html` | capture points, tooltip with id and state | — ; legend: medida / imputada / baja confianza | categorical |
| Ruta | `ruta.html` | polyline in capture order, start and end markers | — ; the legend states the ordering basis | single colour |
| Canal A…D (4 tabs) | `canal_X.html` | Parseval channel power per capture | "Potencia canal X (dBm)" | `LinearColormap` YlOrRd, fixed range shared by A-D, −60 dBm tick |
| Temperatura | `temperatura.html` | internal sensor temperature | "Temperatura interna del sensor (°C)" | `LinearColormap` Blues→Reds |
| Frecuencia más contaminada | `frecuencia_mas_contaminada.html` | power at bin f* for each capture | "Potencia a f* = xxx.xxx MHz (dBm)" | YlOrRd |
| Fuentes (estimación) | `fuentes.html` | one estimated source per channel, uncertainty circle, route for context | "Estimación de fuente por canal (radio = incertidumbre, m)" | one colour per channel (categorical) |

Rules:
- Captures with `estado_posicion = excluida` are absent from every map (FR-021).
- Imputed positions are drawn with a dashed black outline and are labelled in the legend.
- If an artifact is missing, the dashboard shows `st.error("Falta artefacto: <ruta>. Ejecute python -m espectro.pipeline")`.
  It never computes a fallback value.
- Reloading the browser picks up new artifacts. Loads are cached with `st.cache_data(ttl=60)` at most.
