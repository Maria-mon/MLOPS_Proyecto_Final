from fastapi import FastAPI
from pydantic import BaseModel
import mlflow.pyfunc
import pandas as pd
import os
from sqlalchemy import create_engine
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

# Configuración
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI")
MODEL_NAME = "BestHousePriceModel"
POSTGRES_URI = os.getenv("AIRFLOW_CONN_POSTGRES_DEFAULT")  # Reutiliza variable ya existente

# Inicializar API
app = FastAPI(title="House Price Prediction API")

# Métricas Prometheus
PREDICTION_COUNT = Counter("inference_requests_total", "Número total de solicitudes de inferencia")
PREDICTION_ERRORS = Counter("inference_errors_total", "Errores durante la inferencia")

# Conectar con MLflow y cargar modelo en producción
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
model = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}/Production")

# Esquema de entrada
class InputData(BaseModel):
    bed: int
    bath: float
    house_size: float
    acre_lot: float

# Endpoint de predicción
@app.post("/predict")
def predict(data: InputData):
    try:
        df = pd.DataFrame([data.dict()])
        prediction = model.predict(df)[0]
        PREDICTION_COUNT.inc()

        # Guardar predicción en base de datos
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

# Endpoint para Prometheus
@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

