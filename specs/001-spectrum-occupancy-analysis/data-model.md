# Data Model: Spectrum Occupancy Analysis

Phase 1 output. The entities follow the spec's Key Entities, and each entity maps to a persisted
artifact. The exact file paths and columns are in [contracts/artefactos.md](contracts/artefactos.md).

## Constants (`espectro/config.py`, the single source)

| Name | Value | Used by |
|---|---|---|
| `DIR_MEDIDAS` | `<repo>/medidas_2026_20` (resolved from `__file__`) | extract |
| `DIR_ARTEFACTOS` | `<repo>/artefactos` | all stages |
| `N_BINS` | 1024 | extract, calidad |
| `FC_HZ`, `FS_HZ`, `F_MAX_HZ` | 850e6, 20e6, 10e6 | eje, Nyquist |
| `FRECUENCIAS_MHZ` | `850 + (arange(1024) − 512) · 20/1024` | indicadores, figuras |
| `CANALES` | `{"A": (840, 845), "B": (845, 850), "C": (850, 855), "D": (855, 860)}` MHz | indicadores |
| `UMBRAL_CONTAMINACION_DBM` | −60.0 (**defined only here**) | indicadores, mapas, reporte |
| `LIMITES` | lat 6.0-6.5, lon −75.8…−75.4, alt 1300-2800 m, temp −10…85 °C, dBm −160…+30, error_dist ≤ 5.0 | calidad |
| `MAX_HUECO_BINS`, `MAX_HUECO_CAPTURAS` | 2, 1 | calidad |
| `UMBRAL_SATURACION_DB` | 30.0 | calidad |

## Entities

### Captura cruda (Raw Capture)
The output of extract, one row per file.

- `id_captura` (str, e.g. `"008"`), `archivo` (str), `es_estudio` (bool: name matches `^\d{3}\.txt$`)
- `n_campos` (int), `contrato_ok` (bool), `motivo_contrato` (str | empty)
- `p_0000 … p_1023` (float dBm, raw), `temperatura_c`, `longitud`, `latitud`, `altitud_m`, `error_distancia` (float, raw)

Validation: when `contrato_ok` is false, the values are left empty (NaN) rather than being
reshaped or guessed. The raw files are never written to.

### Perfil espectral (Spectral Profile)
The curated spectrum. It contains only captures with `espectro_utilizable = true`.

- `id_captura` + 1024 dBm columns, named by frequency (`f_840.000000` …), after bin repair.

### Telemetría del sensor (Sensor Telemetry)
Curated. Contains every study capture (61).

- `id_captura`, `orden` (int 1..61 from the file number), `temperatura_c`, `longitud`,
  `latitud`, `altitud_m`, `error_distancia`
- `estado_posicion` ∈ {`medida`, `imputada`, `baja_confianza`, `excluida`}
- `incertidumbre_posicion_m` (float; 0 when measured, about 600 for 008)
- `piso_ruido_dbm` (p10 of the raw spectrum), `delta_piso_db` (relative to the study median)

### Hallazgo de calidad (Quality Finding)
Zero or more per capture.

- `id_captura`, `campo` (e.g. `espectro[517-518]`, `posicion`, `error_distancia`), `regla`,
  `valor_observado`, `limite`, `severidad` ∈ {`info`, `advertencia`, `critico`}, `accion`

### Disposición (Disposition)
Exactly one per file.

- `id_captura`, `disposicion` ∈ {`aceptado`, `corregido`, `imputado`, `descartado`, `excluido_prueba`}
- `alcance` ∈ {`ninguno`, `espectro`, `posicion`, `total`}
- `motivo` (Spanish text), `tecnica` (e.g. `interpolación lineal entre capturas vecinas`), `n_valores_modificados` (int)
- `espectro_utilizable`, `posicion_utilizable` (bool)

State rule: the disposition is decided in precedence order `descartado > imputado > corregido > aceptado`.
The two test files always get `excluido_prueba`.

Resumen de imputación (`resumen_imputacion.json`): the totals per technique and field, each with
its justification, and `total_corregidos` and `total_imputados` (SC-001, SC-011).

### Canal (Channel)
Comes from `CANALES`, with `bin_ini`, `bin_fin` and `n_bins` (256) derived from `FRECUENCIAS_MHZ`.

### Potencia de canal por captura
- `id_captura`, `canal`, `potencia_dbm` (Parseval), `supera_umbral` (bool), plus the joined `latitud`, `longitud`, `estado_posicion` for the maps.

### Indicador de ocupación de canal (Channel Occupancy Indicator)
- `canal`, `f_ini_mhz`, `f_fin_mhz`, `n_capturas`, `potencia_media_dbm` (linear mean → dBm, or empty),
  `potencia_mediana_dbm`, `pct_capturas_sobre_umbral`, `estado` ∈ {`contaminado`, `libre`, `indeterminado`},
  `rango` (1 = the most contaminated)
- `estado = indeterminado` when `n_capturas == 0` (FR-014).

### Frecuencias extremas
- `mas_contaminada`: `{bin, frecuencia_mhz, potencia_dbm}`; `menos_contaminada`: the same fields.

### Ruta de la estación (Station Route)
- `base_ordenamiento` (the text "número de archivo; las capturas no tienen marca de tiempo"),
  `inicio`, `fin` (lat/lon), `longitud_km`, `bbox`, `n_puntos`, `n_imputados`, `n_excluidos`,
  `pares_estacionarios`.

### Evaluación temperatura-calidad
- `n`, `rho_spearman`, `p_spearman`, `rho_parcial_orden`, `p_parcial`, `rho_temp_orden`,
  `conclusion` ∈ {`relación significativa`, `no concluyente`}, `limitacion` (text).

### Sensibilidad a saturación
- For each channel: `potencia_media_dbm_sin_descartados`, `potencia_media_dbm_con_descartados`, `delta_db`, `cambia_estado` (bool) (FR-030).

### Recomendación de banda (Band Recommendation)
- `canal`, `recomendacion` ∈ {`usar`, `evitar`, `sin_datos`}, `estado` (the absolute `contaminado` / `libre` / `indeterminado`), `rango`, `indicador_base` (the `potencia_media_dbm` value), `regla` ("relativa: los 2 canales de menor potencia media → usar; los 2 de mayor → evitar").
- Rule (FR-025): the rule is relative, because all four channels exceed −60 dBm in this data. A channel with no data gets `sin_datos` and is left out of the ranking.

### Estimación de fuente (bonus)
- `canal`, `estado` ∈ {`estimado`, `no_soportado`}, `latitud`, `longitud`, `incertidumbre_m`, `metodo`.

## Relationships

```text
Captura cruda 1─1 Disposición 1─* Hallazgo
Captura cruda 1─1 Telemetría (study set only)
Captura cruda 1─0..1 Perfil espectral (if espectro_utilizable)
Perfil espectral × Canal → Potencia de canal por captura → Indicador (4) → Recomendación (4)
Perfil espectral → Potencia por frecuencia → Frecuencias extremas
Telemetría (posicion_utilizable) → Ruta; Telemetría + Perfil → mapas / temperatura
```
