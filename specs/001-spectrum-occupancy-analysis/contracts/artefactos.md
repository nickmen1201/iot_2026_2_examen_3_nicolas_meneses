# Contract: Artifact layout (pipeline ⇄ dashboard ⇄ report ⇄ S3)

Every artifact lives under `artefactos/` (gitignored). CSV files are UTF-8 with `.` as the decimal
separator and 6 decimal places. JSON files use sorted keys, 2-space indent and `ensure_ascii=False`.
The column semantics are defined in [../data-model.md](../data-model.md).

```text
artefactos/
├── staging/
│   └── capturas_crudas.csv          # 63 rows: id_captura, archivo, es_estudio, n_campos, contrato_ok, motivo_contrato, p_0000..p_1023, telemetry
├── calidad/
│   ├── reporte_calidad.csv          # 63 rows: Disposición
│   ├── hallazgos_calidad.csv        # Hallazgo, 0..n per capture
│   └── resumen_imputacion.json      # totals + técnica + justificación per field
├── curado/
│   ├── telemetria.csv               # 61 rows: Telemetría curada
│   └── espectro.csv                 # rows = captures with espectro_utilizable; columns id_captura + f_<MHz>
├── indicadores/
│   ├── potencia_canal_captura.csv   # long: id_captura, canal, potencia_dbm, supera_umbral, lat, lon, estado_posicion
│   ├── indicadores_canal.csv        # 4 rows A-D
│   ├── potencia_por_frecuencia.csv  # 1024 rows: bin, frecuencia_mhz, potencia_media_dbm
│   ├── frecuencias_extremas.json
│   ├── recomendacion.csv            # 4 rows
│   ├── sensibilidad_saturacion.csv  # 4 rows
│   ├── temperatura_calidad.json
│   ├── ruta.json
│   ├── nyquist.json                 # fs_hz, f_max_hz, veredicto (cumple|no_cumple), en_el_limite, implicaciones
│   └── fuentes_estimadas.csv        # bonus (mandatory, written after the gates)
├── figuras/
│   ├── espectro_medio.png  frecuencias_extremas.png  temperatura_piso_ruido.png  potencia_canales.png
└── sitio/                           # published as-is to the S3 static website
    ├── index.html                   # report (figures embedded as base64)
    └── mapas/
        ├── ubicaciones.html  ruta.html
        ├── canal_A.html  canal_B.html  canal_C.html  canal_D.html
        ├── temperatura.html  frecuencia_mas_contaminada.html
        └── fuentes.html                 # bonus: source estimates
```

## Consumers

| Consumer | Reads | Must not read |
|---|---|---|
| `dashboard/app.py` | `indicadores/indicadores_canal.csv`, `recomendacion.csv`, `frecuencias_extremas.json`, `nyquist.json`, `calidad/resumen_imputacion.json`, `sitio/mapas/*.html` | `staging/`, raw data; must not import `espectro.calidad`, `espectro.indicadores` or `espectro.transform` |
| `espectro/reporte.py` | everything in `calidad/`, `curado/`, `indicadores/`, `figuras/`; `reporte/narrativa/*.md` | raw data |
| S3 datalake (`s3://$ESPECTRO_BUCKET_DATALAKE/espectro/`) | everything except `sitio/` | — |
| S3 site (`s3://$ESPECTRO_BUCKET_SITIO/`) | `sitio/` | — |

## Determinism

`staging/`, `calidad/`, `curado/` and `indicadores/` MUST be byte-identical across two runs
(SC-003). The HTML maps and the report are excluded from this check, because Folium generates
random element ids.
