from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import requests
import pandas as pd
import psycopg2
from sqlalchemy import create_engine
import os

# Configuración básica
default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

# Parámetros de conexión
POSTGRES_RAW_URI = os.getenv("AIRFLOW_CONN_POSTGRES_DEFAULT")
RAW_TABLE = "raw_data"
CLEAN_TABLE = "clean_data"
API_URL = "http://10.43.101.108:80"

# DAG
with DAG(
    dag_id='get_ingest_preprocess',
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval='@once',
    catchup=False,
    description='Ingesta de datos desde API externa y preprocesamiento inmediato',
) as dag:

    def get_data_from_api(**kwargs):
        response = requests.get(API_URL)
        
        if response.status_code != 200:
            print(f"API respondió con código {response.status_code}. No se recibirán más datos.")
            return  # Fin de datos, no se lanza excepción

        try:
            data = response.json()
        except Exception as e:
            print(f"Error al parsear JSON: {e}")
            return

        df = pd.DataFrame(data)
        if df.empty:
            print("El lote recibido está vacío. No se realiza inserción.")
            return

        engine = create_engine(POSTGRES_RAW_URI)
        df.to_sql(RAW_TABLE, engine, if_exists='append', index=False)
        print(f"{len(df)} registros guardados en tabla {RAW_TABLE}.")

    def preprocess_data(**kwargs):
        engine = create_engine(POSTGRES_RAW_URI)
        df = pd.read_sql(f"SELECT * FROM {RAW_TABLE}", engine)

        # Filtrado simple y limpieza
        df = df.dropna(subset=["price", "bed", "bath", "house size", "acre lot"])
        df['bed'] = df['bed'].fillna(0)
        df['bath'] = df['bath'].fillna(0.0)
        df['house size'] = df['house size'].astype(float)
        df['acre lot'] = df['acre lot'].astype(float)

        df.to_sql(CLEAN_TABLE, engine, if_exists='append', index=False)
        print(f"{len(df)} registros preprocesados guardados en tabla {CLEAN_TABLE}.")

    get_data = PythonOperator(
        task_id='get_data_from_api',
        python_callable=get_data_from_api,
        provide_context=True
    )

    preprocess = PythonOperator(
        task_id='preprocess_data',
        python_callable=preprocess_data,
        provide_context=True
    )

    get_data >> preprocess

