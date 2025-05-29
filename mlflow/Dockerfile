FROM python:3.10-slim

# Establecer directorio de trabajo
WORKDIR /mlflow

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivo de requerimientos
COPY requirements.txt ./

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt psycopg2-binary boto3

# Exponer el puerto de MLflow
EXPOSE 5000

# Comando para iniciar el servidor MLflow
CMD ["mlflow", "server", \
     "--backend-store-uri", "postgresql+psycopg2://airflow:airflow@postgres:5432/mlflow_db", \
     "--default-artifact-root", "s3://mlflow-artifacts", \
     "--host", "0.0.0.0", "--port", "5000"]

