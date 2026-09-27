# Research: Spectrum Occupancy Analysis and Dashboard

Phase 0 output for [plan.md](plan.md). The stack itself was fixed by the analyst. This file
records the decisions left open inside that stack, and every NEEDS CLARIFICATION it resolves.

## R1. Bin-to-frequency mapping and channel bins

- **Decision**: `f_k = 850 MHz + (k − 512) · Δf`, with `Δf = 20 MHz / 1024 = 19.53125 kHz` and
  `k = 0..1023`. Bin 0 = 840.000 MHz, bin 1023 = 859.980 MHz. Each channel takes the bins whose
  frequency falls in `[f_ini, f_fin)`: A 840-845 (bins 0-255), B 845-850 (256-511), C 850-855
  (512-767), D 855-860 (768-1023). The bin indices are derived from the edges in code, never
  typed by hand.
- **Rationale**: `medir_celular.py:236` applies `numpy.fft.fftshift` to a 1024-point FFT of
  complex IQ sampled at 20 MS/s and centred at `fc` = 850 MHz. After the shift, the DC bin sits
  at index N/2 = 512. This satisfies FR-008, FR-009 and Principle III.
- **Alternatives**: `linspace(840, 860, 1024)`, which spreads the bins across the closed
  interval, is off by up to one bin and ignores the FFT convention.

## R2. Dashboard framework: Streamlit, not Dash

- **Decision**: Streamlit ≥ 1.38, run as
  `streamlit run dashboard/app.py --server.port 8050 --server.address 0.0.0.0 --server.headless true`.
- **Rationale**: The dashboard only shows tables, a verdict and nine prebuilt Folium HTML maps.
  In Streamlit that is roughly 60 lines with no layout or callback code. Each map is embedded with
  `st.components.v1.html(html, height=560)`, one tab per view, and it renders well on a phone.
  Port 8050 is kept, as the analyst's security-group plan requires.
- **Alternatives**: Dash (`html.Iframe(srcDoc=...)`) works too, but it needs explicit layout
  components and more code for the same result. A static HTML page alone would not meet FR-018,
  which asks for a served web server.

## R3. Heat-map rendering in Folium

- **Decision**: Each map is built from `folium.Map(location=centroid, zoom_start=14,
  tiles="OpenStreetMap")` with two layers under a `LayerControl`:
  1. `plugins.HeatMap` with the weights min-max normalised on the same `[vmin, vmax]` as the legend,
     and a gradient taken from that colormap.
  2. `CircleMarker` points coloured by the same `branca.colormap.LinearColormap`, with a tooltip
     that shows the exact value and unit and whether the position was measured or imputed.

  The colormap is added to the map with a Spanish caption that includes the unit, for example
  "Potencia de canal B (dBm)". Channel maps A-D share one fixed dBm scale so they can be
  compared. The −60 dBm threshold is marked as a tick on the legend.
  Imputed positions are drawn with a dashed black outline and are labelled in the legend.
  The file is saved with `m.save()`: one HTML file per map. Leaflet is loaded from a CDN and
  tiles from OSM, so the viewer needs internet access.
- **Rationale**: A density-only HeatMap has no legend, and along a linear route it shows sampling
  density rather than power. The coloured points give the legible values that FR-020 asks for.
- **Alternatives**: `folium.Choropleth` needs polygons, which we don't have. IDW interpolation
  onto a grid would invent values away from the route.

## R4. Artifact formats

- **Decision**: CSV (UTF-8, `.` decimal, float precision fixed with `float_format="%.6f"`)
  for tables, JSON (`sort_keys=True, indent=2, ensure_ascii=False`) for scalars and verdicts,
  PNG (matplotlib, `metadata={"Software": None}`) for figures. No Parquet, so no pyarrow
  dependency.
- **Rationale**: CSV and JSON can be inspected by hand (Principle II). Fixed formatting and sorted
  keys make repeated runs byte-identical (SC-003). Removing matplotlib's PNG metadata keeps the
  figures byte-identical as well. The HTML maps embed random element ids, so the determinism
  check covers `curado/`, `calidad/` and `indicadores/` only.

## R5. Quality rules and dispositions

- **Decision** (`calidad.py`, with every threshold defined in `config.py`):

  | Rule | Criterion | Consequence |
  |---|---|---|
  | Contract | The file has exactly 1029 finite numeric fields | If not: `descartado`, with scope *total* |
  | Test file | Name is not `NNN.txt` | Excluded from the study and listed as `excluido_prueba` in the report (FR-007) |
  | Spectral bin validity | Finite and within [−160, +30] dBm | Invalid runs of ≤ 2 bins are linearly interpolated (`corregido`). A longer run discards the spectrum |
  | Saturation | Noise floor p10 is more than 30 dB above the study median p10 | Spectrum discarded, telemetry kept (FR-030) |
  | Position failure | lon = lat = alt = 0, or outside bounds (lat 6.0-6.5, lon −75.8…−75.4, alt 1300-2800 m) | If both neighbours are valid, lon/lat/alt are linearly interpolated from them (`imputado`, uncertainty = half the neighbour distance, about 600 m for 008). If not, the capture is excluded from spatial outputs |
  | Distance error | > 5.0 (baseline 0.7-1.4) | Flag `posicion_baja_confianza`, kept as it is (017) |
  | Temperature | Within [−10, 85] °C (internal sensor) | Out-of-range values are flagged, and temperature is not imputed |

  Each capture gets exactly one disposition, applied with the precedence
  `descartado > imputado > corregido > aceptado`. The per-capture flags `espectro_utilizable` and
  `posicion_utilizable` keep the spectrum and the telemetry independent, so 016 is
  `descartado` with scope *espectro*.
- **Rationale**: Implements FR-002 to FR-006, FR-029 and FR-030 with interpolation only. The
  interpolation uses `numpy.interp` over each run of invalid values, found by run-length
  detection.
- **Alternatives**: Median or mean fill is forbidden by FR-029. Deleting whole captures for a
  single bad field would violate FR-005.

## R6. Parseval indicators

- **Decision**: For capture *c* and channel *ch*, `P_lin = Σ_k 10^(dBm_k/10)` in mW over that
  channel's bins, then `P_dBm = 10·log10(P_lin)`. This is the total in-channel power, the Parseval
  sum of the bin powers. The headline figure is `10·log10(mean_c P_lin)`. The supporting figures
  are the percentage of captures with `P_dBm > UMBRAL` and the median of `P_dBm`. The mean power
  per frequency is `10·log10(mean_c 10^(dBm_k/10))` for each bin, over the captures with a usable
  spectrum. The most and least contaminated frequencies are the argmax and argmin of that mean.
  The sum, not the average over bins, is the definition (FR-010): the spectrum is `|FFT|/N`, so
  by Parseval the sum of the bin powers equals the signal's mean power in the channel. The
  average over bins would sit 10·log10(256) ≈ 24 dB lower and has no physical meaning as a
  channel power.
- **Rationale**: FR-010 to FR-013. The spec's clarification on "mean occupancy power" is
  about which captures are averaged, and it is a linear mean. The in-channel summation is
  Parseval's theorem applied to the bin powers.
- **Note for the report**: the max-hold, uncalibrated spectrum biases the power upward (see the
  spec's Assumptions). The report states this as a limitation.

## R7. Temperature vs. quality statistic

- **Decision**: A partial Spearman correlation between temperature and noise floor (p10),
  controlling for acquisition order. The three variables are rank-transformed, the partial Pearson
  correlation of the ranks is taken from the residuals of each variable regressed on the order
  rank, and the p-value comes from a t-test with n − 3 degrees of freedom (`scipy.stats.t`).
  The zero-order Spearman correlation (`scipy.stats.spearmanr`) is also reported. Captures with a
  usable spectrum go into the calculation (016 is excluded, since it is saturated).
  If p ≥ 0.05, the report writes "no concluyente".
- **Rationale**: FR-023 and SC-007. Temperature and order correlate at ρ ≈ 0.91, so the zero-order
  statistic cannot separate their effects.
- **Alternatives**: `pingouin.partial_corr` gives the same result but adds a dependency.

## R8. Route description

- **Decision**: The route is ordered by the capture number in the file name, and that basis is
  written into `ruta.json`. The file records the start and end coordinates, the haversine length
  of the path through the usable positions, the bounding box, the number of stationary pairs
  (identical coordinates) and the count of imputed and excluded positions. The analyst names the
  neighbourhoods crossed in `reporte/narrativa/ruta.md`, reading them off the route map.
- **Rationale**: FR-022. Reverse geocoding would add a network dependency and non-determinism
  for one sentence of prose.

## R9. Nyquist check

- **Decision**: `config.py` holds `FS_HZ = 20e6` and `F_MAX_HZ = 10e6` (complex IQ, baseband
  half-bandwidth). `analisis.py` writes `nyquist.json` with the verdict (`cumple` when
  `fs >= 2·fmax`), a `en_el_limite` flag when the two are equal, and the implication text about
  roll-off at the band edges of A and D. The check never raises an error.
- **Rationale**: FR-028 and SC-010. The verdict is computed rather than typed, so a change to a
  constant flows through to the report.

## R10. Report generation

- **Decision**: `reporte.py` renders `plantillas/reporte.html.j2` with jinja2, which folium
  already installs. Figures are embedded as base64 PNG so the report is a single file. Tables are
  rendered with `DataFrame.to_html`. Each block ends with `Fuente: <artifact path>`. The
  narrative in `reporte/narrativa/*.md` is converted with `markdown`. A missing file renders a
  visible "PENDIENTE: redactar" box. The recommendation table is generated automatically
  with a relative rule (FR-025): the channels are ranked by headline power, the two least
  contaminated get `usar` and the two most contaminated get `evitar`. Each row also shows the
  absolute state (`contaminado` or `libre`). The analyst's
  prose goes next to it. The report links to the maps as `mapas/<name>.html` (a relative
  path, which works both locally and on S3).
- **Figures**: (1) the spectrum of mean power per frequency, with the −60 dBm line, the channel
  boundaries and the max and min frequencies marked; (2) the power per capture at the most
  contaminated frequency and at the least contaminated one, which is the plot FR-013 asks for;
  (3) temperature and noise floor against capture order; (4) a bar chart of channel power
  against the threshold.

## R11. Load stage (datalake + static site)

- **Decision**: `load.py` calls the AWS CLI through `subprocess.run([...], check=True)`:
  - `aws s3 sync artefactos/ s3://$ESPECTRO_BUCKET_DATALAKE/espectro/ --exclude "sitio/*" --delete`
  - `aws s3 sync artefactos/sitio/ s3://$ESPECTRO_BUCKET_SITIO/ --delete`

  If an environment variable is unset, that sync is skipped with a message. This is the normal
  case for local runs, and the exit code stays 0. If the AWS CLI fails, the stage exits non-zero.
  The credentials come from LabInstanceProfile through IMDS, so no keys are stored on the EC2.
- **Rationale**: The analyst required `aws s3 sync`. The CLI is installed on the EC2 with
  `snap` (R12), so using it avoids adding a boto3 dependency.

## R12. EC2 runtime

- **Decision**: Ubuntu Server 24.04 LTS on a t3.micro (the distribution the course uses), installing
  `apt install -y git curl` and the AWS CLI with `snap install aws-cli --classic`
  (Ubuntu does not ship it). The Python environment is built with **uv**:
  `uv venv --python 3.12 .venv` downloads a managed CPython 3.12 into the user's home, and
  `uv pip install --python .venv/bin/python -r requirements.txt` installs the pinned versions.
  The system Python is not used. The instance's `python3` turned out to be newer than 3.12, and
  numpy 2.1.3 has no precompiled wheel for it, so `pip` fell back to a source build that failed
  (`metadata-generation-failed`). Pinning the interpreter keeps the EC2 environment identical to the
  one tested locally (Python 3.12). A 1 GB swapfile is created before the install as a safety
  margin for the 1 GB of RAM. A venv lives at `~/iot/.venv`. A systemd unit,
  `deploy/espectro-dashboard.service`, runs Streamlit as `ubuntu` with `Restart=always`
  and `WantedBy=multi-user.target`, so the dashboard returns when the Learner Lab restarts the
  instance. The security group allows 22 only from the prefix list `com.amazonaws.us-east-1.ec2-instance-connect`
  (IPv4), which the console's Connect button uses, and 8050 from 0.0.0.0/0. The Elastic IP
  keeps the URL `http://<EIP>:8050` fixed.
- **Rationale**: FR-031, with the simplest possible deployment: no Docker, no nginx, no
  pipeline cron job. The pipeline is rerun by hand, which is the cloud decision model.

## R13. S3 static website

- **Decision**: The site bucket has static website hosting enabled with index document
  `index.html`. Block Public Access is turned off and a public-read bucket policy is
  attached, both in the CLI sequence in the README. The datalake bucket stays private.
- **Risk**: If the Learner Lab denies `PutBucketPolicy` or `PutPublicAccessBlock`, the fallback
  is to link the report from the dashboard with a presigned URL, or to accept the dashboard as the
  only public surface. The README documents that fallback.

## R14. Bonus: source-location estimate (mandatory, last)

- **Decision**: For each channel, a power-weighted centroid of the usable positions, with weights
  `P_lin` taken from the captures in the top quartile. The uncertainty is the weighted standard
  distance in metres. When the route is too linear to locate a source (principal-axis
  ratio > 10) or fewer than 5 captures are above the median, the estimate is marked
  `no_soportado`. The estimates are drawn on their own map, `mapas/fuentes.html`: the route
  plus one marker per channel labelled "Estimación", with a circle whose radius is the
  uncertainty and the method in the tooltip. `pipeline` always runs this step after the three
  gates pass and before `load` (FR-027). A separate map avoids regenerating the channel maps
  that the presentation gate has already checked.
- **Rationale**: This is the cheapest method that can be defended. A log-distance path-loss fit
  cannot be constrained by points along a single route.
