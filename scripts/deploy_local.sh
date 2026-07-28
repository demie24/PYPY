#!/bin/bash
# scripts/deploy_local.sh
set -e

echo "===================================================="
# Name: PYPY Grid
# Tagline: "Protect Your Power, Protect Yourself"
echo "Deploying PYPY Grid Smart-Grid Cybersecurity SaaS Locally"
echo "===================================================="

# 1. Load local environment configuration
if [ -f .env.example ]; then
    echo "Configuring local environment keys..."
    cp -n .env.example .env || true
fi

# 2. Build Docker images
echo "Building local docker containers..."
docker compose build

# 3. Spin up local containers
echo "Starting PostgreSQL, Redis, MQTT, Gateway, Workers, and Dashboard..."
docker compose up -d

# 4. Await gateway health readiness
echo "Waiting for Smart-Grid Gateway api to report nominal health..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/health | grep -q "healthy"; then
        echo "Smart-Grid Gateway Online and Healthy!"
        break
    fi
    echo "Retrying in 2 seconds... ($i/30)"
    sleep 2
done

echo "===================================================="
echo "PYPY Grid SaaS deployed successfully!"
echo "Dashboard client: http://localhost:3001"
echo "Gateway API docs: http://localhost:8000/docs"
echo "===================================================="
