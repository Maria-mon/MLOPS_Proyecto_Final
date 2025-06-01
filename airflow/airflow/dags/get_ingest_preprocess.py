import pandas as pd
import requests
import logging
import sqlalchemy
from sqlalchemy import create_engine, text
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

# Configuración
POSTGRES_URI = "postgresql+psycopg2://airflow:airflow@172.17.0.1:30432/airflow"
RAW_TABLE = "raw_data"
CLEAN_TABLE = "clean_data"

def get_data_from_api(**kwargs):
    API_URL = "http://10.43.101.108:80/data"
    params = {"group_number": 2, "day": "Tuesday"}

    logging.info(f"[INFO] Haciendo request a {API_URL} con params {params}")
    response = requests.get(API_URL, params=params)
    response.raise_for_status()
    data = response.json()

    if not data:
        logging.warning("[WARNING] No se recibió data del API.")
        return

    df = pd.DataFrame(data)

    if 'data' in df.columns:
        data_expanded = pd.json_normalize(df['data'])
        df = df.drop(columns=['data'])
        df = pd.concat([df, data_expanded], axis=1)
        logging.info(f"[INFO] Data expandida. Nuevas columnas: {data_expanded.columns.tolist()}")

    engine = create_engine(POSTGRES_URI)
    with engine.connect() as conn:
        existing_columns = []
        try:
            result = conn.execute(text(f"SELECT * FROM {RAW_TABLE} LIMIT 0"))
            existing_columns = result.keys()
        except Exception:
            logging.info(f"[INFO] Tabla '{RAW_TABLE}' no existe. Será creada.")

        if existing_columns:
            for col in df.columns:
                if col not in existing_columns:
                    conn.execute(text(f'ALTER TABLE {RAW_TABLE} ADD COLUMN "{col}" TEXT'))
                    logging.info(f"[INFO] Columna '{col}' agregada a la tabla.")

            for col in existing_columns:
                if col not in df.columns:
                    df[col] = pd.NA
                    logging.info(f"[INFO] Columna faltante '{col}' añadida al DataFrame con NaN.")

            df = df[[col for col in existing_columns if col in df.columns] +
                    [col for col in df.columns if col not in existing_columns]]

    df = df.astype(str)
    df.to_sql(RAW_TABLE, engine, if_exists="append", index=False)
    logging.info(f"[INFO] {len(df)} registros guardados en la tabla '{RAW_TABLE}'")

def preprocess_data(**kwargs):
    engine = create_engine(POSTGRES_URI)
    df = pd.read_sql(f"SELECT * FROM {RAW_TABLE}", engine)

    # Eliminamos duplicados
    df = df.drop_duplicates()

    # Convertimos columnas que deberían ser numéricas
    numeric_cols = ['price', 'bed', 'bath', 'acre lot', 'house size']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Guardamos en clean_data
    df.to_sql(CLEAN_TABLE, engine, if_exists="replace", index=False)
    logging.info(f"[INFO] Datos procesados guardados en la tabla '{CLEAN_TABLE}'")

# DAG definition
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2024, 1, 1),
    'retries': 1
}

with DAG(
    dag_id='get_ingest_preprocess',
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
    tags=["etl", "api"]
) as dag:

    get_data_task = PythonOperator(
        task_id='get_data_from_api',
        python_callable=get_data_from_api
    )

    preprocess_task = PythonOperator(
        task_id='preprocess_data',
        python_callable=preprocess_data
    )

    get_data_task >> preprocess_task

