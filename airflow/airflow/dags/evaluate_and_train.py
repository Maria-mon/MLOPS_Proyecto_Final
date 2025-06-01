from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import os
import mlflow
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

# Configuración
POSTGRES_URI = os.getenv("AIRFLOW_CONN_POSTGRES_DEFAULT")
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI")
MLFLOW_EXPERIMENT_NAME = "HousePricePrediction"
TABLE_CLEAN = "clean_data"
MODEL_NAME = "BestHousePriceModel"

# Argumentos por defecto del DAG
default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=1)
}

with DAG(
    dag_id='evaluate_and_train',
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval='@once',
    catchup=False,
    description='Evalúa si se debe reentrenar y registrar un nuevo modelo',
) as dag:

    def should_train_model(**kwargs):
        engine = create_engine(POSTGRES_URI)
        df = pd.read_sql(f"SELECT * FROM {TABLE_CLEAN}", engine)

        if len(df) < 50:
            kwargs['ti'].xcom_push(key="train_decision", value=False)
            kwargs['ti'].xcom_push(key="reason", value="Menos de 50 registros.")
        elif df["price"].nunique() < 5:
            kwargs['ti'].xcom_push(key="train_decision", value=False)
            kwargs['ti'].xcom_push(key="reason", value="Poca variabilidad en price.")
        else:
            kwargs['ti'].xcom_push(key="train_decision", value=True)

    def train_model(**kwargs):
        engine = create_engine(POSTGRES_URI)
        df = pd.read_sql(f"SELECT * FROM {TABLE_CLEAN}", engine)

        if 'price' not in df.columns:
            raise ValueError("No hay columna 'price' en los datos.")

        df = df.dropna(subset=["price"])
        y = df["price"]

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if "price" in numeric_cols:
            numeric_cols.remove("price")

        if not numeric_cols:
            raise ValueError("No hay columnas numéricas para entrenar.")

        X = df[numeric_cols]
        model = LinearRegression()
        model.fit(X, y)
        preds = model.predict(X)
        rmse = mean_squared_error(y, preds, squared=False)

        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

        with mlflow.start_run() as run:
            mlflow.log_param("features", ",".join(numeric_cols))
            mlflow.log_metric("rmse", rmse)
            mlflow.sklearn.log_model(model, "model", registered_model_name=MODEL_NAME)
            kwargs['ti'].xcom_push(key="new_rmse", value=rmse)
            kwargs['ti'].xcom_push(key="run_id", value=run.info.run_id)

    def compare_models(**kwargs):
        new_rmse = float(kwargs['ti'].xcom_pull(key="new_rmse", task_ids="train_model"))
        run_id = kwargs['ti'].xcom_pull(key="run_id", task_ids="train_model")

        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        client = mlflow.tracking.MlflowClient()
        versions = client.get_latest_versions(MODEL_NAME, stages=["Production"])

        if not versions:
            client.transition_model_version_stage(name=MODEL_NAME, version=1, stage="Production")
            return

        prod_model = versions[0]
        current_rmse = float(client.get_run(prod_model.run_id).data.metrics["rmse"])

        if new_rmse < current_rmse - 1000:
            client.transition_model_version_stage(name=MODEL_NAME, version=prod_model.version + 1, stage="Production")
            print("[INFO] Modelo promovido a producción.")
        else:
            print(f"[INFO] No se promueve: nuevo RMSE={new_rmse} >= actual RMSE={current_rmse}")

    def log_skipped_reason(**kwargs):
        reason = kwargs['ti'].xcom_pull(key="reason", task_ids="should_train_model")
        if not reason:
            return

        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

        with mlflow.start_run(run_name="train_skipped") as run:
            mlflow.log_param("skip_reason", reason)

    check = PythonOperator(task_id="should_train_model", python_callable=should_train_model)
    train = PythonOperator(task_id="train_model", python_callable=train_model)
    compare = PythonOperator(task_id="compare_models", python_callable=compare_models)
    skip = PythonOperator(task_id="log_skipped_reason", python_callable=log_skipped_reason)

    check >> [train, skip]
    train >> compare

