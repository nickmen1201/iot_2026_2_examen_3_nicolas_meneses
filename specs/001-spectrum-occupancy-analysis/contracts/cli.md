# Contract: Pipeline CLI

Every command is run from the repository root. Paths are resolved relative to the package
(`espectro/config.py`), so the current working directory only matters for `python -m` resolution.

| Command | Reads | Writes | Exit code |
|---|---|---|---|
| `python -m espectro.extract` | `medidas_2026_20/*.txt` | `artefactos/staging/` | 0 on success, even when some files are malformed (they are flagged, not fatal); 1 if the data folder is missing or holds no study files |
| `python -m espectro.transform` | `artefactos/staging/` | `artefactos/curado/`, `artefactos/calidad/`, `artefactos/indicadores/` | 0; 1 if staging is missing |
| `python -m espectro.presentacion` | `curado/`, `calidad/`, `indicadores/`, `reporte/narrativa/*.md` | `artefactos/sitio/index.html`, `artefactos/sitio/mapas/*.html`, `artefactos/figuras/*.png` | 0; 1 if an input artifact is missing |
| `python -m espectro.load` | `artefactos/` | S3 (see env vars) | 0 when it succeeds or when both buckets are unset (it prints "omitido"); non-zero when `aws` fails |
| `python -m espectro.pipeline [--sin-carga]` | raw data | all of the above, plus `indicadores/fuentes_estimadas.csv` and `sitio/mapas/fuentes.html` | 0 when the three gate checks pass; 2 when a gate fails. The artifacts are still written so the failure can be inspected |

Each stage reads only what earlier stages persisted to disk, and none passes data along in memory
(Principle II).

## Gate checks inside `pipeline`

1. **Quality gate**: `reporte_calidad.csv` has 63 rows, each with one disposition, and `resumen_imputacion.json` has its totals.
2. **Indicator gate**: `indicadores_canal.csv` has 4 rows (A-D), and ranks 1 and 4 are assigned or the channels are marked `indeterminado`.
3. **Presentation gate**: the 8 required map files exist, `index.html` exists, and every `Fuente:` path in the report exists on disk.

Order: extract → transform → presentacion → gates → `espectro.fuentes` (bonus, mandatory) → load.
`fuentes` always runs when gates 1-3 pass (FR-027) and is skipped with exit code 2 when a gate fails.

## Environment variables

| Variable | Meaning | Default |
|---|---|---|
| `ESPECTRO_BUCKET_DATALAKE` | Target bucket for `aws s3 sync artefactos/ s3://…/espectro/` | unset, so the sync is skipped |
| `ESPECTRO_BUCKET_SITIO` | Static-website bucket for `artefactos/sitio/` | unset, so the sync is skipped |
| `ESPECTRO_URL_REPORTE` | Static report URL, linked from the dashboard header (set in the systemd unit) | unset, so no link is shown |

## Dashboard

`streamlit run dashboard/app.py --server.port 8050 --server.address 0.0.0.0 --server.headless true`

## Tests

`python -m pytest -q`
