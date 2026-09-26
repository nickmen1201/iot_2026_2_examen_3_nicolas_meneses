# Feature Specification: Spectrum Occupancy Analysis and Dashboard (840-860 MHz, Medellin)

**Feature Branch**: `001-spectrum-occupancy-analysis`

**Created**: 2026-09-25

**Status**: Draft

**Input**: User description: _(none supplied with the command)_ — derived from `Examen_03_2026_20.md`
(the study brief) and `.specify/memory/constitution.md` v1.0.0. The feature is the complete
graded deliverable: an ETL process over the spectrum measurement set that produces a data
quality assessment, channel contamination indicators, the evidence backing a written technical
report for the Agencia Nacional del Espectro (ANE), and an interactive web dashboard.

## Clarifications

### Session 2026-09-26

- Q: Is a channel contaminated when its Parseval mean power exceeds -60 dBm, or when any single
  bin does? → A: Parseval mean power per channel. The brief defines channel power via Parseval
  in the line that follows the threshold. The any-bin reading marks 44 (A), 44 (B), 61 (C), and
  42 (D) of 61 captures contaminated. Because captures are max-hold over 100 FFTs, one spurious
  peak would flip a whole channel, so the any-bin reading is rejected.
- Q: Is channel contamination computed per capture and then aggregated, or pooled across all
  captures at once? → A: Parseval power per capture per channel first, which feeds the heat
  maps, then aggregated. The headline indicator is the linear-power mean of the per-capture
  channel powers, converted back to dBm. Supporting figures are the percentage of captures whose
  channel power exceeds -60 dBm (occupancy rate, ITU-R SM.1880 style) and the median per-capture
  power as a robustness check against outliers.
- Q: Does this feature generate the written report document, or only the evidence artifacts?
  → A: The pipeline generates the report document in Spanish (Markdown/HTML), with every figure,
  table, and number inserted automatically from artifacts. The analyst writes the interpretive
  narrative and the recommendation inside that generated document.
- Q: To which signal and domain does the Nyquist check apply? → A: Temporal sampling of the RF
  signal by the receiver. The acquisition script shows complex IQ sampling at f_s = 20 MS/s
  centred at 850 MHz, so the baseband f_max = 10 MHz (half of 840-860 MHz). f_s = 2·f_max, so
  the criterion is met exactly at the limit. The implication to report: the band edges (the
  lower end of channel A and the upper end of channel D) sit on the anti-aliasing filter
  roll-off and may be attenuated or aliased. Spectral resolution is 20 MHz / 1024 ≈ 19.5 kHz
  per bin.
- Q: Along which axis is interpolation performed, and what is the largest gap that may be
  imputed? → A: Both axes, with separate limits. Telemetry is interpolated linearly along the
  route between neighbouring captures, with a maximum gap of 1 capture. `008` has all position
  fields zero and gets an imputed position from `007` and `009`, flagged as imputed with about
  600 m of uncertainty. Spectrum is interpolated linearly across adjacent bins, with a maximum
  gap of 2 consecutive bins (≈39 kHz). A wider gap discards the capture, since wider
  interpolation could erase a narrowband carrier. `017` (distance error 17.3) is not imputed.
  Its coordinates are consistent with its neighbours, so it is kept and flagged as a
  low-confidence position.
- Q: How is channel power defined, and how is the recommendation made when every channel exceeds
  -60 dBm? → A: Channel power is the Parseval sum of the linear bin powers over the channel's
  256 bins, which is the total in-channel power. The spectrum is normalised by N, so this sum
  is the signal's mean power in the channel. With this definition, all four headline powers
  exceed -60 dBm (A -33.9, B -13.5, C -10.7, D -24.8 dBm without `016`). The recommendation is
  therefore relative. The two least contaminated channels by headline power are recommended for
  use, and the two most contaminated are to be avoided. Each channel's absolute state
  (contaminated or clear) is still reported next to its recommendation.
- Q: What is done with a capture whose whole spectrum is raised, as in `016`? → A: Its spectrum
  is discarded as suspected receiver saturation, and its telemetry stays usable. The criterion:
  a capture's noise floor (10th percentile of its 1024 bins) exceeds the study median noise floor
  by more than 30 dB. `016` sits 35.6 dB above; the next highest (`024`) sits 21.8 dB above, so
  30 dB falls in a clear natural break. The report states how much the indicators change with
  and without the discarded spectrum.
- Q: Which number represents "data quality" when assessing temperature? → A: The per-capture
  noise floor (10th percentile of spectral power), because thermal noise rises with
  temperature. The statistic is Spearman correlation between temperature and noise floor, with
  acquisition order controlled, since temperature and order correlate at ρ ≈ 0.91.
- Q: Does the brief's "dashboard y aplicación remota" require a separate application? → A: No.
  The dashboard is served from the cloud, reachable from any device including a phone, and it
  shows the decision (contaminated or clear per channel, plus the recommendation). That covers
  "visualice/notifique" without a separate app. The deployment method is decided during
  planning, not in this spec.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trustworthy measurement set with a quality verdict (Priority: P1)

The technical analyst receives 61 raw spectrum captures from a mobile monitoring station and
must know, before drawing any conclusion, which captures are trustworthy. They run the ingest
and cleaning process and obtain a curated measurement set plus a quality report that states,
for every capture, whether it was accepted, corrected, imputed, or discarded, and why. The
report totals how many values were changed and names the technique used for each change.

**Why this priority**: Every other deliverable is illegitimate without it, and the study brief
requires the quality report and imputation count as explicit report content. It is also the
one slice that delivers standalone value: even alone, it answers "can we trust this data?".

**Independent Test**: Run the process against the raw captures only. It must emit a curated
dataset and a quality report listing all 61 captures with a disposition each, and a non-negative
count of corrections and imputations. No indicator or map is needed for this to be useful.

**Acceptance Scenarios**:

1. **Given** the 61 raw captures, **When** the ingest and quality process runs, **Then** the
   quality report lists every capture with exactly one disposition and a stated reason.
2. **Given** a capture whose position fields are all zero (as in `008.txt`) and whose
   neighbouring captures both have valid positions, **When** quality assessment runs, **Then**
   it is flagged as a positioning failure, its position is imputed by linear interpolation
   between its neighbours, and it is listed with disposition imputed, the technique, and the
   positional uncertainty. When a neighbour is also invalid, the capture is excluded from
   position-dependent outputs instead.
3. **Given** a capture whose reported distance error is far outside the population baseline
   (as in `017.txt` at 17.3 against a 0.7-1.4 baseline), **When** quality assessment runs,
   **Then** it is flagged as a low-confidence position with the bound that triggered the flag,
   and it is kept, not imputed, when its coordinates are consistent with its neighbours.
4. **Given** any value is corrected or imputed, **When** the report is produced, **Then** the
   technique, the count of affected values, and the justification are stated.
5. **Given** the process is run twice without changing inputs, **When** outputs are compared,
   **Then** the curated dataset and quality report are identical.

---

### User Story 2 - Channel contamination indicators and ranking (Priority: P2)

The analyst needs the central analytical answer: how contaminated are the four 5 MHz channels
(A, B, C, D) spanning 840-860 MHz, which is worst, and which is cleanest. From the curated
set, the process computes each channel's mean occupancy power by Parseval summation, classifies
each against the -60 dBm contamination threshold, and ranks the channels.

**Why this priority**: This is the question the ANE is asking and the spine of the written
report. It depends only on Story 1 and unblocks both remaining stories.

**Independent Test**: Given the curated dataset, the process emits four channel indicators with
power in dBm, an occupied/clear classification each, and a named most- and least-contaminated
channel. Verifiable as a table without any visualisation.

**Acceptance Scenarios**:

1. **Given** the curated dataset, **When** indicators are computed, **Then** channels A, B, C,
   and D are defined as the four consecutive 5 MHz blocks of 840-860 MHz in ascending frequency
   order, and each reports a mean occupancy power in dBm.
2. **Given** a channel's spectral bins, **When** its mean power is computed, **Then** the
   conversion from dBm to linear power precedes the summation and the result is converted back
   to dBm for reporting.
3. **Given** the four channel powers, **When** classification runs, **Then** each channel is
   labelled contaminated or clear against the -60 dBm threshold, and the most and least
   contaminated channels are named with their values.
4. **Given** every capture contributing to a channel was discarded by quality assessment,
   **When** indicators are computed, **Then** that channel's indicator is reported as
   undetermined rather than as a number.
5. **Given** the single most and least contaminated frequencies across the whole system,
   **When** indicators are computed, **Then** both are identified by frequency with their power.

---

### User Story 3 - Interactive dashboard for the ANE (Priority: P3)

A reviewer at the agency opens a served web dashboard and explores the study spatially: where
the measurements were taken, the path the mobile station followed, how each channel's
contamination is distributed across Medellin, how the sensor's own temperature varied along the
route, and how the worst frequency is distributed geographically.

**Why this priority**: It is half the graded deliverable and the largest build, so it is
sequenced before the smaller report-evidence slice despite equal grade weight. It consumes
Story 1 and Story 2 outputs and adds no analysis of its own.

**Independent Test**: Start the server and confirm all required maps render from curated
artifacts, each labelled with its units and colour scale, with no recomputation of cleaning or
indicator logic in the dashboard itself.

**Acceptance Scenarios**:

1. **Given** the dashboard is served, **When** the reviewer opens it, **Then** measurement
   locations, the station route, a heat map per channel (A, B, C, D), a sensor temperature heat
   map, and a most-contaminated-frequency heat map are all reachable.
2. **Given** any view is displayed, **When** the reviewer inspects it, **Then** its units and
   colour scale are stated on the view.
3. **Given** captures excluded for positioning failure, **When** spatial views render, **Then**
   those captures are absent from the map rather than plotted at a default location, and
   captures with an imputed position are visually distinguished from measured positions.
4. **Given** the curated artifacts change, **When** the dashboard is reloaded, **Then** the
   views reflect the new values without any dashboard code change.

---

### User Story 4 - Evidence pack for the written report (Priority: P4)

The analyst assembles the written technical report for the ANE and needs every claim backed.
The process produces the supporting evidence: a description of the route the station followed,
an assessment of whether sensor temperature affected measurement quality, plots of the most and
least contaminated frequencies, and the indicator table underpinning the band recommendation.

**Why this priority**: Smallest slice, since it reuses artifacts from Stories 1-3, but it
carries the report's argumentative weight and the recommendation the agency acts on.

**Independent Test**: Confirm each required report element has a corresponding artifact, and
that the temperature assessment states both a computed statistic and its limitation.

**Acceptance Scenarios**:

1. **Given** the curated positions, **When** the route is described, **Then** its ordering basis
   is stated explicitly, since the captures carry no timestamp field.
2. **Given** sensor temperature trends upward across the capture sequence, **When** the
   temperature-versus-quality question is assessed, **Then** the assessment reports a statistic
   and explicitly addresses that temperature is confounded with acquisition order, rather than
   asserting causation from correlation alone.
3. **Given** the data does not support a conclusion, **When** the report states it, **Then** it
   says so explicitly rather than asserting a direction.
4. **Given** the indicator table, **When** the recommendation is written, **Then** it names
   which bands to use and which to avoid, derivable from the indicators alone.

---

### User Story 5 - Contamination source location estimate (Priority: P5)

For the study's bonus objective, the analyst estimates where each band's interference originates
by extrapolating from signal strength across the measured positions, and places those estimates
on the map.

**Why this priority**: The constitution permits it only once the three quality gates pass. It must never delay Stories 1-4.

**Independent Test**: With all gates passing, confirm each band yields a source estimate placed
on the map and labelled as an estimate with its method and uncertainty.

**Acceptance Scenarios**:

1. **Given** all three quality gates pass, **When** source estimation runs, **Then** each
   studied band receives a location estimate labelled with its method and uncertainty.
2. **Given** the measurement geometry cannot constrain a source, **When** estimation runs,
   **Then** it reports the estimate as unsupported instead of emitting a location.

---

### Edge Cases

- A capture reports all position fields as zero (present: `008.txt`) — positioning failure,
  whose position is imputed from its two neighbours because the gap is a single capture.
- A run of more than 2 consecutive invalid spectral bins in one capture — the capture is
  discarded instead of interpolated.
- A capture reports a distance error far outside the population baseline (present: `017.txt`).
- Captures carry no timestamp, so route ordering must rest on a stated, defensible basis.
- Test captures (`medidaprueba.txt`, `medidaprueba2.txt`) are not part of the 61-capture study
  set and must not silently enter the indicators.
- A capture's spectrum sits near the noise floor across all bins. It is kept, because a low
  noise floor is a valid quiet reading and is not a defect.
- A capture's whole spectrum is raised, suggesting receiver saturation (present: `016.txt`,
  noise floor 35.6 dB above the study median) — its spectrum is discarded per FR-030 so it does
  not inflate the channel indicators.
- Non-finite or unparseable values appear in a spectral or telemetry field.
- A capture does not present the expected field count.
- Two captures report identical coordinates, so the station was stationary between them.
- All captures contributing to a channel are discarded, leaving its indicator undetermined.
- Reported altitude or coordinates fall outside plausible bounds for the study area.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST ingest the raw captures without modifying them, treating the raw
  measurement set as an immutable input.
- **FR-002**: System MUST validate each capture against the expected structure of 1024 spectral
  power values in dBm followed by sensor temperature, longitude, latitude, altitude, and
  distance error, and MUST flag any non-conforming capture rather than reshaping it by guesswork.
- **FR-003**: System MUST assign exactly one disposition per capture — accepted, corrected,
  imputed, or discarded — with a stated reason, and MUST retain discarded captures in the
  quality report.
- **FR-004**: System MUST enforce and record plausibility bounds on position, altitude,
  temperature, and spectral power, reporting violations as quality findings.
- **FR-005**: System MUST NOT silently coerce values, drop captures, or substitute zero for
  missing data.
- **FR-006**: System MUST report the total count of corrected and imputed values, the technique
  applied, and the justification for that technique per affected field.
- **FR-007**: System MUST exclude the two test captures from the study set, stating that
  exclusion in the quality report.
- **FR-008**: System MUST map the 1024 spectral bins onto the 840-860 MHz frequency axis before
  any channel aggregation.
- **FR-009**: System MUST define channels A, B, C, and D as the four consecutive 5 MHz blocks of
  the band in ascending frequency order.
- **FR-010**: System MUST compute each channel's mean occupancy power by Parseval summation over
  that channel's bins: the sum of the linear bin powers, which is the total in-channel power.
  The conversion from dBm to linear power happens before summation, and the result is converted
  back to dBm for reporting.
- **FR-011**: System MUST classify channel contamination against the -60 dBm threshold, applied
  to the channel's Parseval mean power: a channel is contaminated when that power exceeds
  -60 dBm, not when any individual bin does. The threshold MUST be defined in exactly one
  place.
- **FR-012**: System MUST compute each channel's Parseval power per capture, then aggregate it
  across the measurement set. The headline indicator is the linear-power mean of the per-capture
  channel powers, converted to dBm. Each channel MUST also report the percentage of captures
  whose channel power exceeds -60 dBm and the median per-capture power. The per-capture values
  feed the channel heat maps.
- **FR-013**: System MUST identify the most and least contaminated channel, and the most and
  least contaminated single frequency across the whole system, reporting each with its power.
  A frequency's power is the linear-power mean of that bin across accepted captures, in dBm.
  System MUST produce a plot of the most and the least contaminated frequency.
- **FR-014**: System MUST report a channel indicator as undetermined when no accepted capture
  contributes to it.
- **FR-015**: System MUST persist the curated dataset, the quality report, and the channel
  indicators as inspectable artifacts on disk.
- **FR-016**: System MUST allow a full rebuild from raw captures to every downstream artifact as
  a single documented operation, producing identical results on repeated runs.
- **FR-017**: System MUST keep the extract, transform, and load stages separately runnable and
  separately inspectable.
- **FR-018**: System MUST serve an interactive dashboard over a web server presenting
  measurement locations, the station route, a heat map per channel (A, B, C, D), a sensor
  temperature heat map, and a most-contaminated-frequency heat map, all drawn over a map of
  Medellín. The dashboard MUST also show the decision: each channel's contaminated-or-clear
  verdict and the band recommendation.
- **FR-019**: Dashboard MUST read only curated artifacts and MUST NOT reimplement cleaning,
  imputation, or indicator logic.
- **FR-020**: Each dashboard view MUST state its units and colour scale.
- **FR-021**: System MUST omit captures whose position could not be imputed from spatial views
  rather than plotting them at a default location. Captures with an imputed position MUST be
  shown and visually distinguished from measured positions.
- **FR-022**: System MUST describe the route the station followed (start and end points, total
  length, and the areas it crossed) and MUST state the basis on which it is ordered, given the
  absence of a timestamp field.
- **FR-023**: System MUST assess whether sensor temperature relates to measurement quality,
  measured as the per-capture noise floor (10th percentile of spectral power). It MUST report
  the Spearman correlation between temperature and noise floor with acquisition order
  controlled, the statistic's limitation, and the confound that temperature trends upward with
  capture order.
- **FR-024**: System MUST produce, for the written report, the evidence artifacts backing each
  claim, such that every report claim cites a specific artifact. System MUST generate the report
  document in Spanish (Markdown/HTML) with every figure, table, and number inserted
  automatically from artifacts. The analyst writes the interpretive narrative and the
  recommendation inside that generated document.
- **FR-025**: System MUST state which bands it recommends for use and which to avoid, derivable
  from the computed indicators alone. The rule is relative: channels are ranked by headline
  power. The two least contaminated are recommended for use and the two most contaminated are to
  be avoided, even when all four exceed -60 dBm. Each channel's absolute contaminated-or-clear
  state is reported next to its recommendation. A channel with no data is marked as having no
  data.
- **FR-026**: System MUST express report content and every dashboard label in Spanish, matching
  the audience of the deliverable.
- **FR-027**: System MUST produce a source-location estimate for each channel (the brief's bonus)
  and place it on a map in the dashboard. Estimation is built last and runs only after the
  three quality gates pass. Each estimate MUST be labelled as an estimate with its method and
  uncertainty, or marked as unsupported when the geometry cannot constrain a source.
- **FR-028**: System MUST verify whether the measurements satisfy the Nyquist sampling criterion
  (f_s ≥ 2·f_max) and report the outcome explicitly as met or not met. The verdict MUST appear
  prominently in the written report together with its implications for the reliability of the
  results. A failed check MUST NOT halt processing: the analysis continues and the report
  highlights the violation. The check applies to temporal sampling of the RF signal: complex IQ
  at f_s = 20 MS/s centred at 850 MHz, so f_max = 10 MHz in baseband. The report MUST state that
  the criterion is met exactly at the limit (f_s = 2·f_max). It MUST also state that the band
  edges (lower end of channel A, upper end of channel D) sit on the anti-aliasing filter
  roll-off, so those channels' edge bins may be attenuated or aliased.
- **FR-029**: System MUST impute missing or invalid values by interpolation only. Statistical
  imputation (mean, median, mode, or model-based estimation) is out of scope and MUST NOT be
  used. Telemetry MUST be interpolated linearly along the route between neighbouring captures,
  with a maximum gap of 1 consecutive capture. Spectral values MUST be interpolated linearly
  across adjacent bins within a capture, with a maximum gap of 2 consecutive bins (≈39 kHz).
  A larger gap discards the capture (spectrum) or excludes it from position-dependent outputs
  (telemetry). Each imputed position MUST carry its positional uncertainty.
- **FR-030**: System MUST discard a capture's spectrum as suspected receiver saturation when its
  noise floor (10th percentile of its 1024 bins) exceeds the study median noise floor by more
  than 30 dB. Its telemetry remains usable for route and temperature outputs. The report MUST
  state how much the channel indicators change with and without the discarded spectrum.
- **FR-031**: The pipeline and the dashboard MUST run on cloud infrastructure, and the
  dashboard MUST be reachable remotely from any device with a browser, including a phone. This
  remote dashboard is the "aplicación remota" of the brief. The deployment method is decided
  during planning.

### Key Entities *(include if feature involves data)*

- **Raw Capture**: One immutable measurement taken at one position, carrying a spectral power
  profile plus sensor telemetry. Identified by its source file; 61 form the study set.
- **Spectral Profile**: The 1024 power values of a capture, mapped onto the 840-860 MHz axis.
- **Sensor Telemetry**: The non-spectral attributes of a capture — sensor temperature,
  longitude, latitude, altitude, and reported distance error.
- **Quality Finding**: An observation about one capture or field, carrying the rule violated,
  the severity, and the resulting disposition.
- **Disposition**: The verdict on a capture — accepted, corrected, imputed, or discarded — with
  its reason, and the technique and affected-value count where a change was made.
- **Channel**: One of four named 5 MHz blocks (A, B, C, D) partitioning the band, defined by its
  frequency range and the spectral bins falling in it.
- **Channel Occupancy Indicator**: A channel's headline mean occupancy power in dBm (linear mean
  of per-capture Parseval powers) with its contaminated-or-clear classification, its percentage
  of captures above -60 dBm, and its median per-capture power, or an undetermined marker.
- **Station Route**: The ordered sequence of accepted measurement positions describing the
  mobile station's path, with its ordering basis recorded.
- **Band Recommendation**: A use-or-avoid judgement per channel, made by relative ranking of the
  headline power and traced to the indicators supporting it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 61 study captures carry a recorded disposition with a stated reason, and the
  quality report states a total count of corrected and imputed values — zero unexplained gaps.
- **SC-002**: All four channels report an occupancy power with a contamination classification,
  or an explicit undetermined marker, and the most and least contaminated channels are named.
- **SC-003**: Two consecutive full rebuilds from the raw captures produce identical curated
  data, quality reports, and indicator values.
- **SC-004**: A reviewer opening the dashboard can identify the most contaminated channel within
  30 seconds without consulting any other document.
- **SC-005**: All required dashboard maps are present: locations, route, four channel heat maps,
  sensor temperature, most contaminated frequency, and source estimates. Each map states its
  units and colour scale.
- **SC-006**: 100% of claims in the written report cite a specific supporting artifact.
- **SC-007**: The temperature-versus-quality question is answered with a computed statistic, a
  stated limitation, and explicit treatment of the acquisition-order confound.
- **SC-008**: A reviewer can rebuild the full analysis from the raw captures on a clean machine
  using only the declared dependencies and documented instructions.
- **SC-009**: The band recommendation names every channel as recommended or not, with each
  judgement traceable to an indicator value. At least one channel is recommended for use
  whenever at least one channel has data.
- **SC-010**: The written report contains a dedicated Nyquist section stating an explicit met or
  not-met verdict and its implications for the reliability of the results.
- **SC-011**: The report states the number of imputed values, the interpolation method used, and
  the reason for each imputation.

## Assumptions

- Cloud deployment runs on a university-provided AWS Academy Lab account with a credit cap, set
  up manually by the analyst; the solution must be the simplest and cheapest possible that
  still covers the full brief, including the bonus.
- The 61 numbered captures constitute the study set; `medidaprueba.txt` and `medidaprueba2.txt`
  are acquisition tests and are excluded.
- Captures carry no timestamp, so the route is ordered by capture sequence as implied by file
  naming. This is recorded as the ordering basis rather than treated as a measured time.
- Sensor temperature readings of roughly 42-50 °C represent the instrument's internal
  temperature, not ambient air temperature, so they are plausible rather than outliers.
- The band spans 840-860 MHz across 1024 bins, giving four channels of 256 bins each; the
  brief's four consecutive 5 MHz blocks therefore tile the band exactly.
- The -60 dBm contamination threshold and the four-channel plan are given by the study and are
  not the analyst's to choose.
- "Most contaminated frequency in the whole system" is a single study-wide frequency, whose heat
  map shows that one frequency's power distributed across measurement positions.
- Position, altitude, and coordinate plausibility bounds are those of the Medellin metropolitan
  area and its elevation.
- The legacy acquisition scripts and the instrument trace file in the measurement folder are
  historical reference documenting how data was captured; they are not runnable parts of this
  deliverable and are not modified.
- The dashboard serves a small number of concurrent reviewers, so throughput is not a design
  driver; clarity of the views is.
- Excluding a capture from position-dependent outputs does not exclude its spectral data from
  channel indicators, provided the spectrum itself passed quality assessment. Symmetrically,
  discarding a capture's spectrum does not discard its valid telemetry.
- The study brief sets delivery on 2026-09-26. The bonus is in scope and is built last.
- Spectral values are uncalibrated relative levels: the acquisition computed
  `20·log10(|FFT|/N)` as a max-hold over 100 FFTs. They are treated as dBm per the brief, but the
  report MUST state this as a limitation, because max-hold biases Parseval means upward and the
  -60 dBm threshold assumes calibrated power.
