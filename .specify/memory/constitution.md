<!--
SYNC IMPACT REPORT
Version change: 1.0.0 -> 1.1.0 (2026-09-26)
Bump rationale: MINOR. The source-location extrapolation (the brief's bonus) changes from
  optional (MAY) to mandatory (MUST), still scheduled last and gated on the three quality
  gates. No principle was removed or redefined.
Modified sections:
  - Development Workflow & Quality Gates: bonus clause.

Previous report:
Version change: (unratified template) -> 1.0.0
Bump rationale: Initial ratification. The prior file was an unfilled scaffold with no
  defined governance, so this is the first enforceable version (MAJOR baseline).
Modified principles:
  - [PRINCIPLE_1_NAME] -> I. Data Quality Before Analysis (NON-NEGOTIABLE)
  - [PRINCIPLE_2_NAME] -> II. Reproducible, Traceable ETL
  - [PRINCIPLE_3_NAME] -> III. Physically Grounded Indicators
  - [PRINCIPLE_4_NAME] -> IV. Evidence-Backed Recommendations
  - [PRINCIPLE_5_NAME] -> V. Dashboard as the Delivery Surface
Added sections:
  - Technical Constraints & Data Contract (was [SECTION_2_NAME])
  - Development Workflow & Quality Gates (was [SECTION_3_NAME])
  - Governance rules populated
Removed sections: none
Deferred items:
  - Dashboard framework choice is intentionally left to the planning phase; the
    constitution constrains the required capabilities, not the library.
-->

# Espectro 840-860 MHz (IoT Examen 3, 2026-20) Constitution

## Core Principles

### I. Data Quality Before Analysis (NON-NEGOTIABLE)

No indicator, map, or recommendation may be computed from a measurement that has not first
passed through an explicit quality assessment. The pipeline MUST produce a machine-readable
quality report before any downstream stage runs, and that report MUST state, per measurement
file: whether the row conforms to the data contract, which fields are missing or physically
implausible, and the disposition assigned (accepted, corrected, imputed, or discarded).

Every correction and imputation MUST be counted and justified. The report MUST name the
imputation technique used, the exact number of values it modified, and the reason that
technique is defensible for that field. Silent coercion, silent row-dropping, and
fill-with-zero are forbidden; a discarded measurement MUST remain listed in the report with
its rejection cause.

Rationale: The evaluated deliverable is a technical judgement handed to a regulator. A number
whose provenance and trustworthiness cannot be stated is worse than a missing number.

### II. Reproducible, Traceable ETL

Raw measurements under `medidas_2026_20/` are immutable inputs and MUST NOT be edited in
place. All cleaning, imputation, and transformation MUST happen in code that writes to
separate curated artifacts, so that a full rebuild from raw data to dashboard is a single
documented command and yields identical results on re-run.

The extract, transform, and load stages MUST remain separately runnable and separately
inspectable. Intermediate artifacts (curated measurement table, quality report, per-channel
indicators) MUST be persisted to disk rather than held only in memory, and any random
operation MUST use a fixed seed.

Rationale: The competency being evaluated is the design of an ETL process. A pipeline that
cannot be re-run and audited stage by stage cannot be defended under questioning.

### III. Physically Grounded Indicators

Spectrum indicators MUST follow the physics and the stated measurement geometry, not
convenience. The 1024 spectral bins MUST be mapped to the 840-860 MHz axis before any
channel aggregation, and channels A, B, C, and D MUST be defined as the four consecutive
5 MHz blocks of that band, in ascending frequency order.

Mean channel occupancy power MUST be computed with Parseval summation over the discrete bins
belonging to that channel, with the dBm-to-linear-power conversion performed before summation
and the result converted back to dBm for reporting. A channel is classified as
occupied/contaminated when its power exceeds -60 dBm; this threshold is a fixed constant of
the analysis and MUST appear in exactly one place in the code.

Rationale: Averaging dBm values directly, or hard-coding bin indices without a frequency
mapping, produces numbers that look plausible and are wrong. The threshold and the band plan
are given by the study, not chosen by the analyst.

### IV. Evidence-Backed Recommendations

Every claim in the written report MUST be traceable to a computed artifact. Statements about
the most and least contaminated band, about whether sensor temperature affects measurement
quality, and about the route followed by the mobile station MUST each cite the figure, table,
or indicator file that supports them.

Where the data does not support a conclusion, the report MUST say so explicitly rather than
assert a direction. A correlation reported between temperature and data quality MUST be
accompanied by the statistic computed and its limitation. Recommendations to the Agencia
Nacional del Espectro MUST state which bands to use and which to avoid, and MUST be derivable
from the occupancy indicators alone.

Rationale: The deliverable's value is the argued judgement. Unsupported assertions are the
failure mode the rubric penalizes most directly.

### V. Dashboard as the Delivery Surface

The interactive dashboard MUST be served over a web server and MUST read only curated
artifacts produced by the ETL pipeline; it MUST NOT recompute cleaning or imputation logic of
its own. Duplicating transformation logic in the presentation layer is a violation even when
the results agree.

The dashboard MUST provide: the location of the measurements, the route of the mobile station,
a heat map over Medellin for each of channels A, B, C, and D, a heat map of sensor
temperature, and a heat map of the most contaminated frequency. Each view MUST remain legible
and MUST state its units and its color scale.

Rationale: A single curated source behind both the report and the dashboard is what keeps the
two from disagreeing in front of the evaluator.

## Technical Constraints & Data Contract

The data contract is fixed by the measurement instrument and MUST be validated on ingest:
each measurement file carries 1029 comma-separated values on one line, where columns 1-1024
are the spectrum in dBm across 840-860 MHz, and columns 1025-1029 are, in order, sensor
temperature, longitude, latitude, altitude, and distance error. A file that does not match
this shape MUST be flagged by the quality report, never reshaped by guesswork.

Plausibility bounds MUST be enforced and recorded rather than assumed: coordinates outside
the Medellin metropolitan area, altitudes inconsistent with the city's elevation, and
non-finite or out-of-range power values are quality findings. The legacy GNU Radio acquisition
scripts (`biblioteca.py`, `medir_celular.py`) and `ANTENNA1.csv` are Python 2 era reference
material documenting how the data was captured; they MUST NOT be treated as runnable parts of
the deliverable and MUST NOT be modified.

Analysis and dashboard code MUST be Python 3. Numerical work MUST use the established
scientific stack rather than hand-rolled equivalents. The specific dashboard and mapping
libraries are chosen during planning; whatever is chosen MUST be declared with pinned
versions so the reviewer can reproduce the environment.

## Development Workflow & Quality Gates

Code MUST be structured into named, single-purpose modules with explanatory comments, and
those comments and all reader-facing deliverables MUST be written in Spanish, matching the
audience of the report. Linear scripts with no separation of concerns do not satisfy this
requirement.

Three gates MUST pass before the work is considered deliverable:

1. **Quality gate** - the pipeline runs end to end from raw data with no errors, and the
   quality report is produced with imputation counts filled in.
2. **Indicator gate** - the four channel occupancy values are computed via Parseval summation
   and the most and least contaminated channels are identified with their numbers.
3. **Presentation gate** - the dashboard starts, serves every view required by Principle V,
   and the written report cites the artifacts backing each of its claims.

Failures MUST be fixed at their root cause. Suppressing a warning, widening a plausibility
bound to make data pass, or hard-coding a result to make a view render are violations.
The extrapolation work that estimates the geographic source of contamination per band is part
of the deliverable and MUST be done. It is built last and runs only after all three gates pass,
and each estimate MUST be labelled as an estimate with its method and uncertainty stated.

## Governance

This constitution supersedes ad-hoc practice for this repository. Where a convenient shortcut
conflicts with a principle here, the principle wins, and the shortcut MUST be either abandoned
or justified in writing as a documented exception in the affected artifact.

Amendments MUST be made by updating this file, recording the change in a Sync Impact Report
comment at its top, and bumping the version. Versioning is semantic: MAJOR for removing or
redefining a principle in a backward-incompatible way, MINOR for adding a principle or
materially expanding guidance, PATCH for clarifications and wording that change no obligation.
The ratification date is fixed; the last-amended date MUST be updated on every substantive
change.

Compliance is reviewed at each of the three quality gates above, and at every Spec Kit phase
transition: `/speckit-plan` MUST confirm the plan violates no principle, `/speckit-tasks` MUST
carry the gates into the task list, and `/speckit-implement` MUST NOT mark work complete while
a gate is failing. Complexity MUST be justified against Principle II and Principle V; if a
simpler pipeline satisfies the deliverable, the simpler pipeline is required.

**Version**: 1.1.0 | **Ratified**: 2026-09-25 | **Last Amended**: 2026-09-26
