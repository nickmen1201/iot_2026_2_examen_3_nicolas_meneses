---

description: "Task list for Spectrum Occupancy Analysis and Dashboard (840-860 MHz, Medellin)"
---

# Tasks: Spectrum Occupancy Analysis and Dashboard (840-860 MHz, Medellin)

**Input**: Design documents from `specs/001-spectrum-occupancy-analysis/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: A few pytest unit tests on the physics and on the imputation rules. The plan asks for
them (`tests/test_fisica.py`, `tests/test_calidad.py`), and they are small by design to fit the
3-hour budget. End-to-end checks are the checkpoint tasks and the quickstart validation scenarios V1-V7.

**Organization**: Tasks are grouped by user story. US1-US4 follow spec priority. The pipeline,
load and deployment work comes next, as a cross-cutting phase. US5 (the bonus) is built last,
as FR-027 and constitution v1.1.0 require.

**Conventions for every task**: Python 3.12. Code comments, docstrings, labels and report text are in
Spanish. Every path is resolved through `espectro/config.py`, with no absolute paths and no
reliance on the working directory. Every stage module exposes `main()` and ends with
`if __name__ == "__main__": raise SystemExit(main())`. `medidas_2026_20/` is never written to.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1-US5 from spec.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Repository skeleton and pinned environment.

- [X] T001 Create the package skeleton at the repo root: `espectro/__init__.py` (a one-line Spanish docstring), empty directories `espectro/plantillas/`, `dashboard/`, `deploy/`, `reporte/narrativa/` and `tests/`, and an empty `tests/__init__.py`
- [X] T002 [P] Create `requirements.txt` with pinned versions that are compatible with Python 3.12 and have wheels: `numpy==2.1.3`, `pandas==2.2.3`, `scipy==1.14.1`, `matplotlib==3.9.2`, `folium==0.18.0`, `branca==0.8.0`, `jinja2==3.1.4`, `markdown==3.7`, `streamlit==1.40.1`, `pytest==8.3.3`
- [X] T003 [P] Create `.gitignore` with `artefactos/`, `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `h1`, `h2` (the files `biblioteca.pyc` already tracked in `medidas_2026_20/` stay as they are)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Constants and deterministic I/O used by every stage.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Implement `espectro/config.py` with every constant in the data-model.md "Constants" table:
  - `RAIZ = Path(__file__).resolve().parents[1]`, and `DIR_MEDIDAS`, `DIR_ARTEFACTOS` and its subfolders `DIR_STAGING`, `DIR_CALIDAD`, `DIR_CURADO`, `DIR_INDICADORES`, `DIR_FIGURAS`, `DIR_SITIO`, `DIR_MAPAS` (= `DIR_SITIO/"mapas"`), plus `DIR_NARRATIVA` (= `RAIZ/"reporte"/"narrativa"`) and `DIR_PLANTILLAS`.
  - `N_BINS = 1024`, `FC_HZ = 850e6`, `FS_HZ = 20e6`, `F_MAX_HZ = 10e6`, and `FRECUENCIAS_MHZ = 850 + (np.arange(1024) - 512) * 20 / 1024`.
  - `CANALES = {"A": (840.0, 845.0), …, "D": (855.0, 860.0)}` and a function `bins_canal(canal) -> np.ndarray`, which returns the indices where `f_ini <= FRECUENCIAS_MHZ < f_fin`.
  - `UMBRAL_CONTAMINACION_DBM = -60.0`, with a comment stating this is the only place it is defined.
  - A `LIMITES` dict (`lat` (6.0, 6.5), `lon` (-75.8, -75.4), `alt_m` (1300, 2800), `temp_c` (-10, 85), `dbm` (-160, 30), `error_dist_max` 5.0), `MAX_HUECO_BINS = 2`, `MAX_HUECO_CAPTURAS = 1`, `UMBRAL_SATURACION_DB = 30.0` and `PATRON_ESTUDIO = r"^\d{3}\.txt$"`.
  - `N_CAPTURAS_TOTAL = 63`, `N_CAPTURAS_ESTUDIO = 61`.
  - The map file names `MAPAS_REQUERIDOS` (the 8 names from contracts/artefactos.md) and `MAPA_FUENTES = "fuentes.html"`.
- [X] T005 Implement `espectro/utilidades.py` with the deterministic I/O helpers from research R4:
  - `asegurar_dir(p)`.
  - `escribir_csv(df, ruta)`, which calls `to_csv(index=False, float_format="%.6f", lineterminator="\n", encoding="utf-8")`.
  - `escribir_json(obj, ruta)`, with `sort_keys=True, indent=2, ensure_ascii=False`, and numpy types converted to native types.
  - `leer_csv(ruta)` and `leer_json(ruta)`, which raise a Spanish `FileNotFoundError("Falta artefacto: …")` when the file is missing.
  - `haversine_m(lat1, lon1, lat2, lon2)`.
  - `dbm_a_mw(x) = 10**(x/10)` and `mw_a_dbm(x) = 10*log10(x)`.
- [X] T006 [P] Write `tests/test_fisica.py::test_eje_y_canales`. It asserts that bin 0 = 840.0 MHz, bin 512 = 850.0 MHz and bin 1023 ≈ 859.98047 MHz, that each `bins_canal` returns 256 contiguous indices (A 0-255, B 256-511, C 512-767, D 768-1023), and that `UMBRAL_CONTAMINACION_DBM == -60.0`

**Checkpoint**: `python -m pytest -q` passes.

---

## Phase 3: User Story 1 - Trustworthy measurement set with a quality verdict (Priority: P1) 🎯 MVP

**Goal**: Turn the raw captures into staging, a curated set and a quality report. The report
gives every file one disposition and totals the corrected and imputed values.

**Independent Test**: Run `python -m espectro.extract && python -m espectro.transform`.
`artefactos/calidad/reporte_calidad.csv` must have 63 rows, each with exactly one disposition and
a reason. `resumen_imputacion.json` must hold non-negative totals. A second run must produce
byte-identical files.

- [X] T007 [US1] Implement `espectro/extract.py`:
  - Read the files `sorted(DIR_MEDIDAS.glob("*.txt"))`, strip each line and split it on `,`.
  - Record `n_campos`. Set `contrato_ok = (n_campos == 1029 and every field parses as float)`. Non-finite values such as `nan`/`inf` count as parsed, and `calidad` checks finiteness bin by bin. When the contract fails, set `motivo_contrato` and fill the values with NaN, without reshaping anything.
  - Build the columns `id_captura` (the stem), `archivo`, `es_estudio` (from `PATRON_ESTUDIO`), `p_0000…p_1023`, `temperatura_c`, `longitud`, `latitud`, `altitud_m` and `error_distancia`.
  - Write `artefactos/staging/capturas_crudas.csv` through `escribir_csv`.
  - Return 1 with a Spanish message when `DIR_MEDIDAS` is missing or no study file matches.
- [X] T008 [US1] Implement `espectro/calidad.py` with pure functions over DataFrames, following research R5 and data-model.md:
  - (a) `reparar_espectro(valores) -> (valores_reparados, hallazgos, n_corregidos, utilizable)`: a bin is invalid when it is non-finite or outside `LIMITES["dbm"]`. Invalid runs are found by run-length. A run of `<= MAX_HUECO_BINS` with a valid neighbour on both sides is repaired with `np.interp`. A longer run, or one that touches bin 0 or 1023, makes the spectrum unusable.
  - (b) `evaluar_saturacion(df_estudio)`: the noise floor is `np.percentile` p10 over the 1024 raw bins, computed only for captures that passed the contract. `delta_piso_db` is measured against the study median. A capture with `delta > UMBRAL_SATURACION_DB` has its spectrum discarded and gets a finding with rule `saturacion_receptor`.
  - (c) `evaluar_posiciones(df_estudio)`: order the captures by `orden = int(id_captura)`. A position is invalid when lon, lat and alt are all 0, or when any of them is outside `LIMITES`. A single invalid capture whose previous and next captures are both valid gets the midpoint of those neighbours for lon, lat and alt (linear interpolation with t = 0.5). It is then `estado_posicion = "imputada"`, `incertidumbre_posicion_m = haversine(vecinos)/2` and 3 values imputed. Any other invalid capture is `"excluida"`. A capture with `error_distancia > LIMITES["error_dist_max"]` is `"baja_confianza"` and gets a finding that records the bound; its coordinates are kept. Every other capture is `"medida"`, with uncertainty 0.
  - (d) Flag temperatures outside `LIMITES["temp_c"]`, without imputing them.
  - (e) `asignar_disposiciones(...)`: produce one row per file (63). The test files get `excluido_prueba`. The rest take the precedence `descartado > imputado > corregido > aceptado`. Fill `alcance` (`total` for a contract failure, `espectro` when only the spectrum is discarded, `posicion` for imputed or excluded positions), `motivo`, `tecnica`, `n_valores_modificados`, `espectro_utilizable` and `posicion_utilizable`.
  - (f) `resumen_imputacion(...)`: a dict with `total_corregidos` and `total_imputados`, and one entry per field and technique holding `tecnica`, `n_valores` and a Spanish `justificacion` (FR-006, SC-011).
  - Never fill with zero, and never use a mean or median (FR-029).
- [X] T009 [US1] Write `tests/test_calidad.py` on synthetic frames. Cases:
  - 2 consecutive NaN bins are interpolated and the capture is `corregido`.
  - 3 consecutive NaN bins make the spectrum unusable.
  - A zero position between two valid neighbours is imputed to the midpoint, with its uncertainty > 0.
  - Two consecutive zero positions are both `excluida`.
  - A noise floor 31 dB above the median makes the spectrum `descartado` with `alcance="espectro"`, while `posicion_utilizable` stays true.
  - A test file is `excluido_prueba`.
- [X] T010 [US1] Implement `espectro/transform.py`, step 1:
  - `main()` reads `staging/capturas_crudas.csv`. It returns 1 if the file is missing.
  - It runs the `calidad` functions and writes `calidad/reporte_calidad.csv`, `calidad/hallazgos_calidad.csv`, `calidad/resumen_imputacion.json`, `curado/telemetria.csv` (61 rows, columns as in data-model.md) and `curado/espectro.csv`. The spectrum file holds only the rows with `espectro_utilizable`, with columns `id_captura` plus `f_{freq:.6f}`.
  - Structure `main()` as a sequence of step functions, so that US2 and US4 can append their own.
- [X] T011 [US1] Checkpoint (**Quality gate**): run extract and transform, and confirm these results:
  - 63 rows in the report.
  - `008` is `imputado`, with uncertainty ≈ 600 m.
  - `016` is `descartado` with scope `espectro`.
  - `017` is `aceptado` and has a `baja_confianza` finding.
  - Both `medidaprueba*` files are `excluido_prueba`.
  - Running it twice gives identical sha256 hashes for `staging/`, `calidad/` and `curado/`.
  - `python -m pytest -q` passes.

  Fix any failure at its root cause (constitution).

**Checkpoint**: US1 is independently usable, and the question "can we trust the data?" is answered.

---

## Phase 4: User Story 2 - Channel contamination indicators and ranking (Priority: P2)

**Goal**: Parseval channel powers per capture, 4 channel indicators, a ranking, the extreme
frequencies and the relative recommendation.

**Independent Test**: After `python -m espectro.transform`, `indicadores/indicadores_canal.csv`
must have 4 rows, each with a power in dBm, a state and a rank. `frecuencias_extremas.json` must
name 2 frequencies, and `recomendacion.csv` must have 2 `usar` and 2 `evitar`.

- [X] T012 [US2] Implement `espectro/indicadores.py` (FR-010 to FR-014 and FR-025, research R6), importing the threshold only from `config`:
  - `potencia_canal_captura(espectro, telemetria)`: for each capture and channel, `potencia_dbm = mw_a_dbm(sum(dbm_a_mw(bins_canal)))` and `supera_umbral = potencia_dbm > UMBRAL_CONTAMINACION_DBM`. The result is a long frame joined with `latitud`, `longitud` and `estado_posicion`.
  - `indicadores_canal(pcc)`: `n_capturas`, `potencia_media_dbm = mw_a_dbm(mean(dbm_a_mw(potencia_dbm)))`, `potencia_mediana_dbm`, `pct_capturas_sobre_umbral`, and `estado` (`contaminado`/`libre`, or `indeterminado` with empty numbers when `n_capturas == 0`). `rango` is 1 for the highest power, and channels with no data have no rank.
  - `potencia_por_frecuencia(espectro)`: the linear mean for each bin, then dBm (1024 rows).
  - `frecuencias_extremas(ppf)`: the argmax and argmin, each with `bin`, `frecuencia_mhz` and `potencia_dbm`.
  - `recomendacion(ind)`: rank the channels that have data by `potencia_media_dbm`. The lower half gets `usar` and the upper half gets `evitar`. A channel without data gets `sin_datos`. Include `estado`, `rango` and `indicador_base`, and the Spanish `regla` text from data-model.md.
- [X] T013 [P] [US2] Add these tests to `tests/test_fisica.py`:
  - A 256-bin channel at −90 dBm gives Parseval ≈ −65.918 dBm.
  - The linear mean of −50 and −70 dBm ≈ −52.967 dBm (not −60).
  - A channel with zero captures is `indeterminado`.
  - `recomendacion` on 4 channels gives exactly 2 `usar`, the two lowest.
- [X] T014 [US2] Extend `espectro/transform.py` with step 2. It reads `curado/espectro.csv` and `curado/telemetria.csv`, and writes `indicadores/potencia_canal_captura.csv`, `indicadores_canal.csv`, `potencia_por_frecuencia.csv`, `frecuencias_extremas.json` and `recomendacion.csv`
- [X] T015 [US2] Checkpoint (**Indicator gate**): after `python -m espectro.transform`, check these results:
  - 4 rows (A-D) with ranks 1 and 4 assigned.
  - The recommendation is 2 `usar` and 2 `evitar`.
  - For one capture, the value in `potencia_canal_captura.csv` matches a manual Parseval sum computed from `curado/espectro.csv`.
  - The indicator files are identical across two runs.

  Then run `python -m pytest -q`.

**Checkpoint**: the ANE's question (which channel is worst and which is cleanest) is answered as a table.

---

## Phase 5: User Story 3 - Interactive dashboard for the ANE (Priority: P3)

**Goal**: 8 required Folium maps plus a Streamlit dashboard that shows the decision and the maps, reading artifacts only.

**Independent Test**: `python -m espectro.presentacion` writes 8 files to `artefactos/sitio/mapas/`.
`streamlit run dashboard/app.py --server.port 8050` shows the verdict header and 8 map tabs,
each with a legend giving the unit and the colour scale. Captures with `excluida` positions are absent, and `008` is visibly marked as imputed.

- [X] T016 [US3] Implement the helpers in `espectro/mapas.py` (research R3, contracts/dashboard.md):
  - `mapa_base(df)` is `folium.Map(location=centroid, zoom_start=14, tiles="OpenStreetMap")`.
  - `capa_valores(m, df, columna, vmin, vmax, cmap, leyenda, unidad)` adds a `plugins.HeatMap` with weights `(v - vmin)/(vmax - vmin)` clipped to [0, 1] and a gradient sampled from `cmap`. It also adds a `CircleMarker` for each point, filled with `cmap(v)` and with a tooltip that shows `id_captura`, the value with its unit, and the position state. Imputed points get `color="black", dash_array="5,5"`. Both layers go into `FeatureGroup`s under a `LayerControl`, and `cmap.caption = leyenda` is added to the map.
  - `leyenda_estados(m)` adds a small fixed HTML legend (`folium.Element`) explaining medida, imputada and baja confianza.
  - Every function drops the rows with `estado_posicion == "excluida"` before drawing (FR-021).
- [X] T017 [US3] Implement `mapas.generar_mapas()` in `espectro/mapas.py`. It writes the 8 files in `config.MAPAS_REQUERIDOS` to `DIR_MAPAS`:
  - `ubicaciones.html`: categorical colours by `estado_posicion`, plus the state legend.
  - `ruta.html`: a `PolyLine` in `orden`, with "Inicio" and "Fin" markers and a legend with the ordering basis text from data-model.md.
  - `canal_A…D.html`: read from `indicadores/potencia_canal_captura.csv`. Use one shared `vmin`/`vmax` (the floor and ceiling of the power across all channels) and a YlOrRd `LinearColormap`. The tick labels include `UMBRAL_CONTAMINACION_DBM`, and the caption is `"Potencia canal X (dBm)"`.
  - `temperatura.html`: from `curado/telemetria.csv`, a blue→red scale with the caption `"Temperatura interna del sensor (°C)"`.
  - `frecuencia_mas_contaminada.html`: the bin comes from `frecuencias_extremas.json`, and the values from that `f_…` column of `curado/espectro.csv`, joined to the telemetry. The caption is `"Potencia a f* = xxx.xxx MHz (dBm)"`.

  Add Spanish comments throughout.
- [X] T018 [US3] Implement `espectro/presentacion.py`. `main()` checks that the inputs it needs exist, returning 1 with the message "Falta artefacto: …" when one is missing. It then calls `mapas.generar_mapas()`, and later `reporte.generar_reporte()`, which is added in T027.
- [X] T019 [US3] Implement `dashboard/app.py`, following contracts/dashboard.md:
  - Start with `sys.path.insert(0, str(Path(__file__).resolve().parents[1]))` and import **only** `espectro.config`, for paths and the threshold. Never import `calidad`, `indicadores` or `transform` (FR-019).
  - Add loaders for CSV, JSON and HTML wrapped in `st.cache_data(ttl=60)`. A missing file produces `st.error("Falta artefacto: <ruta>. Ejecute python -m espectro.pipeline")` and `st.stop()`.
  - Use `st.set_page_config(layout="wide")` and the Spanish title.
  - Show 4 `st.metric` columns (value in dBm, the delta against the threshold, and the state label).
  - Add a line naming the most and least contaminated channel and frequency.
  - Show the recommendation table with the note on the relative rule.
  - Add an `st.expander("Calidad de datos y Nyquist")` holding the totals from `resumen_imputacion.json`, the discarded captures from `reporte_calidad.csv`, and the verdict from `nyquist.json`.
  - Add a link to `ESPECTRO_URL_REPORTE` when it is set.
  - Add 8 `st.tabs` (Ubicaciones, Ruta, Canal A, B, C, D, Temperatura, Frecuencia más contaminada), each running `components.html(html, height=560)`.
- [X] T020 [US3] Checkpoint: run `python -m espectro.presentacion` and start Streamlit on port 8050. Check these results:
  - Every tab renders with its legend.
  - `008` has a dashed outline.
  - The most contaminated channel can be identified within 30 s (SC-004).
  - V4 passes: `grep -n "import" dashboard/app.py` shows no `calidad`, `indicadores` or `transform`.
  - V5 passes: edit `indicadores_canal.csv` by hand and reload, and the change shows. Rerun transform afterwards to restore the file.

  The Nyquist expander needs US4. Until then it shows the missing-artifact error, which is expected.

**Checkpoint**: the dashboard serves every required view locally.

---

## Phase 6: User Story 4 - Evidence pack for the written report (Priority: P4)

**Goal**: The route, temperature and quality, Nyquist and saturation-sensitivity evidence, 4 figures and the Spanish HTML report, in which every block cites its artifact.

**Independent Test**: `artefactos/sitio/index.html` has the sections listed in T025, and each block has a `Fuente:` path that exists on disk. The temperature section shows ρ, the partial ρ, p, the limitation and the confound. The Nyquist box reads "cumple (en el límite)".

- [X] T021 [US4] Implement `espectro/analisis.py`:
  - (a) `describir_ruta(telemetria)` (research R8): use only the rows with `posicion_utilizable`, sorted by `orden`. It returns `base_ordenamiento`, `inicio` and `fin`, `longitud_km` (the haversine sum), `bbox`, `n_puntos`, `n_imputados`, `n_excluidos` and `pares_estacionarios` (consecutive points with identical coordinates).
  - (b) `temperatura_vs_calidad(telemetria, disposiciones)` (research R7): use the captures with `espectro_utilizable`. Report `rho_spearman` and `p_spearman` from `scipy.stats.spearmanr(temp, piso)` and `rho_temp_orden`. For the partial Spearman controlled for `orden`, rank all three variables, take the residuals of the temp and piso ranks after a linear regression on the order rank (`np.polyfit`), and compute the Pearson correlation of the residuals. The p-value comes from `t = r*sqrt((n-3)/(1-r²))` and `scipy.stats.t.sf` two-sided with n − 3 degrees of freedom. `conclusion` is `"no concluyente"` when `p_parcial >= 0.05`. Add a Spanish `limitacion` text that covers the confound with order, the fact that the reading is internal and not ambient temperature, and correlation versus causation.
  - (c) `verificar_nyquist()` (research R9): return `fs_hz`, `f_max_hz`, `veredicto` (`"cumple"` if `FS_HZ >= 2*F_MAX_HZ`, else `"no_cumple"`), `en_el_limite` and a Spanish `implicaciones` text about the anti-aliasing roll-off at the lower edge of channel A and the upper edge of channel D. It never raises.
  - (d) `sensibilidad_saturacion(staging, disposiciones, pcc_sin)`: recompute the channel indicators with the spectra discarded for saturation added back in, taking their raw values from `staging/capturas_crudas.csv` and reusing the functions in `indicadores`. For each channel it returns `potencia_media_dbm_sin_descartados`, `_con_descartados`, `delta_db` and `cambia_estado` (FR-030).
- [X] T022 [P] [US4] Add these tests to `tests/test_fisica.py`:
  - `verificar_nyquist()` returns `veredicto == "cumple"` and `en_el_limite is True`.
  - The partial Spearman on synthetic data, where x and y are both built from z plus independent noise (fixed seed), gives |ρ_parcial| < 0.3 while the zero-order |ρ| > 0.7.
- [X] T023 [US4] Extend `espectro/transform.py` with step 3. It writes `indicadores/ruta.json`, `temperatura_calidad.json`, `nyquist.json` and `sensibilidad_saturacion.csv`
- [X] T024 [US4] Implement `generar_figuras()` in `espectro/reporte.py`. Call `matplotlib.use("Agg")`, give every axis a Spanish label with its unit, and save with `savefig(..., dpi=120, metadata={"Software": None})` to `DIR_FIGURAS`. The four figures:
  - (1) `espectro_medio.png`: the power per frequency, a threshold line, the channel boundaries and labels A-D, and the max and min frequencies annotated.
  - (2) `frecuencias_extremas.png`: two panels showing the power per capture (x = orden) at the most and at the least contaminated frequency, with the threshold line (FR-013).
  - (3) `temperatura_piso_ruido.png`: temperature and noise floor against `orden` on twin axes, with 016 marked.
  - (4) `potencia_canales.png`: bars of `potencia_media_dbm` per channel, the threshold line, and bar colours by state.
- [X] T025 [P] [US4] Create `espectro/plantillas/reporte.html.j2`, a Spanish, mobile-friendly HTML file with inline CSS. The sections:
  1. Resumen y decisión
  2. Datos y calidad (dispositions table, imputation totals with technique and justification, SC-011)
  3. **Verificación de Nyquist**, as a highlighted box with the verdict and implications (SC-010)
  4. Indicadores por canal (table + fig 4)
  5. Frecuencias más y menos contaminadas (fig 1 + fig 2)
  6. Sensibilidad a la saturación (016)
  7. Ruta (numbers + `narrativa.ruta` + link `mapas/ruta.html`)
  8. Temperatura y calidad (statistics + limitation + fig 3 + `narrativa.temperatura`)
  9. Recomendación (table + `narrativa.recomendacion`)
  10. Limitaciones (max-hold uncalibrated levels, edges at the Nyquist limit, ordering without timestamps)
  11. Mapas interactivos (links to each `mapas/*.html`)
  12. Estimación de fuentes (rendered only `{% if fuentes %}`)
  13. Conclusiones (`narrativa.conclusiones`)

  Every table, figure and number block ends with `<p class="fuente">Fuente: {{ ruta }}</p>`.
- [X] T026 [P] [US4] Create the narrative stubs `reporte/narrativa/ruta.md`, `temperatura.md`, `recomendacion.md` and `conclusiones.md`. Each holds a single line `PENDIENTE: redactar <tema> (el analista).`, so the gap stays visible in the report until the analyst writes it.
- [X] T027 [US4] Implement `generar_reporte()` in `espectro/reporte.py`:
  - Call `generar_figuras()`.
  - Load every artifact listed for `reporte.py` in contracts/artefactos.md.
  - Embed the PNGs as base64 `data:` URIs and render the tables with `DataFrame.to_html(index=False)`.
  - Convert each narrative file with `markdown.markdown`. A missing file renders a `PENDIENTE: redactar` box.
  - Pass `fuentes` only when `indicadores/fuentes_estimadas.csv` exists.
  - Render the template with jinja2 (`FileSystemLoader(DIR_PLANTILLAS)`) to `DIR_SITIO/"index.html"`.
  - Return the list of cited `Fuente:` paths, for the presentation gate.

  Then wire it into `espectro/presentacion.py`.
- [X] T028 [US4] Checkpoint: run `python -m espectro.transform && python -m espectro.presentacion`, open `artefactos/sitio/index.html`, and check these results:
  - All 4 figures render.
  - The Nyquist box is prominent.
  - Every `Fuente:` path exists (SC-006).
  - The map links resolve.
  - The dashboard Nyquist expander now renders.

**Checkpoint**: every required report element has a backing artifact.

---

## Phase 7: Pipeline, load and deployment (cross-cutting, required before US5)

**Purpose**: Build everything with a single command (FR-016), add the S3 load stage (research R11), and deploy to the cloud (FR-031, quickstart §3-6).

- [X] T029 [P] Implement `espectro/load.py`. It builds `aws s3 sync <DIR_ARTEFACTOS>/ s3://$ESPECTRO_BUCKET_DATALAKE/espectro/ --exclude "sitio/*" --delete` and `aws s3 sync <DIR_SITIO>/ s3://$ESPECTRO_BUCKET_SITIO/ --delete`, and runs each with `subprocess.run([...], check=True)`. When a variable is unset, it prints `"Carga a <destino> omitida: variable no definida"` and skips that sync. It returns 0 when every sync succeeds or is skipped. When the CLI fails (`CalledProcessError`) or `aws` is not found (`FileNotFoundError`), it returns 1.
- [X] T030 Implement `espectro/pipeline.py`:
  - Parse `argparse` with a `--sin-carga` flag.
  - Run `extract.main()`, `transform.main()` and `presentacion.main()` in order, stopping at the first non-zero exit code.
  - Run the three gate checks from contracts/cli.md as functions `gate_calidad()`, `gate_indicadores()` and `gate_presentacion()`, and print a Spanish PASA/FALLA line for each.
  - If a gate fails, return 2 and skip the rest.
  - If `importlib.util.find_spec("espectro.fuentes")` is found, run `fuentes.main()`. This is the bonus, which always runs after the gates (FR-027).
  - Unless `--sin-carga` is passed, run `load.main()`.
- [X] T031 [P] Create `deploy/espectro-dashboard.service` exactly as in quickstart.md §4 (`User=ubuntu`, `WorkingDirectory=/home/ubuntu/iot`, the `ESPECTRO_URL_REPORTE` environment variable, the Streamlit `ExecStart` on 0.0.0.0:8050, `Restart=always`, `WantedBy=multi-user.target`)
- [X] T032 Write `README.md` in Spanish. Replace the current one-line file with these sections:
  - Objective and structure (the tree from plan.md).
  - Requirements.
  - Local run (quickstart §1).
  - Commands per stage (contracts/cli.md).
  - Artifacts produced.
  - **Despliegue S3**, with the exact command sequence from quickstart §3.
  - **Despliegue EC2**, with the console steps and the exact command sequence from quickstart §4.
  - Update cycle (§5).
  - Deployment checks (§6).
  - The fallback when the lab denies the public bucket policy (research R13).
  - Dashboard and report URLs, as placeholders `<EIP>` and `<bucket>`.
- [X] T033 Run the local end-to-end validation:
  - `python -m espectro.pipeline --sin-carga` exits 0 and prints PASA for all 3 gates.
  - Quickstart V1 (stages run on their own), V2 (the determinism hash diff is empty), V3 (the threshold is defined once) and V6 (`git status medidas_2026_20` is clean).
  - `python -m pytest -q` passes.
- [ ] T034 Deploy as the analyst, working manually in the Learner Lab. Follow quickstart §3 to create the buckets and the static website, and §4 for the EC2 (Ubuntu 24.04, t3.micro, LabInstanceProfile, ports 22 and 8050, Elastic IP, swap, clone, venv, pipeline with the two bucket exports, systemd). Then run the §6 checks and V7 (open `http://<EIP>:8050` on a phone).

**Checkpoint**: **Presentation gate** passed. The dashboard is live at a fixed URL, and the artifacts are in the datalake and on the static site.

---

## Phase 8: User Story 5 - Contamination source location estimate (Priority: P5, bonus, mandatory, built last)

**Goal**: A labelled source estimate for each channel, or an explicit `no_soportado` marker, placed on its own map in the dashboard (FR-027, research R14).

**Independent Test**: With all 3 gates passing, `python -m espectro.pipeline --sin-carga` writes `indicadores/fuentes_estimadas.csv` (4 rows, each `estimado` or `no_soportado`, with its method and uncertainty) and `sitio/mapas/fuentes.html`. The dashboard shows a "Fuentes (estimación)" tab.

- [X] T035 [US5] Implement `espectro/fuentes.py` (research R14):
  - Read `indicadores/potencia_canal_captura.csv` and keep the rows with a usable position.
  - Project lat and lon to local metres with an equirectangular projection around the centroid.
  - For each channel, take the captures in the top quartile of `P_lin`. The estimate is their `P_lin`-weighted centroid, and the uncertainty is the weighted standard distance in metres.
  - Mark `no_soportado`, with empty coordinates, when fewer than 5 captures are above the channel median, or when the square root of the ratio of the largest to the smallest eigenvalue of the weighted covariance of the top-quartile positions is greater than 10.
  - `metodo` = `"centroide ponderado por potencia lineal (cuartil superior)"`.
  - Write `indicadores/fuentes_estimadas.csv` through `escribir_csv`.
  - Write `DIR_MAPAS/"fuentes.html"`: the route polyline for context, and for each estimated channel a `Marker` labelled `"Estimación canal X"` whose tooltip shows the method and uncertainty, plus a `Circle` with `radius = incertidumbre_m`, with one categorical colour per channel. Add a legend with the caption `"Estimación de fuente por canal (radio = incertidumbre, m)"` that lists the `no_soportado` channels.
  - `main()` returns 1 if an input is missing.
- [X] T036 [US5] Add the 9th tab, "Fuentes (estimación)", to `dashboard/app.py`, embedding `mapas/fuentes.html` and showing the `fuentes_estimadas.csv` table under it. The report section 12 in `espectro/plantillas/reporte.html.j2` is already conditional. To include it in the report, rerun `presentacion`, and then `fuentes`, which the pipeline does: T030 orders them presentacion → gates → fuentes. So `generar_reporte()` has to be called once more after `fuentes` whenever it produced output. Add that call to `espectro/pipeline.py` right after `fuentes.main()`.
- [ ] T037 [US5] Checkpoint and redeploy:
  - Run `python -m espectro.pipeline --sin-carga`. Check that `fuentes_estimadas.csv` has 4 rows, each estimate is labelled with its method and uncertainty, the map renders, and report section 12 is present.
  - On the EC2, run the update cycle from quickstart §5 (`git pull`, the pipeline with the bucket exports, `systemctl restart`), and confirm the tab at `http://<EIP>:8050`.

**Checkpoint**: every story, including the bonus, is delivered.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [X] T038 [P] Review `espectro/*.py` and `dashboard/app.py`. Every module needs a Spanish module docstring and Spanish comments at each non-obvious step (the constitution's development workflow), and every user-facing label must be in Spanish (FR-026)
- [X] T039 Run the final gate sweep: `python -m pytest -q`, quickstart V2 (determinism) and V3 (the threshold is defined once), and `python -m espectro.pipeline --sin-carga`, which must exit 0 with all gates at PASA
- [ ] T040 Hand-off to the analyst: write the interpretive narrative in `reporte/narrativa/ruta.md` (the neighbourhoods crossed, read from `mapas/ruta.html`), `temperatura.md`, `recomendacion.md` and `conclusiones.md`, citing the artifacts. Then rerun the pipeline on the EC2 (quickstart §5) so the S3 report is updated

---

## Dependencies & Execution Order

### Phase dependencies

```text
Setup (T001-T003)
  └─> Foundational (T004-T006)
        └─> US1 (T007-T011)  ── Quality gate
              └─> US2 (T012-T015)  ── Indicator gate
                    ├─> US3 (T016-T020)   (needs US2 artifacts for the channel maps)
                    └─> US4 (T021-T028)   (needs US2; T028 completes the US3 Nyquist expander)
                          └─> Phase 7 (T029-T034) ── Presentation gate + deployment
                                └─> US5 (T035-T037) ── bonus, built last
                                      └─> Polish (T038-T040)
```

### User story dependencies

- **US1**: depends only on Foundational. It is the MVP.
- **US2**: needs the curated artifacts from US1.
- **US3**: needs US1 (telemetry, position states) and US2 (channel powers, extreme frequency). It adds no analysis of its own.
- **US4**: needs US1 and US2. It can be built in parallel with US3, since they touch different files, except for `presentacion.py` (T018 then T027).
- **US5**: needs the three gates passing, so it comes after Phase 7 (constitution v1.1.0).

### Within each story

- `config`/`utilidades` → domain module → `transform.py` step → checkpoint.
- `transform.py` is edited in T010, T014 and T023. Those three edits are sequential.
- `tests/test_fisica.py` is edited in T006, T013 and T022, all sequential. They are marked [P] only against the module work in their own phase.

---

## Parallel Opportunities

- **Setup**: T002 ∥ T003.
- **Foundational**: T006 ∥ T005, once T004 is done.
- **US2**: T013 (tests) ∥ T012, since the function signatures are fixed in the task text.
- **US3 ∥ US4**: after T015, T016-T017 (`mapas.py`) can proceed alongside T021-T026 (`analisis.py`, `reporte.py`, template, narrative).
- **US4**: T022 ∥ T025 ∥ T026, all while T021/T024 are in progress.
- **Phase 7**: T029 ∥ T031 ∥ T032 (different files). T030 needs T029.

### Parallel example: US4

```text
Task: "T021 [US4] Implement espectro/analisis.py (ruta, temperatura, Nyquist, sensibilidad)"
Task: "T025 [P] [US4] Create espectro/plantillas/reporte.html.j2"
Task: "T026 [P] [US4] Create reporte/narrativa/*.md stubs"
Task: "T022 [P] [US4] Add Nyquist and partial-Spearman tests to tests/test_fisica.py"
```

---

## Implementation Strategy

### MVP first (3-hour budget, plan.md "Execution order")

1. Phases 1-3 (≈45 min): **stop and validate** the Quality gate (T011). This already answers "can we trust the data?".
2. Phase 4 (≈20 min): the Indicator gate. The core question for the ANE is answered as a table.
3. Phases 5 and 6 (≈60 min): the maps and dashboard, then the report evidence.
4. Phase 7 (≈35 min): one-command rebuild, S3 load, EC2 deployment. The URL is live.
5. Phase 8 (the remaining time): the bonus. Because the pipeline already loads to S3 and the service is running, delivering it is just the update cycle.
6. Phase 9: the gate sweep and the analyst's narrative.

### Scope guards

- Do not add a database, containers, nginx or cron (plan.md Constraints).
- Do not widen a plausibility bound or hard-code a result to make a gate pass (constitution Development Workflow).
- The dashboard never imports `calidad`, `indicadores` or `transform` (Principle V).
