#!/bin/bash

COMPANY="$1"
ADMIN_USER="$2"
ADMIN_PASS="$3"
HOST_PORT="$4"
SECRET_KEY="$5"

SERVICE_NAME=$(echo "$COMPANY" | tr '[:upper:]' '[:lower:]' | tr -d ' ')
COMPOSE_FILE="docker-compose.generated.yml"

cat <<EOF > $COMPOSE_FILE
version: '3'
services:
  inference_${SERVICE_NAME}:
    build:
      context: .
      dockerfile: Dockerfile
    image: rag-app
    command: gunicorn inference:app --chdir /app --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001 --timeout 120
    ports:
      - "$((HOST_PORT + 2000)):8001"
    gpus:
      - driver: nvidia
        count: all
        capabilities: ["gpu"]

  db_${SERVICE_NAME}:
    image: postgres:latest
    pull_policy: never
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: root
      POSTGRES_DB: RetrievalSystem
    ports:
      - "$((HOST_PORT + 1000)):5432"
    volumes:
      - db_data_${SERVICE_NAME}:/var/lib/postgresql/data

  app_${SERVICE_NAME}:
    image: rag-app
    environment:
      FLASK_APP: "app:app"
      FLASK_ENV: production
      SECRET_KEY: "$SECRET_KEY"
      DATABASE_URL: "postgresql://postgres:root@db_${SERVICE_NAME}:5432/RetrievalSystem"
      SERVICE_NAME: "$SERVICE_NAME"
      COMPANY_NAME: "$COMPANY"
      PORT: 9000
      ADMIN_USERNAME: "$ADMIN_USER"
      ADMIN_PASSWORD: "$ADMIN_PASS"
      INFERENCE_URL: "http://inference_${SERVICE_NAME}:8001/score"
    ports:
      - "$HOST_PORT:9000"
    volumes:
      - data_volume_${SERVICE_NAME}:/app/data
      - data_volume_${SERVICE_NAME}:/app/videos
    depends_on:
      - db_${SERVICE_NAME}

volumes:
  db_data_${SERVICE_NAME}:
  data_volume_${SERVICE_NAME}:
EOF

echo "Generated $COMPOSE_FILE for company '$COMPANY'."
echo "Starting services with docker-compose..."
docker compose -f $COMPOSE_FILE up -d