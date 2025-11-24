from flask import Flask, request, jsonify
from flasgger import Swagger, swag_from
import json

app = Flask(__name__)

# ============================
# Swagger Configuration
# ============================
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/apispec.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/swagger/"
}

swagger = Swagger(app, config=swagger_config)


# ============================
# Dummy Model Function
# ============================
def run_model(input_data):
    return {
        "status": "success",
        "length": len(str(input_data)),
        "model_output": f"Processed: {input_data}"
    }


# ============================
# /predict Endpoint (JSON File Only)
# ============================
@app.route("/predict", methods=["POST"])
@swag_from({
    "tags": ["Model"],
    "summary": "Upload JSON file",
    "consumes": ["multipart/form-data"],
    "parameters": [
        {
            "name": "file",
            "in": "formData",
            "type": "file",
            "required": True,
            "description": "Upload JSON file to process"
        }
    ],
    "responses": {
        200: {
            "description": "Success",
            "schema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "length": {"type": "integer"},
                    "model_output": {"type": "string"}
                }
            }
        },
        400: {"description": "Invalid JSON file or missing file"}
    }
})
def predict():
    if "file" not in request.files:
        return jsonify({"error": "file is missing"}), 400

    file = request.files["file"]
    try:
        json_data = json.load(file)
    except Exception as e:
        return jsonify({"error": "Invalid JSON file", "details": str(e)}), 400

    return jsonify(run_model(json_data))


# ============================
# /test Endpoint
# ============================
@app.route("/test", methods=["GET"])
@swag_from({
    "tags": ["Test"],
    "summary": "Test API",
    "description": "Simple test endpoint to verify API is running",
    "responses": {
        200: {
            "description": "API is working",
            "schema": {"type": "string"}
        }
    }
})
def test_api():
    return "lol ya Adel"


# ============================
# Home Endpoint
# ============================
@app.route("/", methods=["GET"])
def home():
    return "API is running. Go to /swagger/ for documentation."


# ============================
# Run App
# ============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
