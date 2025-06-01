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

# Inferir columnas esperadas del modelo cargado
try:
    model = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}/Production")
    dummy_input = pd.DataFrame([{k: 0.0 for k in range(5)}])
    model.predict(dummy_input)
except Exception as e:
    msg = str(e)
    import re
    found_cols = re.findall(r"Feature names seen at fit time, yet now missing:\n- (.+)", msg)
    if found_cols:
        expected_columns = found_cols[0].split("\n- ")
    else:
        expected_columns = ["group_number", "batch_number", "bed", "bath"]  # fallback por defecto
else:
    expected_columns = ["group_number", "batch_number", "bed", "bath"]

# Inputs para inferencia (solo los esperados)
st.sidebar.header("Parámetros de entrada")

input_data = {}
for col in expected_columns:
    if col in ["bed", "batch_number", "group_number"]:
        input_data[col] = st.sidebar.number_input(col, min_value=0, value=1, step=1)
    else:
        input_data[col] = st.sidebar.number_input(col, min_value=0.0, value=1.0, step=0.5)

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
    input_df = pd.DataFrame([input_data])
    explainer = shap.Explainer(model.predict, input_df)
    shap_values = explainer(input_df)

    st.set_option('deprecation.showPyplotGlobalUse', False)
    fig, ax = plt.subplots()
    shap.plots.waterfall(shap_values[0], max_display=10, show=False)
    st.pyplot(fig)

except Exception as e:
    st.info(f"No se pudo generar la explicación SHAP: {e}")

