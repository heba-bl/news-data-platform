# Déploiement Kubernetes — News Data Platform

## Prérequis
- Minikube ou cluster Kubernetes
- kubectl configuré
- Images Docker buildées

## Déploiement

```bash
# 1. Créer le namespace
kubectl apply -f namespace.yaml

# 2. Créer ConfigMap et Secrets
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml

# 3. Déployer les services infrastructure
kubectl apply -f deployments/zookeeper.yaml
kubectl apply -f deployments/kafka.yaml
kubectl apply -f deployments/postgres.yaml
kubectl apply -f deployments/minio.yaml
kubectl apply -f deployments/grafana.yaml

# 4. Vérifier l'état
kubectl get pods -n news-platform
kubectl get services -n news-platform
```

## Vérification
```bash
kubectl get all -n news-platform
kubectl logs deployment/grafana -n news-platform
```
