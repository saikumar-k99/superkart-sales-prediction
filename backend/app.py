
"""
SuperKart sales prediction API (Flask)

GET  /                  welcome message
GET  /health            health check
POST /v1/predict        one product-store record as JSON       -> {"Sales": <float>}
POST /v1/predictbatch   CSV file in the form field "file"      -> {"0": <float>, "1": <float>, ...}
"""

# Import necessary libraries
import os

import joblib  # For loading the serialized model
import pandas as pd  # For data manipulation
from flask import Flask, request, jsonify  # For creating the Flask API

# Initialize Flask app with a name
superkart_api = Flask("SuperKart")
superkart_api.json.sort_keys = False  # keep the batch predictions in the order of the rows
superkart_api.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # reject uploads larger than 5 MB

# Load the trained model (preprocessing + regressor in one pipeline), whatever the working directory is
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "superkart_model.joblib")
model = joblib.load(MODEL_PATH)

# The features the model expects
NUMERICAL_FEATURES = [
    "Product_Weight",
    "Product_Allocated_Area",
    "Product_MRP",
    "Store_Age_Years",
]
FEATURES = [
    "Product_Weight",
    "Product_Sugar_Content",
    "Product_Allocated_Area",
    "Product_MRP",
    "Store_Size",
    "Store_Location_City_Type",
    "Store_Type",
    "Product_Id_char",
    "Store_Age_Years",
    "Product_Type_Category",
]


def prepare_features(raw):
    """Validate the raw input (a DataFrame) and return the model features in the right order and types."""
    missing = [col for col in FEATURES if col not in raw.columns]
    if missing:
        raise ValueError("Missing required field(s): " + ", ".join(missing))

    features = raw[FEATURES].copy()
    for col in NUMERICAL_FEATURES:
        features[col] = pd.to_numeric(features[col], errors="coerce")

    invalid = features.columns[features.isnull().any()].tolist()
    if invalid:
        raise ValueError("Empty or non-numeric value(s) in: " + ", ".join(invalid))
    if (features[NUMERICAL_FEATURES] < 0).any().any():
        raise ValueError("The numerical fields cannot be negative.")

    for col in FEATURES:
        if col not in NUMERICAL_FEATURES:
            features[col] = features[col].astype(str).str.strip()
    return features


# Define a route for the home page
@superkart_api.get("/")
def home():
    return "Welcome to the SuperKart System"


# Define a health-check route (used by the Streamlit UI and by monitoring tools)
@superkart_api.get("/health")
def health():
    return jsonify({"status": "ok"})


# Define an endpoint to predict sales for a single product
@superkart_api.post("/v1/predict")
def predict_sales():
    # Get JSON data from the request
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Send the product and store details as a JSON object."}), 400

    # Extract the relevant features from the input data and convert them into a DataFrame
    try:
        input_data = prepare_features(pd.DataFrame([data]))
    except (ValueError, TypeError) as err:
        return jsonify({"error": str(err)}), 400

    # Make a prediction using the trained model
    prediction = float(model.predict(input_data)[0])

    # Return the prediction as a JSON response
    return jsonify({"Sales": round(prediction, 2)})


# Define an endpoint to predict sales for a batch of products
@superkart_api.post("/v1/predictbatch")
def predict_sales_batch():
    # Get the uploaded CSV file from the request
    file = request.files.get("file")
    if file is None or file.filename == "":
        return jsonify({"error": 'Upload a CSV file in the form field named "file".'}), 400

    # Read the file into a DataFrame and validate it
    try:
        raw_data = pd.read_csv(file)
        if raw_data.empty:
            raise ValueError("The uploaded CSV file has no rows.")
        input_data = prepare_features(raw_data)
    except (ValueError, TypeError) as err:
        return jsonify({"error": str(err)}), 400

    # Make predictions for the batch data
    predictions = model.predict(input_data).tolist()

    # Create an output dictionary mapping row index to predicted sales
    output_dict = {str(i): round(pred, 2) for i, pred in enumerate(predictions)}

    return jsonify(output_dict)


# Run the Flask app (local development server only - inside the Docker container the app is served by Gunicorn)
if __name__ == "__main__":
    superkart_api.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "7860")),
        debug=False,
    )
