# PYPY Grid — Kubernetes Deployment Guide
> **"Protect Your Power, Protect Yourself"**

This guide covers deploying the PYPY Grid SaaS Platform to a Kubernetes cluster.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Cluster Setup](#cluster-setup)
3. [Secrets & ConfigMap](#secrets--configmap)
4. [Deploying Services](#deploying-services)
5. [Ingress & TLS](#ingress--tls)
6. [Autoscaling](#autoscaling)
7. [Verifying the Deployment](#verifying-the-deployment)
8. [Rolling Updates via CI/CD](#rolling-updates-via-cicd)

---

## 1. Prerequisites

| Tool | Minimum Version |
|------|----------------|
| kubectl | 1.28+ |
| Kubernetes cluster | 1.28+ (GKE / EKS / k3s) |
| Nginx Ingress Controller | Installed |
| cert-manager (optional) | For TLS |

---

## 2. Cluster Setup

Ensure your `kubectl` is pointed to your cluster:

```bash
kubectl cluster-info
kubectl get nodes
```

Install Nginx Ingress Controller (if not installed):

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.0/deploy/static/provider/cloud/deploy.yaml
```

---

## 3. Secrets & ConfigMap

### Apply ConfigMap (non-sensitive values)

```bash
kubectl apply -f k8s/configmap.yaml
```

### Apply Secrets (sensitive credentials)

> ⚠️ **IMPORTANT**: In production, use a secrets manager (Vault, AWS Secrets Manager, GCP Secret Manager) instead of static secret files.

For local/demo purposes:

```bash
# Update base64 values in k8s/secrets.yaml first, then:
kubectl apply -f k8s/secrets.yaml
```

To encode your own values:

```bash
echo -n "my_secure_password" | base64
```

### Persistent Volume Claim

```bash
kubectl apply -f k8s/pvc.yaml
```

---

## 4. Deploying Services

Apply all manifests in the correct dependency order:

```bash
# Step 1: Config & Storage
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/pvc.yaml

# Step 2: Application deployments
kubectl apply -f k8s/gateway-deployment.yaml
kubectl apply -f k8s/worker-deployment.yaml
kubectl apply -f k8s/digital-twin-deployment.yaml
kubectl apply -f k8s/dashboard-deployment.yaml

# Step 3: Networking
kubectl apply -f k8s/ingress.yaml

# Step 4: Autoscaling
kubectl apply -f k8s/hpa.yaml
```

Check all pods are running:

```bash
kubectl get pods -w
```

---

## 5. Ingress & TLS

The `ingress.yaml` routes traffic for:

| Subdomain | Service |
|-----------|---------|
| `pypygrid.com` | `dashboard-service:80` |
| `app.pypygrid.com` | `dashboard-service:80` |
| `api.pypygrid.com` | `gateway-service:8000` |

### Enable TLS with cert-manager

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Add tls section to k8s/ingress.yaml then reapply
kubectl apply -f k8s/ingress.yaml
```

---

## 6. Autoscaling

The `hpa.yaml` configures HorizontalPodAutoscalers:

| Deployment | Min Replicas | Max Replicas | CPU Threshold |
|------------|-------------|-------------|---------------|
| `gateway-deployment` | 2 | 10 | 80% |
| `worker-deployment` | 2 | 8 | 85% |

View current scaling status:

```bash
kubectl get hpa
```

---

## 7. Verifying the Deployment

```bash
# All pods healthy
kubectl get pods

# All services have endpoints
kubectl get services

# Check gateway API is reachable
kubectl port-forward service/gateway-service 8000:8000
curl http://localhost:8000/api/health
```

Expected response:

```json
{"status": "healthy", "service": "smart-grid-gateway"}
```

---

## 8. Rolling Updates via CI/CD

The GitHub Actions CD workflow (`.github/workflows/cd.yml`) automatically:

1. Builds and pushes Docker images to registry on `main` branch push
2. Applies updated Kubernetes manifests
3. Triggers rolling restarts for Gateway, Dashboard, and Worker deployments

To manually trigger a rolling update:

```bash
kubectl rollout restart deployment/gateway-deployment
kubectl rollout restart deployment/dashboard-deployment
kubectl rollout status deployment/gateway-deployment
```
