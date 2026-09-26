# Implementation Plan: Spectrum Occupancy Analysis and Dashboard (840-860 MHz, Medellin)

**Branch**: `001-spectrum-occupancy-analysis` | **Date**: 2026-09-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-spectrum-occupancy-analysis/spec.md`

## Summary

This is a file-based ETL pipeline in Python 3.12. It turns the 61 raw captures in `medidas_2026_20/`
into curated CSV/JSON artifacts, a quality report, channel indicators computed by Parseval
summation, nine self-contained Folium maps (eight required plus the bonus source map), and a Spanish HTML report. A single
Streamlit process on an EC2 t3.micro serves the dashboard on port 8050, reading only those
artifacts. The load stage runs `aws s3 sync` twice: once to push the artifacts to an S3 datalake
bucket, and once to publish the report and maps as an S3 static website backup. One command,
`python -m espectro.pipeline`, rebuilds everything from the raw data. Each stage
(`espectro.extract`, `espectro.transform`, `espectro.presentacion`, `espectro.load`) can also be
run on its own.

The work is capped at 3 hours, so the plan is the minimum that satisfies every FR and gate.
The source-location bonus (US5) is the last task.

## Technical Context

**Language/Version**: Python 3.12 (the version on the local dev machine and on Ubuntu 24.04)

**Primary Dependencies**: numpy, pandas, scipy (analysis); matplotlib (figures); folium +
branca (maps; jinja2 comes with folium and also renders the report); markdown (narrative
fragments); streamlit (dashboard); pytest (tests). All pinned in `requirements.txt`.

**Storage**: Files only. The artifacts go under `artefactos/` (gitignored, rebuilt by the pipeline). The
remote copy lives in S3 (a datalake bucket and a static-site bucket). No database.

**Testing**: pytest with a handful of unit tests on the physics and imputation rules, plus a
determinism check (build twice, hash the artifacts) documented in quickstart.

**Target Platform**: AWS Academy Learner Lab, EC2 t3.micro on Ubuntu Server 24.04 LTS
(system `python3` 3.12 from apt, AWS CLI from snap), with LabInstanceProfile, an Elastic IP and a systemd unit. Local
Windows for development.

**Project Type**: Batch data pipeline (CLI) plus a single-page web dashboard.

**Performance Goals**: Not a driver. There are 61 × 1024 values, and a full rebuild should take under 1 minute on t3.micro.

**Constraints**: 1 GB RAM on t3.micro (add a 1 GB swap before `pip install`); Learner Lab
sessions stop the instance (systemd `enable` + Elastic IP keep the URL stable); no containers,
no DB; relative data paths (the data ships with the repo); 3-hour budget.

**Scale/Scope**: 61 study captures + 2 test captures, 4 channels, 9 maps, 1 report, and a handful of reviewers.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / rule | How the plan satisfies it | Status |
|---|---|---|
| I. Data Quality Before Analysis | `transform` runs the quality step (`calidad.py`) first and writes `reporte_calidad.csv`, `hallazgos_calidad.csv` and `resumen_imputacion.json` before computing indicators. Indicators read only captures whose spectrum is usable. Discarded captures stay listed. No fill-with-zero, and interpolation is limited to gaps of 1 capture or 2 bins (FR-029). | PASS |
| II. Reproducible, Traceable ETL | Raw folder read-only; stages separately runnable via `python -m`; every intermediate persisted under `artefactos/`; no randomness (no seed needed; documented); `pipeline` = single rebuild command; pinned deps. | PASS |
| III. Physically Grounded Indicators | Bin→frequency map from `fftshift` (bin 512 = 850 MHz) in `config.py`; channels derived from frequency edges, not hard-coded indices; Parseval in linear mW; `UMBRAL_CONTAMINACION_DBM = -60.0` defined once in `config.py`. | PASS |
| IV. Evidence-Backed Recommendations | The report template puts a `Fuente: artefactos/...` line under every table, figure and number. The recommendation is computed from `indicadores_canal.csv`. The temperature section reports the partial Spearman correlation, its p-value, the limitation and the confound. Where the data is inconclusive, the template shows "no concluyente". | PASS |
| V. Dashboard as Delivery Surface | Streamlit app reads only `artefactos/` CSV/JSON + prebuilt map HTML; zero imports from `espectro.transform`; 9 maps each with branca legend (units + colour scale). | PASS |
| Data contract (1029 values) | `extract` validates the field count and finiteness, and flags malformed files without reshaping them. | PASS |
| Spanish comments/deliverables | Code comments, labels, report and narrative are in Spanish. The plan documents are in English, as the spec is. | PASS |
| Legacy scripts not run/modified | The pipeline only reads `*.txt`. `biblioteca.py`, `medir_celular.py` and `ANTENNA1.csv` are untouched. | PASS |
| Bonus mandatory, last, after 3 gates (v1.1.0) | `pipeline` always runs `espectro.fuentes` after the three gate checks pass and before `load`. It is built last. | PASS |
| Simplest pipeline (Governance) | Flat package, no framework and no DB. Streamlit was picked over Dash (see research R2). | PASS |

**Post-design re-check (after Phase 1)**: PASS. The design adds no violations, so Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-spectrum-occupancy-analysis/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1-R14
├── data-model.md        # Phase 1: entities + artifact schemas
├── quickstart.md        # Phase 1: local run, validation, EC2 + S3 deployment
├── contracts/
│   ├── cli.md           # Stage commands, exit codes, env vars
│   ├── artefactos.md    # File layout and column contracts (pipeline ⇄ dashboard/report)
│   └── dashboard.md     # Views, labels, units, colour scales
└── tasks.md             # Phase 2 (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
requirements.txt                 # versiones fijadas
espectro/                        # paquete del pipeline (se ejecuta desde la raíz del repo)
├── __init__.py
├── config.py                    # rutas relativas, eje de frecuencia, canales, UMBRAL (-60 dBm, única definición), límites
├── extract.py                   # lee *.txt → artefactos/staging/, valida contrato de 1029 valores
├── calidad.py                   # disposiciones, límites de plausibilidad, interpolación, saturación
├── indicadores.py               # Parseval por captura/canal, agregados, frecuencias extremas, recomendación
├── analisis.py                  # ruta, temperatura vs piso de ruido (Spearman parcial), Nyquist, sensibilidad 016
├── transform.py                 # orquesta calidad → indicadores → analisis; escribe curado/, calidad/, indicadores/
├── mapas.py                     # 8 mapas Folium autocontenidos → artefactos/sitio/mapas/
├── reporte.py                   # figuras matplotlib + HTML (jinja2) → artefactos/sitio/index.html
├── presentacion.py              # orquesta mapas + reporte
├── load.py                      # aws s3 sync (datalake + sitio estático); omite si no hay bucket configurado
├── fuentes.py                   # BONUS (obligatorio, último): estimación de fuente por canal → mapas/fuentes.html
├── pipeline.py                  # reconstrucción completa: extract → transform → presentacion → gates → fuentes → load
└── plantillas/reporte.html.j2
reporte/narrativa/               # texto interpretativo del analista (Markdown, versionado)
├── ruta.md  temperatura.md  recomendacion.md  conclusiones.md
dashboard/app.py                 # Streamlit; solo lee artefactos/
deploy/espectro-dashboard.service  # unidad systemd
tests/test_fisica.py  tests/test_calidad.py
artefactos/                      # generado (gitignored)
README.md                        # comandos exactos de despliegue EC2 + S3
```

**Structure decision**: one flat Python package at the repo root. It runs with `python -m` and
needs no install step or PYTHONPATH changes, which keeps the EC2 steps short. The dashboard is a
separate top-level folder so that it cannot accidentally import transform logic (Principle V).
The analyst's narrative lives outside `artefactos/`, so rebuilds never overwrite it.

## Execution order within the 3-hour budget

| Block | Content | Budget |
|---|---|---|
| 1 | `config`, `extract`, `calidad` + tests → **Quality gate** | 45 min |
| 2 | `indicadores`, `analisis` → **Indicator gate** | 35 min |
| 3 | `mapas`, `reporte` (figures, template, narrative stubs) | 45 min |
| 4 | `dashboard/app.py`, `load`, `pipeline`, README deploy section → **Presentation gate** | 25 min |
| 5 | EC2 + S3 deployment following quickstart | 20 min |
| 6 | `fuentes.py` bonus (mandatory, last) | remainder |

## Complexity Tracking

No violations.
