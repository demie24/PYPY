#!/bin/bash
# scripts/deploy_vps.sh
set -e

echo "===================================================="
echo "Deploying PYPY Grid Smart-Grid SaaS on VPS Host"
echo "===================================================="

# 1. Update system packages
echo "Updating packages..."
sudo apt-get update && sudo apt-get install -y curl git ufw nginx

# 2. Configure Firewall (allow ssh, http, https, mqtt port)
echo "Setting up UFW Firewall profiles..."
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 1884/tcp
sudo ufw --force enable

# 3. Pull latest main branch updates
echo "Pulling production release tags..."
git pull origin main

# 4. Configure Production Environment Variables
if [ ! -f .env ]; then
    echo "CRITICAL: Please configure .env file before running production deployments."
    exit 1
fi

# 5. Start Production Stack via Docker Compose
echo "Launching production container orchestration engine..."
docker compose -f docker-compose.yml up -d --remove-orphans

# 6. Configure Nginx Reverse Proxy & SSL Certificates
echo "Configuring Nginx routing..."
sudo cp nginx.conf /etc/nginx/sites-available/pypygrid.conf
sudo ln -sf /etc/nginx/sites-available/pypygrid.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default || true

# Check Nginx config and restart
sudo nginx -t
sudo systemctl restart nginx

echo "===================================================="
echo "PYPY Grid SaaS VPS deployment complete!"
echo "Main web portal active. Setup SSL via Certbot: certbot --nginx"
echo "===================================================="
