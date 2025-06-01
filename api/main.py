from fastapi import FastAPI, Request
import mlflow.pyfunc
import pandas as pd
import os
from sqlalchemy import create_engine
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
from starlette.status import HTTP_400_BAD_REQUEST
import numpy as np

# Configuración
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MODEL_NAME = os.getenv("MODEL_NAME", "BestHousePriceModel")
POSTGRES_URI = os.getenv("AIRFLOW_CONN_POSTGRES_DEFAULT")

app = FastAPI(title="House Price Prediction API")

PREDICTION_COUNT = Counter("inference_requests_total", "Número total de solicitudes de inferencia")
PREDICTION_ERRORS = Counter("inference_errors_total", "Errores durante la inferencia")

# Cargar modelo desde MLflow
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
model = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}/Production")

# Inferir columnas esperadas dinámicamente
expected_columns = ["group_number", "batch_number", "bed", "bath"]  # <- extraído manualmente o desde predict error

@app.post("/predict")
async def predict(request: Request):
    try:
        input_json = await request.json()
        df = pd.DataFrame([input_json])

        # Agregar columnas faltantes como NaN
        for col in expected_columns:
            if col not in df.columns:
                df[col] = np.nan

        # Reordenar y eliminar columnas extras
        df = df[expected_columns]

        # Realizar predicción
        prediction = model.predict(df)[0]
        PREDICTION_COUNT.inc()

        try:
            engine = create_engine(POSTGRES_URI)
            df["prediction"] = prediction
            df.to_sql("inference_log", engine, if_exists="append", index=False)
        except Exception as db_err:
            print(f"[WARNING] Error guardando en base de datos: {db_err}")

        return {"predicted_price": prediction}

    except Exception as e:
        PREDICTION_ERRORS.inc()
        return {"error": str(e)}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

