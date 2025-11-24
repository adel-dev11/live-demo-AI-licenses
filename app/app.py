from flask import Flask, request, jsonify
from flasgger import Swagger, swag_from
import os
import re
import joblib
import pandas as pd
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'super_secret_key_2025'

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

Swagger(app, config=swagger_config)

app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

model = joblib.load('model/license_safety_model_v1.pkl')

SAFE_ALTERNATIVES = {
    "GPL-3.0": "Use MIT or Apache-2.0 (More flexible, no Copyleft)",
    "GPL-2.0": "Use MIT or Apache-2.0",
    "GPL": "Use MIT or Apache-2.0",
    "AGPL-3.0": "MIT or Apache-2.0 (AGPL forces source disclosure over network)",
    "AGPL": "MIT or Apache-2.0",
    "LGPL-3.0": "Use MIT (less restrictions)",
    "LGPL": "Use MIT",
    "MPL-2.0": "Apache-2.0 or MIT (easier to integrate)",
    "CC-BY-SA-4.0": "MIT (not suitable for source code)",
    "CC0-1.0": "Very safe",
    "EPL": "Apache-2.0 or MIT",
    "CDDL": "Apache-2.0",
}

def get_safe_alternative(license_name):
    license_upper = license_name.upper()
    for dangerous, alternative in SAFE_ALTERNATIVES.items():
        if dangerous in license_upper:
            return alternative
    return "MIT or Apache-2.0 (most commercially safe)"

def predict_license(license_id):
    if not license_id or license_id.strip() == "":
        return "unknown", 0.0

    sample = pd.DataFrame([{
        'name_length': len(license_id),
        'has_gpl': 1 if 'GPL' in license_id.upper() else 0,
        'has_lgpl': 1 if 'LGPL' in license_id.upper() else 0,
        'has_mpl': 1 if 'MPL' in license_id.upper() else 0,
        'has_apache': 1 if 'APACHE' in license_id.upper() else 0,
        'has_bsd': 1 if 'BSD' in license_id.upper() else 0,
        'has_mit': 1 if 'MIT' in license_id.upper() else 0,
        'is_osi': 1,
        'is_deprecated': 0
    }])

    try:
        pred = model.predict(sample)[0]
        prob = model.predict_proba(sample)[0].max()
        return ("safe" if pred == 1 else "dangerous"), prob

    except:
        if any(x in license_id.upper() for x in ['GPL', 'AGPL', 'CC-BY-SA', 'EPL', 'CDDL']):
            return "dangerous", 0.85
        return "safe", 0.95

def extract_all_licenses(filepath):
    filename = os.path.basename(filepath).lower()

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    licenses = set()
    source = "uploaded file"

    if any(kw in content.lower() for kw in ['"workspaces"', 'turbo', 'lerna', 'pnpm', '"packages"']):
        licenses.add("MIT")
        source = "Monorepo structure → assumed MIT"

    elif filename == "package-lock.json":
        try:
            data = json.loads(content)
            if "packages" in data:
                for pkg in data["packages"].values():
                    if "license" in pkg:
                        licenses.add(pkg["license"])
                    if "licenses" in pkg:
                        for l in pkg.get("licenses", []):
                            if isinstance(l, dict) and "type" in l:
                                licenses.add(l["type"])
                            else:
                                licenses.add(str(l))
            source = "package-lock.json"
        except:
            pass

    elif filename.endswith("package.json"):
        try:
            data = json.loads(content)
            # Single license
            if "license" in data:
                lic = data["license"]
                if isinstance(lic, str):
                    licenses.add(lic)
                elif isinstance(lic, dict) and "type" in lic:
                    licenses.add(lic["type"])
            # Multiple licenses
            if "licenses" in data and isinstance(data["licenses"], list):
                for lic in data["licenses"]:
                    licenses.add(lic)
            if not licenses:
                licenses.add("MIT")
                source = "default license → MIT"
        except:
            pass

    if not licenses:
        matches = re.findall(r'"license"\s*:\s*"([^"]+)"', content)
        matches += re.findall(r'"type"\s*:\s*"([^"]+)"', content)
        matches += re.findall(r'SPDX-License-Identifier:\s*([A-Za-z0-9\.\-\+]+)', content)
        licenses.update([m.strip() for m in matches])

    return list(licenses), source

@app.route("/api/predict", methods=["POST"])
@swag_from({
    "tags": ["Model"],
    "summary": "Analyze project license risk",
    "description": "Accepts JSON file and returns license risk level",
    "consumes": ["multipart/form-data", "application/json"],
    "parameters": [
        {
            "name": "file",
            "in": "formData",
            "type": "file",
            "required": False,
            "description": "JSON file to analyze"
        }
    ],
    "responses": {
        200: {"description": "Analysis result"},
        400: {"description": "Invalid input"}
    }
})
def api_predict():

    if "file" not in request.files or request.files["file"].filename == "":
        return jsonify({"error": "JSON file is required"}), 400

    file = request.files["file"]
    try:
        json_data = json.load(file)
    except Exception as e:
        return jsonify({"error": "Invalid JSON file", "details": str(e)}), 400

    try:
        content_str = json.dumps(json_data)
        tmp_path = "uploads/tmp_input.json"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content_str)

        licenses, source = extract_all_licenses(tmp_path)

    except Exception as e:
        return jsonify({"error": "JSON analysis failed", "details": str(e)}), 400

    dependencies_output = []
    risk_scores = {"low": 0, "medium": 0, "high": 0}

    for lic in licenses:
        status, conf = predict_license(lic)
        alt = get_safe_alternative(lic)

        risk_level = "low" if status == "safe" else "high"
        risk_scores[risk_level] += 1

        dependencies_output.append({
            "name": lic,
            "version": "unknown",
            "license": lic,
            "riskLevel": risk_level,
            "issues": [
                {
                    "type": "license",
                    "title": f"Issue detected in {lic}",
                    "description": "License may affect project usage",
                    "legalImpact": "May impose distribution restrictions" if risk_level == "high" else "None",
                    "businessImpact": "Could affect commercial usage" if risk_level == "high" else "Minimal"
                }
            ],
            "impact": {
                "legal": "High legal risk" if risk_level == "high" else "Low legal impact",
                "business": "Could restrict usage" if risk_level == "high" else "Safe for business",
                "technical": "No technical issues",
                "severityScore": round(conf * 100, 2)
            },
            "recommendation": {
                "action": "Replace" if risk_level == "high" else "Keep",
                "steps": [
                    f"Consider using: {alt}"
                ] if risk_level == "high" else ["No action required"]
            }
        })

    total = len(licenses)
    overall = "high" if risk_scores["high"] > 0 else "medium" if risk_scores["medium"] > 0 else "low"

    response_body = {
        "overallRiskLevel": overall,
        "overallRiskScore": risk_scores["high"] * 60 + risk_scores["medium"] * 30,

        "summary": {
            "totalDependencies": total,
            "highRisk": risk_scores["high"],
            "mediumRisk": risk_scores["medium"],
            "lowRisk": risk_scores["low"],
            "mainWarning": "Some licenses may cause legal issues" if risk_scores["high"] > 0 else "No major legal concerns detected"
        },

        "dependencies": dependencies_output,

        "aiSummary": {
            "narrative": "License analysis completed. Each dependency was evaluated for legal risk.",
            "recommendedNextSteps": [
                "Replace high-risk licenses if possible",
                "Update project documentation",
                "Review legal requirements for commercial distribution"
            ]
        },

        "analysisLimitations": "This analysis is automated and does not replace professional legal review."
    }

    return jsonify(response_body)

@app.route("/")
def home():
    return "LicenseGuard Pro API is running. Visit /swagger/ for docs."

if __name__ == '__main__':
    print("LicenseGuard Pro 2025 — API Ready!")
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
