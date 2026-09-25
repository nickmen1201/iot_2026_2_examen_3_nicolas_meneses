# Feature Specification: Spectrum Occupancy Analysis and Dashboard (840-860 MHz, Medellin)

**Feature Branch**: `001-spectrum-occupancy-analysis`

**Created**: 2026-09-25

**Status**: Draft

**Input**: User description: _(none supplied with the command)_ — derived from `Examen_03_2026_20.md`
(the study brief) and `.specify/memory/constitution.md` v1.0.0. The feature is the complete
graded deliverable: an ETL process over the spectrum measurement set that produces a data
quality assessment, channel contamination indicators, the evidence backing a written technical
report for the Agencia Nacional del Espectro (ANE), and an interactive web dashboard.

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
2. **Given** a capture whose position fields are all zero (as in `008.txt`), **When** quality
   assessment runs, **Then** it is flagged as a positioning failure and excluded from
   position-dependent outputs, while remaining listed in the report with its cause.
3. **Given** a capture whose reported distance error is far outside the population baseline
   (as in `017.txt` at 17.3 against a 0.7-1.4 baseline), **When** quality assessment runs,
   **Then** it is flagged as a low-confidence position with the bound that triggered the flag.
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

**Independent Test**: Start the server and confirm all six required views render from curated
artifacts, each labelled with its units and colour scale, with no recomputation of cleaning or
indicator logic in the dashboard itself.

**Acceptance Scenarios**:

1. **Given** the dashboard is served, **When** the reviewer opens it, **Then** measurement
   locations, the station route, a heat map per channel (A, B, C, D), a sensor temperature heat
   map, and a most-contaminated-frequency heat map are all reachable.
2. **Given** any view is displayed, **When** the reviewer inspects it, **Then** its units and
   colour scale are stated on the view.
3. **Given** captures excluded for positioning failure, **When** spatial views render, **Then**
   those captures are absent from the map rather than plotted at a default location.
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
2. **Given** sensor temperature rises monotonically across the capture sequence, **When** the
   temperature-versus-quality question is assessed, **Then** the assessment reports a statistic
   and explicitly addresses that temperature is confounded with acquisition order, rather than
   asserting causation from correlation alone.
3. **Given** the data does not support a conclusion, **When** the report states it, **Then** it
   says so explicitly rather than asserting a direction.
4. **Given** the indicator table, **When** the recommendation is written, **Then** it names
   which bands to use and which to avoid, derivable from the indicators alone.

---

### User Story 5 - Contamination source location estimate (Priority: P5, optional)

For the study's bonus objective, the analyst estimates where each band's interference originates
by extrapolating from signal strength across the measured positions, and places those estimates
on the map.

**Why this priority**: Explicitly optional in the study brief, and the constitution permits it
only once the three quality gates pass. It must never delay Stories 1-4.

**Independent Test**: With all gates passing, confirm each band yields a source estimate placed
on the map and labelled as an estimate with its method and uncertainty.

**Acceptance Scenarios**:

1. **Given** all three quality gates pass, **When** source estimation runs, **Then** each
   studied band receives a location estimate labelled with its method and uncertainty.
2. **Given** the measurement geometry cannot constrain a source, **When** estimation runs,
   **Then** it reports the estimate as unsupported instead of emitting a location.

---

### Edge Cases

- A capture reports all position fields as zero (present: `008.txt`) — positioning failure.
- A capture reports a distance error far outside the population baseline (present: `017.txt`).
- Captures carry no timestamp, so route ordering must rest on a stated, defensible basis.
- Test captures (`medidaprueba.txt`, `medidaprueba2.txt`) are not part of the 61-capture study
  set and must not silently enter the indicators.
- A capture's spectrum sits near the noise floor across all bins, indicating a dead capture.
- A capture's spectrum contains extremely high readings suggesting receiver overload or a
  near-field emitter, which inflate a channel indicator if accepted uncritically.
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
  that channel's bins, converting from dBm to linear power before summation and back to dBm for
  reporting.
- **FR-011**: System MUST classify channel contamination against the -60 dBm threshold, applied
  as [NEEDS CLARIFICATION: does a channel count as contaminated when its Parseval mean power
  exceeds -60 dBm, or when any individual bin within it does? Under the any-bin reading all 61
  captures are contaminated in all four channels, which makes the brief's most-versus-least
  question unanswerable; the Parseval-mean reading discriminates cleanly.], and MUST define that
  threshold in exactly one place.
- **FR-012**: System MUST aggregate channel occupancy across the measurement set as
  [NEEDS CLARIFICATION: is a channel's contamination level computed per capture and then
  aggregated across the route, or pooled across all captures at once? The first yields a
  per-position distribution suitable for the heat maps; the second yields a single study-wide
  figure. Both may be needed, but which one is the headline indicator?].
- **FR-013**: System MUST identify the most and least contaminated channel, and the most and
  least contaminated single frequency across the whole system, reporting each with its power.
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
  temperature heat map, and a most-contaminated-frequency heat map.
- **FR-019**: Dashboard MUST read only curated artifacts and MUST NOT reimplement cleaning,
  imputation, or indicator logic.
- **FR-020**: Each dashboard view MUST state its units and colour scale.
- **FR-021**: System MUST omit captures excluded for positioning failure from spatial views
  rather than plotting them at a default location.
- **FR-022**: System MUST state the basis on which the station route is ordered, given the
  absence of a timestamp field.
- **FR-023**: System MUST assess whether sensor temperature relates to measurement quality,
  reporting the statistic computed, its limitation, and the confound that temperature rises
  monotonically across the capture sequence.
- **FR-024**: System MUST produce, for the written report, the evidence artifacts backing each
  claim, such that every report claim cites a specific artifact. The written narrative itself is
  [NEEDS CLARIFICATION: does this feature generate the report document, or produce the evidence
  artifacts the analyst writes the narrative around? This changes scope substantially.].
- **FR-025**: System MUST state which bands it recommends for use and which to avoid, derivable
  from the computed indicators alone.
- **FR-026**: System MUST express report content and every dashboard label in Spanish, matching
  the audience of the deliverable.
- **FR-027**: Optional source-location estimates, if produced, MUST be labelled as estimates with
  their method and uncertainty, and MUST NOT be attempted before the three quality gates pass.

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
- **Channel Occupancy Indicator**: A channel's mean occupancy power in dBm with its
  contaminated-or-clear classification, or an undetermined marker.
- **Station Route**: The ordered sequence of accepted measurement positions describing the
  mobile station's path, with its ordering basis recorded.
- **Band Recommendation**: A use-or-avoid judgement per channel, traced to the indicators
  supporting it.

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
- **SC-005**: All six required dashboard views are present and each states its units and colour
  scale.
- **SC-006**: 100% of claims in the written report cite a specific supporting artifact.
- **SC-007**: The temperature-versus-quality question is answered with a computed statistic, a
  stated limitation, and explicit treatment of the acquisition-order confound.
- **SC-008**: A reviewer can rebuild the full analysis from the raw captures on a clean machine
  using only the declared dependencies and documented instructions.
- **SC-009**: The band recommendation names every channel as recommended or not, with each
  judgement traceable to an indicator value.

## Assumptions

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
  channel indicators, provided the spectrum itself passed quality assessment.
- The study is delivered by 2026-09-28, which bounds the scope of optional work.
