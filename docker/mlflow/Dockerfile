# MLflow tracking server, built from scratch rather than a pre-built image
# so exactly what's installed is known: mlflow itself, psycopg2 for the
# Postgres backend store, and boto3 for the S3-compatible (Cloudflare R2)
# artifact store. Pinned to match this repo's own client requirement
# (pyproject.toml's "tracking" extra: mlflow>=2.12) -- server and client
# don't need to match exactly, but staying in the same major line avoids
# surprises.
FROM python:3.12-slim

RUN pip install --no-cache-dir \
    "mlflow>=2.12,<3" \
    psycopg2-binary \
    boto3

EXPOSE 5000
