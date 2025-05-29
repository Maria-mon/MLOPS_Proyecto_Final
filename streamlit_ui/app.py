import streamlit as st
import pandas as pd
import mlflow
import mlflow.pyfunc
import requests
import os
import shap
import matplotlib.pyplot as plt
import numpy as np

# Configuración
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
API_INFERENCE_URL = os.getenv("INFERENCE_API_URL", "http://inference-api:8000/predict")
MODEL_NAME = "BestHousePriceModel"

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

st.set_page_config(page_title="Interfaz de Inferencia", layout="wide")
st.title("Predicción de Precios de Vivienda")
st.markdown("Esta interfaz permite realizar inferencias usando el modelo actual en producción y explorar el historial de modelos.")

# Inputs para inferencia
st.sidebar.header("Parámetros de entrada")
bed = st.sidebar.number_input("Habitaciones", min_value=0, value=3)
bath = st.sidebar.number_input("Baños", min_value=0.0, value=2.0, step=0.5)
house_size = st.sidebar.number_input("Tamaño de la casa (ft²)", min_value=0.0, value=1800.0)
acre_lot = st.sidebar.number_input("Tamaño del lote (acres)", min_value=0.0, value=0.2)

input_data = {
    "bed": bed,
    "bath": bath,
    "house_size": house_size,
    "acre_lot": acre_lot
}

# --- Inferencia vía API ---
if st.sidebar.button("Predecir"):
    try:
        response = requests.post(API_INFERENCE_URL, json=input_data)
        if response.status_code == 200:
            result = response.json()
            st.success(f"Precio predicho: ${result['predicted_price']:,.2f}")
        else:
            st.error(f"Error en la API: {response.text}")
    except Exception as e:
        st.error(f"Excepción durante inferencia: {e}")

st.divider()
st.subheader("Historial de modelos en MLflow")

try:
    client = mlflow.tracking.MlflowClient()
    runs = client.search_runs(experiment_ids=["0"], order_by=["metrics.rmse ASC"])

    if runs:
        df = pd.DataFrame([{
            "Run ID": run.info.run_id,
            "Modelo": run.data.tags.get("mlflow.runName", "N/A"),
            "RMSE": run.data.metrics.get("rmse", None),
            "R²": run.data.metrics.get("r2_score", None),
            "Estado": run.info.status,
            "Producción": "Sí" if MODEL_NAME in [m.name for m in client.get_registered_model(MODEL_NAME).latest_versions if m.current_stage == "Production"] and run.info.run_id in [m.run_id for m in client.get_registered_model(MODEL_NAME).latest_versions] else "No"
        } for run in runs])

        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay ejecuciones registradas en MLflow.")
except Exception as e:
    st.warning(f"No se pudo conectar a MLflow: {e}")

st.divider()
st.subheader("Explicabilidad del modelo con SHAP")

try:
    model = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}/Production")
    input_df = pd.DataFrame([input_data])
    explainer = shap.Explainer(model.predict, input_df)
    shap_values = explainer(input_df)

    st.set_option('deprecation.showPyplotGlobalUse', False)
    fig, ax = plt.subplots()
    shap.plots.waterfall(shap_values[0], max_display=10, show=False)
    st.pyplot(fig)

except Exception as e:
    st.info(f"No se pudo generar la explicación SHAP: {e}")

