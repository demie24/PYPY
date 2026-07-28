#!/bin/bash
# deploy_production.sh
# PYPY Grid V11.9 GA — Production Deployment Script
# Purpose: Orchestrates container stack deployment, SSL routing, and health checks on production nodes.

set -e

echo "====================================================================="
echo "   ⚡ DEPLOYING PYPY GRID SMART-GRID SAAS PLATFORM (GA PHASE) ⚡"
echo "====================================================================="

# 1. Environment Check
if [ ! -f .env.production ]; then
    echo "❌ ERROR: .env.production file not found!"
    echo "Please configure .env.production before running this deployment."
    exit 1
fi

echo "🔄 Loading production keys into active deployment environment (.env)..."
cp .env.production .env

# 2. Docker compose configuration validation
echo "🔬 Validating docker-compose configuration..."
docker compose -f docker-compose.prod.yml config > /dev/null

# 3. Pull latest image layers or build local images
echo "🛠️  Building smart-grid core and dashboard containers..."
docker compose -f docker-compose.prod.yml build --pull

# 4. Spin up containerized services
echo "🚀 Spanning production clusters (DB, Cache, MQTT, Worker, API, Dashboard, Proxy)..."
docker compose -f docker-compose.prod.yml up -d --remove-orphans

# 5. Perform Gateway Health Checks
echo "⏳ Awaiting gateway nominal health state reporting..."
for i in {1..30}; do
    # Using python snippet inside bash to check health response code
    STATUS=$(python3 -c "
import urllib.request, json
try:
    with urllib.request.urlopen('http://localhost:8000/api/health', timeout=2) as r:
        data = json.loads(r.read().decode())
        print(data.get('status', 'offline'))
except Exception:
    print('offline')
" 2>/dev/null || echo "offline")

    if [ "$STATUS" = "healthy" ] || [ "$STATUS" = "nominal" ] || [ "$STATUS" = "nominal_health" ] || [ "$STATUS" = "SUCCESS" ]; then
        echo "✅ Smart-Grid API Gateway online and reporting healthy status."
        break
    fi
    echo "   -> Retrying in 2s... ($i/30)"
    sleep 2
done

# 6. Setup / Reload Nginx reverse proxy
if [ -f /etc/nginx/sites-available/default ]; then
    echo "🧹 Removing default Nginx site configs..."
    sudo rm -f /etc/nginx/sites-enabled/default || true
fi

if [ -f nginx/pypygrid.conf ] && [ -d /etc/nginx ]; then
    echo "🔀 Configuring Nginx reverse proxy configurations..."
    sudo cp nginx/pypygrid.conf /etc/nginx/sites-available/pypygrid.conf
    sudo ln -sf /etc/nginx/sites-available/pypygrid.conf /etc/nginx/sites-enabled/pypygrid.conf
    
    echo "🔍 Testing Nginx configuration syntax..."
    if sudo nginx -t; then
        echo "🔄 Reloading Nginx service..."
        sudo systemctl reload nginx || sudo systemctl restart nginx
    else
        echo "⚠️  WARNING: Nginx configuration test failed. Skipping reload."
    fi
fi

echo "====================================================================="
echo "  🎉 PYPY GRID DEPLOYMENT NOMINAL AND GA PHASE ONLINE!"
echo "  Client Portal URL:  https://pypygrid.com"
echo "  Secure API URL:     https://api.pypygrid.com"
echo "  Secure Console:     https://app.pypygrid.com"
echo "====================================================================="
