# Quickstart: build, validate, deploy

This guide shows that the feature works end to end. The README carries the same deployment
sequence, and the exact commands that follow are meant to be copied into it. The commands and
artifacts are specified in [contracts/cli.md](contracts/cli.md) and [contracts/artefactos.md](contracts/artefactos.md).

## 1. Local run (Windows / Linux)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
python -m espectro.pipeline --sin-carga
streamlit run dashboard/app.py --server.port 8050
```

Expected results:
- `artefactos/calidad/reporte_calidad.csv` has 63 rows. `008` is `imputado` (posicion, ~600 m).
  `016` is `descartado` with scope `espectro`. `017` is `aceptado` and its finding is
  `posicion_baja_confianza`. `medidaprueba*` are `excluido_prueba`.
- `artefactos/indicadores/indicadores_canal.csv` has 4 rows, each with a `potencia_media_dbm`,
  a state and a rank.
- `artefactos/indicadores/recomendacion.csv` has 2 channels as `usar` and 2 as `evitar`.
- `artefactos/indicadores/fuentes_estimadas.csv` has 4 rows, each `estimado` or `no_soportado`.
- `artefactos/indicadores/nyquist.json` has `"veredicto": "cumple"` and `"en_el_limite": true`.
- `artefactos/sitio/mapas/` holds 9 HTML files (8 required + `fuentes.html`), and `artefactos/sitio/index.html` opens with 4
  figures and a `Fuente:` line under each block.
- http://localhost:8050 shows the verdict header and 9 tabs: ubicaciones, ruta, A, B, C, D,
  temperatura, frecuencia and fuentes, with a legend on each map.

## 2. Validation scenarios

| # | Scenario | How | Pass condition |
|---|---|---|---|
| V1 | Stages run on their own | `python -m espectro.extract && python -m espectro.transform && python -m espectro.presentacion` | Each exits 0, and each stage's folder appears only after that stage runs |
| V2 | Determinism (SC-003) | Run the pipeline, then `find artefactos/staging artefactos/calidad artefactos/curado artefactos/indicadores -type f -exec sha256sum {} + \| sort > h1`, rerun the pipeline, repeat into `h2`, then `diff h1 h2` | No diff |
| V3 | Threshold defined once | `grep -rn "\-60" espectro dashboard` | Only `config.py` defines the constant. Other hits are comments or format strings that use the constant |
| V4 | Dashboard does not recompute | `grep -n "import espectro" dashboard/app.py` | No imports of `calidad`, `indicadores` or `transform` |
| V5 | Artifact change is reflected | Edit one value in `indicadores_canal.csv` and reload the browser | The new value is shown |
| V6 | Raw data untouched | `git status medidas_2026_20` | Clean |
| V7 | Phone access | Open `http://<EIP>:8050` on a phone | The header and maps render |

## 3. S3 buckets (AWS Academy Learner Lab terminal or CloudShell, us-east-1)

```bash
export SUFIJO=nmeneses-2026
export DATALAKE=espectro-datalake-$SUFIJO
export SITIO=espectro-sitio-$SUFIJO

aws s3 mb s3://$DATALAKE --region us-east-1
aws s3 mb s3://$SITIO --region us-east-1

# Sitio estático público (solo el bucket del sitio)
aws s3api put-public-access-block --bucket $SITIO \
  --public-access-block-configuration BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false
aws s3 website s3://$SITIO/ --index-document index.html
aws s3api put-bucket-policy --bucket $SITIO --policy "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Sid\":\"LecturaPublica\",\"Effect\":\"Allow\",\"Principal\":\"*\",\"Action\":\"s3:GetObject\",\"Resource\":\"arn:aws:s3:::$SITIO/*\"}]}"
```

The site URL is `http://$SITIO.s3-website-us-east-1.amazonaws.com`. If the lab denies the
public policy, see research R13 for the fallback.

## 4. EC2 (console steps + commands)

In the console:
1. Launch an instance with Ubuntu Server 24.04 LTS, type **t3.micro**, the analyst's key pair (us-east-1), and IAM
   instance profile **LabInstanceProfile**. The security group allows inbound **22** (prefix list `com.amazonaws.us-east-1.ec2-instance-connect`, IPv4) and
   **8050** (0.0.0.0/0).
2. Under Elastic IPs, allocate an address and associate it with the instance. The dashboard URL
   is then `http://<EIP>:8050`.

Connect with **EC2 Instance Connect** (browser) or `ssh -i <llave>.pem ubuntu@<EIP>`, and run:

```bash
# Swap de 1 GB (t3.micro tiene 1 GB de RAM; pip de numpy/scipy lo necesita)
sudo dd if=/dev/zero of=/swapfile bs=1M count=1024
sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab

sudo apt update && sudo apt install -y git curl
sudo snap install aws-cli --classic
git clone https://github.com/nickmen1201/iot_2026_2_examen_3_nicolas_meneses.git ~/iot
cd ~/iot

# Entorno con Python 3.12 gestionado por uv (ver research R12)
curl -LsSf https://astral.sh/uv/install.sh | sh
~/.local/bin/uv venv --python 3.12 .venv
~/.local/bin/uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -c "import numpy, pandas, scipy, folium, streamlit; print('OK')"

# Pipeline en la nube (modelo de decisión) + carga a S3
export ESPECTRO_BUCKET_DATALAKE=espectro-datalake-nmeneses-2026
export ESPECTRO_BUCKET_SITIO=espectro-sitio-nmeneses-2026
.venv/bin/python -m espectro.pipeline

# Dashboard como servicio systemd
sudo cp deploy/espectro-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now espectro-dashboard
systemctl status espectro-dashboard --no-pager
```

`deploy/espectro-dashboard.service` contains:

```ini
[Unit]
Description=Dashboard ocupación espectro 840-860 MHz
After=network-online.target
Wants=network-online.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/iot
Environment=ESPECTRO_URL_REPORTE=http://espectro-sitio-nmeneses-2026.s3-website-us-east-1.amazonaws.com
ExecStart=/home/ubuntu/iot/.venv/bin/streamlit run dashboard/app.py --server.port 8050 --server.address 0.0.0.0 --server.headless true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## 5. Update cycle after a code or narrative change

```bash
cd ~/iot && git pull
.venv/bin/python -m espectro.pipeline      # requires the two ESPECTRO_BUCKET_* exports
sudo systemctl restart espectro-dashboard
```

## 6. Deployment checks

- `aws s3 ls s3://$DATALAKE/espectro/ --recursive | wc -l` is greater than 0.
- `curl -I http://$SITIO.s3-website-us-east-1.amazonaws.com` returns `200`.
- Stop and start the lab, then open `http://<EIP>:8050` without any SSH step. It is served
  (systemd enable + Elastic IP).
