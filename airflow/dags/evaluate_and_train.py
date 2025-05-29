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

default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=1)
}

POSTGRES_URI = os.getenv("AIRFLOW_CONN_POSTGRES_DEFAULT")
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI")
MLFLOW_EXPERIMENT_NAME = "HousePricePrediction"

TABLE_CLEAN = "clean_data"
MODEL_NAME = "BestHousePriceModel"

with DAG(
    dag_id='evaluate_and_train',
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval='@once',
    catchup=False,
    description='Evalúa si se debe reentrenar un modelo con los datos acumulados',
) as dag:

    def should_train_model(**kwargs):
        engine = create_engine(POSTGRES_URI)
        df = pd.read_sql(f"SELECT * FROM {TABLE_CLEAN}", engine)

        if df.shape[0] < 100:
            kwargs['ti'].xcom_push(key="train_decision", value=False)
            kwargs['ti'].xcom_push(key="reason", value="Menos de 100 registros en CLEAN.")
            return

        grouped = df.groupby('city')['price'].mean()
        change = grouped.std()

        if change < 10000:
            kwargs['ti'].xcom_push(key="train_decision", value=False)
            kwargs['ti'].xcom_push(key="reason", value="Sin variación significativa en precio promedio por ciudad.")
        else:
            kwargs['ti'].xcom_push(key="train_decision", value=True)

    def train_model(**kwargs):
        engine = create_engine(POSTGRES_URI)
        df = pd.read_sql(f"SELECT * FROM {TABLE_CLEAN}", engine)

        df = df.dropna(subset=["price", "bed", "bath", "house size", "acre lot"])
        X = df[["bed", "bath", "house size", "acre lot"]]
        y = df["price"]

        model = LinearRegression()
        model.fit(X, y)
        preds = model.predict(X)
        rmse = mean_squared_error(y, preds, squared=False)

        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

        with mlflow.start_run() as run:
            mlflow.log_param("model_type", "LinearRegression")
            mlflow.log_metric("rmse", rmse)
            mlflow.sklearn.log_model(model, "model", registered_model_name=MODEL_NAME)
            kwargs['ti'].xcom_push(key="new_rmse", value=rmse)
            kwargs['ti'].xcom_push(key="run_id", value=run.info.run_id)

    def compare_models(**kwargs):
        new_rmse = kwargs['ti'].xcom_pull(key="new_rmse", task_ids="train_model")
        new_rmse = float(new_rmse)

        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        client = mlflow.tracking.MlflowClient()
        versions = client.get_latest_versions(MODEL_NAME, stages=["Production"])

        if not versions:
            # No hay modelo en producción, promover directamente
            run_id = kwargs['ti'].xcom_pull(key="run_id", task_ids="train_model")
            client.transition_model_version_stage(name=MODEL_NAME, version=1, stage="Production")
            return

        prod_model = versions[0]
        prod_run = client.get_run(prod_model.run_id)
        current_rmse = float(prod_run.data.metrics["rmse"])

        if new_rmse < current_rmse - 1000:  # Umbral de mejora
            client.transition_model_version_stage(name=MODEL_NAME, version=prod_model.version + 1, stage="Production")
        else:
            print(f"Modelo nuevo no mejora suficiente: {new_rmse} >= {current_rmse}")

    def log_skipped_reason(**kwargs):
        reason = kwargs['ti'].xcom_pull(key="reason", task_ids="should_train_model")
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

        with mlflow.start_run(run_name="batch_skipped") as run:
            mlflow.log_param("skip_reason", reason)

    check = PythonOperator(
        task_id="should_train_model",
        python_callable=should_train_model,
        provide_context=True,
    )

    train = PythonOperator(
        task_id="train_model",
        python_callable=train_model,
        provide_context=True,
    )

    compare = PythonOperator(
        task_id="compare_models",
        python_callable=compare_models,
        provide_context=True,
    )

    skip = PythonOperator(
        task_id="log_skipped_reason",
        python_callable=log_skipped_reason,
        provide_context=True,
    )

    check >> [train, skip]
    train >> compare

