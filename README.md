# Ocupación del espectro 840-860 MHz en Medellín — IoT Examen 3 (2026-20)

Proceso ETL sobre 61 capturas de una estación móvil de monitoreo del espectro. El proceso produce:

- un reporte de calidad de datos (disposición por captura, imputaciones contadas y justificadas);
- indicadores de contaminación por canal (A, B, C y D de 5 MHz), calculados por suma de Parseval
  y comparados con el umbral de −60 dBm;
- un informe técnico en HTML (español) para la ANE, con figuras y tablas insertadas automáticamente;
- mapas de calor interactivos sobre OpenStreetMap de Medellín;
- un dashboard web (Streamlit) desplegado en AWS, con copia estática del informe en S3.

Especificación y diseño: `specs/001-spectrum-occupancy-analysis/` (spec, plan, tareas, contratos).

## Estructura

```text
requirements.txt                   versiones fijadas
medidas_2026_20/                   datos crudos (inmutables; viajan con el repositorio)
espectro/                          paquete del pipeline
├── config.py                      rutas relativas, eje de frecuencia, canales, umbral (única definición), límites
├── extract.py                     E: lee *.txt → artefactos/staging/ y valida el contrato de 1029 valores
├── calidad.py                     disposiciones, límites de plausibilidad, interpolación, saturación
├── indicadores.py                 Parseval por captura y canal, agregados, frecuencias extremas, recomendación
├── analisis.py                    ruta, temperatura vs piso de ruido, Nyquist, sensibilidad a saturación
├── transform.py                   T: orquesta calidad → indicadores → análisis
├── mapas.py, reporte.py           mapas Folium e informe HTML
├── presentacion.py                orquesta mapas + informe
├── fuentes.py                     bonus: estimación de la ubicación de las fuentes por canal
├── load.py                        L: aws s3 sync al datalake y al sitio estático
├── pipeline.py                    reconstrucción completa + compuertas de calidad
└── plantillas/reporte.html.j2
reporte/narrativa/*.md             texto interpretativo del analista (se inserta en el informe)
dashboard/app.py                   dashboard Streamlit (solo lee artefactos/)
deploy/espectro-dashboard.service  unidad systemd para la EC2
tests/                             pruebas unitarias (pytest)
artefactos/                        salidas generadas (no versionadas)
```

## Ejecución local

Requiere Python 3.12.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
python -m espectro.pipeline --sin-carga
streamlit run dashboard/app.py --server.port 8050
```

Abrir http://localhost:8050 (dashboard) y `artefactos/sitio/index.html` (informe).

### Etapas por separado

| Comando | Lee | Escribe |
|---|---|---|
| `python -m espectro.extract` | `medidas_2026_20/*.txt` | `artefactos/staging/` |
| `python -m espectro.transform` | `artefactos/staging/` | `artefactos/calidad/`, `curado/`, `indicadores/` |
| `python -m espectro.presentacion` | artefactos anteriores + `reporte/narrativa/` | `artefactos/sitio/` (informe y mapas), `artefactos/figuras/` |
| `python -m espectro.fuentes` | `indicadores/`, `curado/` | `indicadores/fuentes_estimadas.csv`, `sitio/mapas/fuentes.html` |
| `python -m espectro.load` | `artefactos/` | S3 (si `ESPECTRO_BUCKET_DATALAKE` / `ESPECTRO_BUCKET_SITIO` están definidas) |
| `python -m espectro.pipeline [--sin-carga]` | datos crudos | todo lo anterior; código 2 si una compuerta falla |

### Artefactos principales

- `artefactos/calidad/reporte_calidad.csv`: una disposición por archivo (63). Además `hallazgos_calidad.csv` y `resumen_imputacion.json`.
- `artefactos/curado/telemetria.csv` y `espectro.csv`: conjunto curado.
- `artefactos/indicadores/indicadores_canal.csv`, `recomendacion.csv`, `frecuencias_extremas.json`, `nyquist.json`, `temperatura_calidad.json`, `ruta.json`, `sensibilidad_saturacion.csv`, `fuentes_estimadas.csv`.
- `artefactos/sitio/index.html` (informe) y `artefactos/sitio/mapas/*.html` (9 mapas).

## Despliegue en AWS (Learner Lab, us-east-1)

Arquitectura: el repositorio se clona en una EC2, que ejecuta el pipeline (modelo de decisión en la
nube), carga los artefactos curados a un bucket S3 (datalake) y publica el informe y los mapas en un
bucket S3 con alojamiento web estático. El dashboard corre en la misma EC2 como servicio systemd.

### 1. Buckets S3 (terminal del Learner Lab o CloudShell)

```bash
export SUFIJO=nmeneses-2026
export DATALAKE=espectro-datalake-$SUFIJO
export SITIO=espectro-sitio-$SUFIJO

aws s3 mb s3://$DATALAKE --region us-east-1
aws s3 mb s3://$SITIO --region us-east-1

# Sitio estático público (solo el bucket del sitio; el datalake queda privado)
aws s3api put-public-access-block --bucket $SITIO \
  --public-access-block-configuration BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false
aws s3 website s3://$SITIO/ --index-document index.html
aws s3api put-bucket-policy --bucket $SITIO --policy "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Sid\":\"LecturaPublica\",\"Effect\":\"Allow\",\"Principal\":\"*\",\"Action\":\"s3:GetObject\",\"Resource\":\"arn:aws:s3:::$SITIO/*\"}]}"
```

URL del sitio: `http://espectro-sitio-nmeneses-2026.s3-website-us-east-1.amazonaws.com`.

Si el laboratorio niega `PutBucketPolicy` o `PutPublicAccessBlock`, el dashboard queda como única
superficie pública. En ese caso, para compartir el informe se puede generar un enlace temporal con
`aws s3 presign s3://$SITIO/index.html --expires-in 604800`.

### 2. EC2 (consola)

1. Lanzar una instancia **Ubuntu Server 24.04 LTS**, tipo **t3.micro**, con un par de llaves propio
   (us-east-1) y perfil de IAM **LabInstanceProfile**.
2. Grupo de seguridad, reglas de entrada:
   - puerto **22**, desde la lista de prefijos `com.amazonaws.us-east-1.ec2-instance-connect` (IPv4);
   - puerto **8050**, desde `0.0.0.0/0`.
3. En *Direcciones IP elásticas*, asignar una dirección y asociarla a la instancia. El dashboard queda
   fijo en `http://<EIP>:8050`.

### 3. EC2 (terminal: *Conectar → EC2 Instance Connect*, usuario `ubuntu`)

```bash
# Swap de 1 GB (t3.micro tiene 1 GB de RAM; pip de numpy/scipy lo necesita)
sudo dd if=/dev/zero of=/swapfile bs=1M count=1024
sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab

sudo apt update && sudo apt install -y git python3-venv python3-pip
sudo snap install aws-cli --classic
git clone https://github.com/nickmen1201/iot_2026_2_examen_3_nicolas_meneses.git ~/iot
cd ~/iot
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

# Pipeline en la nube (modelo de decisión) + carga a S3
export ESPECTRO_BUCKET_DATALAKE=espectro-datalake-nmeneses-2026
export ESPECTRO_BUCKET_SITIO=espectro-sitio-nmeneses-2026
.venv/bin/python -m espectro.pipeline

# Dashboard como servicio systemd (vuelve solo cuando el lab reinicia la instancia)
sudo cp deploy/espectro-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now espectro-dashboard
systemctl status espectro-dashboard --no-pager
```

### 4. Actualizar después de un cambio de código o de narrativa

```bash
cd ~/iot && git pull
export ESPECTRO_BUCKET_DATALAKE=espectro-datalake-nmeneses-2026
export ESPECTRO_BUCKET_SITIO=espectro-sitio-nmeneses-2026
.venv/bin/python -m espectro.pipeline
sudo systemctl restart espectro-dashboard
```

### 5. Comprobaciones

```bash
aws s3 ls s3://espectro-datalake-nmeneses-2026/espectro/ --recursive | wc -l   # > 0
curl -I http://espectro-sitio-nmeneses-2026.s3-website-us-east-1.amazonaws.com  # HTTP 200
```

- Abrir `http://<EIP>:8050` desde un celular con datos móviles.
- Detener y volver a iniciar el lab: el dashboard vuelve sin entrar por SSH (`systemctl enable` + IP elástica).

## Enlaces de entrega

- Dashboard en vivo: `http://<EIP>:8050` (requiere el lab encendido).
- Informe y mapas (copia estática): `http://espectro-sitio-nmeneses-2026.s3-website-us-east-1.amazonaws.com`.
