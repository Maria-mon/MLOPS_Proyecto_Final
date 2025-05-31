#!/bin/bash

# Namespace
NAMESPACE=mlops

echo "Iniciando port-forward para todos los servicios del proyecto MLOPS_Proyecto_Final_2025..."

# MLflow
kubectl port-forward svc/mlflow 5000:5000 -n $NAMESPACE &
echo "MLflow disponible en http://localhost:5000"

# MinIO
kubectl port-forward svc/minio-nodeport 9000:9000 -n $NAMESPACE &
echo "MinIO disponible en http://localhost:9000"

# PostgreSQL
kubectl port-forward svc/postgres 5432:5432 -n $NAMESPACE &
echo "PostgreSQL disponible en localhost:5432"

# Prometheus
kubectl port-forward svc/prometheus 9090:9090 -n $NAMESPACE &
echo "Prometheus disponible en http://localhost:9090"

# Grafana
kubectl port-forward svc/grafana 3000:3000 -n $NAMESPACE &
echo "Grafana disponible en http://localhost:3000"

# Inference API
kubectl port-forward svc/inference-api 8000:8000 -n $NAMESPACE &
echo "Inference API disponible en http://localhost:8000"

# Streamlit UI
kubectl port-forward svc/streamlit-ui 8501:8501 -n $NAMESPACE &
echo "Streamlit UI disponible en http://localhost:8501"

echo "Todos los port-forward han sido lanzados. Usa CTRL+C para detenerlos si estás en modo interactivo."
