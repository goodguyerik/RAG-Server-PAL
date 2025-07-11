#!/bin/bash

COMPANY_NAME=${COMPANY_NAME:-DefaultCompany}
PORT=${PORT:-9000}
ADMIN_USERNAME=${ADMIN_USERNAME:-admin}
ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin}
SERVICE_NAME=${SERVICE_NAME:-db}
SECRET_KEY=${SECRET_KEY:-a_default_insecure_key}
INFERENCE_URL=${INFERENCE_URL:-http://inference_:8001/score}

echo "Starting container for company: $COMPANY_NAME on port: $PORT"
echo "Using ADMIN_USERNAME: $ADMIN_USERNAME and ADMIN_PASSWORD: $ADMIN_PASSWORD"

cat <<EOF > config.py
# Auto-generated configuration file
COMPANY_NAME = "${COMPANY_NAME}"
LOGO_PATH = "static/logos/${COMPANY_NAME}.png"
ADMIN_USERNAME = "${ADMIN_USERNAME}"
ADMIN_PASSWORD = "${ADMIN_PASSWORD}"
SERVICE_NAME = "${SERVICE_NAME}"
SECRET_KEY = "${SECRET_KEY}"
INFERENCE_URL = "${INFERENCE_URL}"
EOF

exec gunicorn --timeout 1200 -w 1 --log-level debug -b 0.0.0.0:$PORT app:app