# PYPY Grid — Deployment Guide
> **"Protect Your Power, Protect Yourself"**

This guide covers local development setup, production VPS deployment, and Docker Compose orchestration for the PYPY Grid Smart-Grid Cybersecurity SaaS Platform.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Local Deployment (Docker Compose)](#local-deployment-docker-compose)
4. [Production VPS Deployment](#production-vps-deployment)
5. [Database Backup & Restore](#database-backup--restore)
6. [Security Hardening Checklist](#security-hardening-checklist)
7. [Monitoring & Logs](#monitoring--logs)

---

## 1. Prerequisites

| Tool | Minimum Version |
|------|----------------|
| Docker | 24.x |
| Docker Compose | v2.x |
| Node.js | 18.x |
| Python | 3.10+ |
| Git | 2.x |

---

## 2. Environment Configuration

Copy and configure the `.env` file:

```bash
cp .env.example .env
```

Key variables:

```env
DATABASE_URL=postgresql://pypy_admin:YOUR_SECURE_PASSWORD@postgres:5432/pypy_saas
REDIS_URL=redis://redis:6379/0
JWT_SECRET=YOUR_RANDOM_JWT_SECRET_KEY
ALLOWED_ORIGINS=https://pypygrid.com,https://app.pypygrid.com
BILLING_PROVIDER=manual   # or stripe / toyyibpay
STRIPE_SECRET_KEY=sk_live_xxxx
```

---

## 3. Local Deployment (Docker Compose)

### Quick Start

```bash
./scripts/deploy_local.sh
```

This will:
1. Copy `.env.example` → `.env` if missing
2. Build all Docker images
3. Start PostgreSQL, Redis, MQTT, Gateway, Workers, and Dashboard
4. Poll the Gateway health endpoint for readiness

### Manual Steps

```bash
docker compose build
docker compose up -d
docker compose ps          # Verify all containers are healthy
docker compose logs -f gateway
```

### Service Ports

| Service | Port |
|---------|------|
| Dashboard | http://localhost:3001 |
| Gateway API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |
| MQTT | localhost:1884 |

---

## 4. Production VPS Deployment

```bash
# Pull latest release
git pull origin main

# Ensure .env is configured for production
nano .env

# Deploy
./scripts/deploy_vps.sh
```

### SSL/HTTPS with Certbot

After `deploy_vps.sh` completes, secure your domains:

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d pypygrid.com -d app.pypygrid.com -d api.pypygrid.com
```

Certbot will automatically renew every 90 days.

### Nginx Configuration

The gateway routes traffic as follows:

| Domain | Backend |
|--------|---------|
| `pypygrid.com` | Dashboard (port 80) |
| `app.pypygrid.com` | Dashboard (port 80) |
| `api.pypygrid.com` | Gateway API (port 8000) |

---

## 5. Database Backup & Restore

### Backup

```bash
./scripts/backup.sh
```

Backups are stored in `./backups/` as timestamped `.tar.gz` archives.

### Restore

```bash
# Decompress
tar -xzf backups/pypy_backup_YYYYMMDD_HHMMSS.tar.gz -C backups/restore/

# Restore to running Postgres
docker exec -i smart_grid_postgres psql -U pypy_admin pypy_saas < backups/restore/pypy_db_*.sql
```

---

## 6. Security Hardening Checklist

- [x] **JWT Expiry**: Tokens expire in 15 minutes (900 seconds)
- [x] **Rate Limiting**: 150 requests/minute per IP enforced at gateway
- [x] **CORS Hardening**: `ALLOWED_ORIGINS` env var restricts cross-origin access
- [x] **Security Headers**: HSTS, X-Frame-Options DENY, nosniff, XSS protection enabled
- [x] **Secret Management**: Passwords and JWT secrets in `.env` (never committed)
- [x] **HTTPS Ready**: Nginx configured for Certbot SSL certificates
- [x] **Docker Restart Policies**: All services configured with `restart: always`
- [x] **Health Checks**: All containers have liveness and readiness probes

---

## 7. Monitoring & Logs

View live logs per service:

```bash
docker compose logs -f gateway         # FastAPI Gateway
docker compose logs -f celery_worker   # Simulation Worker
docker compose logs -f postgres        # Database
```

Check container health status:

```bash
docker compose ps
```
