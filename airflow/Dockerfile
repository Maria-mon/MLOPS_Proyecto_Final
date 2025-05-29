FROM apache/airflow:2.8.1

USER airflow

# Crear y usar carpeta de trabajo propia del usuario airflow
WORKDIR /home/airflow

# Copiar requirements al entorno del usuario
COPY requirements.txt requirements.txt

# Instalar requirements localmente
RUN pip install --no-cache-dir --user -r requirements.txt

# Crear los directorios de logs dentro de una ruta accesible
RUN mkdir -p /home/airflow/logs/scheduler \
             /home/airflow/logs/webserver \
             /home/airflow/logs/task \
             /home/airflow/logs/dag_processor_manager

# Exportar variable de entorno para logs (opcional, si los usas en airflow.cfg)
ENV AIRFLOW__LOGGING__BASE_LOG_FOLDER=/home/airflow/logs

# No definimos CMD aquí, lo hace docker-compose (webserver o scheduler)















