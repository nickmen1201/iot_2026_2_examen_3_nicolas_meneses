"""Etapa LOAD: sincroniza los artefactos con S3 usando el AWS CLI (`aws s3 sync`).

- Datalake (privado): todo artefactos/ excepto sitio/  ->  s3://$ESPECTRO_BUCKET_DATALAKE/espectro/
- Sitio estático (público, solo lectura): artefactos/sitio/  ->  s3://$ESPECTRO_BUCKET_SITIO/

Las credenciales vienen del perfil de instancia de la EC2 (LabInstanceProfile); no se guardan llaves.
Si una variable no está definida (corrida local), esa carga se omite sin error.
"""

import os
import subprocess
import sys

from espectro import config


def comandos() -> list[tuple[str, list[str] | None]]:
    """Arma los comandos de sincronización; None significa que el destino no está configurado."""
    datalake = os.environ.get("ESPECTRO_BUCKET_DATALAKE")
    sitio = os.environ.get("ESPECTRO_BUCKET_SITIO")
    return [
        ("datalake", None if not datalake else
         ["aws", "s3", "sync", f"{config.DIR_ARTEFACTOS}/", f"s3://{datalake}/espectro/",
          "--exclude", "sitio/*", "--delete"]),
        ("sitio estático", None if not sitio else
         ["aws", "s3", "sync", f"{config.DIR_SITIO}/", f"s3://{sitio}/", "--delete"]),
    ]


def main() -> int:
    if not config.DIR_ARTEFACTOS.exists():
        print("ERROR: no hay artefactos para cargar. Ejecute python -m espectro.pipeline")
        return 1
    for destino, cmd in comandos():
        if cmd is None:
            print(f"Carga a {destino} omitida: variable no definida")
            continue
        print(f"Carga a {destino}: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True)
        except FileNotFoundError:
            print("ERROR: no se encontró el comando 'aws' (instale el AWS CLI)")
            return 1
        except subprocess.CalledProcessError as e:
            print(f"ERROR: aws s3 sync falló con código {e.returncode}")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
