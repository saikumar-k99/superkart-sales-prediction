
"""SuperKart - Streamlit front end of the sales prediction API."""

import io
import os

import pandas as pd
import requests
import streamlit as st

# Base URL of the Flask backend.
# Inside Docker, the backend container is reached by its container name ("backend") over the Docker network.
# For a local run, point the app to the local API, e.g.:  BACKEND_URL=http://127.0.0.1:7860 streamlit run app.py
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:7860").rstrip("/")

st.set_page_config(page_title="SuperKart Sales Forecast", page_icon="🛒", layout="wide")

# The allowed values are the categories the model was trained on
SUGAR_OPTIONS = ["Low Sugar", "Regular", "No Sugar"]
STORE_SIZE_OPTIONS = ["Small", "Medium", "High"]
CITY_TYPE_OPTIONS = ["Tier 1", "Tier 2", "Tier 3"]
STORE_TYPE_OPTIONS = ["Supermarket Type1", "Supermarket Type2", "Departmental Store", "Food Mart"]
PRODUCT_ID_OPTIONS = {"FD": "FD - Food", "DR": "DR - Drinks", "NC": "NC - Non-consumable"}
CATEGORY_OPTIONS = ["Perishables", "Non Perishables"]

# Example record used for the CSV template (first row of the training data)
EXAMPLE_RECORD = {
    "Product_Weight": 12.66,
    "Product_Sugar_Content": "Low Sugar",
    "Product_Allocated_Area": 0.027,
    "Product_MRP": 117.08,
    "Store_Size": "Medium",
    "Store_Location_City_Type": "Tier 2",
    "Store_Type": "Supermarket Type2",
    "Product_Id_char": "FD",
    "Store_Age_Years": 16,
    "Product_Type_Category": "Non Perishables",
}


def backend_is_up():
    """True when the Flask API answers its health check."""
    try:
        return requests.get(f"{BACKEND_URL}/health", timeout=3).ok
    except requests.exceptions.RequestException:
        return False


def error_message(response):
    """Readable error text of a failed API call."""
    try:
        return response.json().get("error", response.text)
    except ValueError:
        return response.text


def predict_single(payload):
    """Send one record to the API. Returns (predicted sales, error message)."""
    try:
        response = requests.post(f"{BACKEND_URL}/v1/predict", json=payload, timeout=30)
    except requests.exceptions.RequestException:
        return None, f"Unable to connect to the prediction API at {BACKEND_URL}."
    if response.status_code != 200:
        return None, error_message(response)
    return response.json()["Sales"], None


def predict_batch(csv_bytes, filename):
    """Send a CSV file to the API. Returns ({row index: predicted sales}, error message)."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/v1/predictbatch",
            files={"file": (filename, csv_bytes, "text/csv")},
            timeout=120,
        )
    except requests.exceptions.RequestException:
        return None, f"Unable to connect to the prediction API at {BACKEND_URL}."
    if response.status_code != 200:
        return None, error_message(response)
    return response.json(), None


# ------------------------------------------------------------------ page
st.title("🛒 SuperKart - Sales Forecast")
st.write(
    "Predict the total sales (revenue) of a product in a store - for one product at a time "
    "or for a whole CSV file of products."
)

with st.sidebar:
    st.header("Prediction API")
    st.caption(BACKEND_URL)
    if backend_is_up():
        st.success("Connected")
    else:
        st.error("Not reachable")
    st.markdown(
        "The model was trained on the 4 SuperKart stores. "
        "It forecasts the **sales of a product in a store**; add up the predictions of all the products "
        "of a store to forecast the revenue of the outlet."
    )

tab_single, tab_batch = st.tabs(["Single prediction", "Batch prediction"])

# ------------------------------------------------------------------ single prediction
with tab_single:
    st.write("Enter the product and store details below to predict the total sales.")

    with st.form("single_prediction_form"):
        left, right = st.columns(2)

        with left:
            st.subheader("Product")
            Product_Weight = st.number_input("Product Weight", min_value=0.0, max_value=100.0, value=12.66, step=0.1, format="%.2f")
            Product_Sugar_Content = st.selectbox("Product Sugar Content", SUGAR_OPTIONS)
            Product_Allocated_Area = st.number_input(
                "Product Allocated Area (share of the display area)", min_value=0.0, max_value=1.0, value=0.027, step=0.001, format="%.3f"
            )
            Product_MRP = st.number_input("Product MRP", min_value=0.0, max_value=1000.0, value=117.08, step=1.0, format="%.2f")
            Product_Id_char = st.selectbox("Product ID Character", list(PRODUCT_ID_OPTIONS), format_func=PRODUCT_ID_OPTIONS.get)
            Product_Type_Category = st.selectbox("Product Type Category", CATEGORY_OPTIONS, index=1)

        with right:
            st.subheader("Store")
            Store_Size = st.selectbox("Store Size", STORE_SIZE_OPTIONS, index=1)
            Store_Location_City_Type = st.selectbox("Store Location City Type", CITY_TYPE_OPTIONS, index=1)
            Store_Type = st.selectbox("Store Type", STORE_TYPE_OPTIONS, index=1)
            Store_Age_Years = st.number_input("Store Age (Years)", min_value=0, max_value=100, value=16, step=1)

        submitted = st.form_submit_button("Predict", type="primary")

    if submitted:
        # Create JSON payload
        product_data = {
            "Product_Weight": Product_Weight,
            "Product_Sugar_Content": Product_Sugar_Content,
            "Product_Allocated_Area": Product_Allocated_Area,
            "Product_MRP": Product_MRP,
            "Store_Size": Store_Size,
            "Store_Location_City_Type": Store_Location_City_Type,
            "Store_Type": Store_Type,
            "Product_Id_char": Product_Id_char,
            "Store_Age_Years": int(Store_Age_Years),
            "Product_Type_Category": Product_Type_Category,
        }
        predicted_sales, error = predict_single(product_data)
        st.session_state["single_result"] = {"payload": product_data, "sales": predicted_sales, "error": error}

    result = st.session_state.get("single_result")
    if result:
        if result["error"]:
            st.error(result["error"])
        else:
            st.success("Prediction completed successfully!")
            st.metric("Predicted Product Store Sales Total", f"₹{result['sales']:,.2f}")
            with st.expander("Request sent to the API"):
                st.json(result["payload"])

# ------------------------------------------------------------------ batch prediction
with tab_batch:
    st.write(
        "Upload a CSV file with one row per product. It must contain these columns: "
        + ", ".join(f"`{col}`" for col in EXAMPLE_RECORD)
        + "."
    )
    st.download_button(
        "Download a CSV template",
        pd.DataFrame([EXAMPLE_RECORD]).to_csv(index=False),
        file_name="superkart_batch_template.csv",
        mime="text/csv",
    )

    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

    if uploaded_file is None:
        st.session_state.pop("batch_result", None)
    else:
        csv_bytes = uploaded_file.getvalue()
        file_key = (uploaded_file.name, len(csv_bytes))

        # forget the previous result as soon as another file is uploaded
        if st.session_state.get("batch_result", {}).get("key") != file_key:
            st.session_state.pop("batch_result", None)

        try:
            batch_df = pd.read_csv(io.BytesIO(csv_bytes))
        except Exception as exc:
            st.error(f"The file could not be read as a CSV: {exc}")
        else:
            st.write(f"Preview of the uploaded file ({len(batch_df)} rows)")
            st.dataframe(batch_df.head(10))

            if st.button("Predict for Batch", type="primary"):
                results, error = predict_batch(csv_bytes, uploaded_file.name)
                if error:
                    st.session_state.pop("batch_result", None)
                    st.error(error)
                else:
                    predictions = pd.Series({int(k): v for k, v in results.items()}).sort_index()
                    output = batch_df.copy()
                    output["Predicted_Sales"] = predictions.reindex(range(len(output))).values
                    st.session_state["batch_result"] = {"key": file_key, "table": output}

    batch_result = st.session_state.get("batch_result")
    if batch_result:
        table = batch_result["table"]
        st.success("Predictions completed successfully!")

        col1, col2, col3 = st.columns(3)
        col1.metric("Products", f"{len(table):,}")
        col2.metric("Total predicted sales", f"₹{table['Predicted_Sales'].sum():,.2f}")
        col3.metric("Average per product", f"₹{table['Predicted_Sales'].mean():,.2f}")

        st.dataframe(table)
        st.download_button(
            "Download the predictions (CSV)",
            table.to_csv(index=False).encode("utf-8"),
            file_name="superkart_predictions.csv",
            mime="text/csv",
        )
