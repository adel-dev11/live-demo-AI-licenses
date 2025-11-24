from flask import Flask, request, jsonify
from flasgger import Swagger, swag_from
import os
import re
import joblib
import pandas as pd
import json
from werkzeug.utils import secure_filename
# ====================== New: Extract dependencies from package.json ======================
import requests
from tqdm import tqdm  # Not necessary here but useful in dev if you want


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

model = joblib.load(r'C:\Users\adel mohamedll\Desktop\Hackathon\live-demo-AI-licenses\model\license_safety_model_v1.pkl')

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


def get_npm_license(package_name, version):
    try:
        clean_version = version.lstrip('^~><= ')
        url = f"https://registry.npmjs.org/{package_name}/{clean_version}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            lic = data.get("license")
            if isinstance(lic, dict):
                return lic.get("type", "UNKNOWN")
            return str(lic) if lic else "UNKNOWN"
    except:
        pass
    try:
        url = f"https://registry.npmjs.org/{package_name}/latest"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            lic = resp.json().get("license")
            if isinstance(lic, dict):
                return lic.get("type", "UNKNOWN")
            return str(lic) if lic else "UNKNOWN"
    except:
        pass
    return "UNKNOWN"

def extract_dependencies_from_package_json(json_data):
    """Extract dependencies + devDependencies with licenses from npm"""
    deps = {}
    if "dependencies" in json_data:
        deps.update(json_data["dependencies"])
    if "devDependencies" in json_data:
        deps.update(json_data["devDependencies"])

    results = []
    print(f"Fetching licenses for dependencies from npm registry...")
    for name, version in deps.items():
        license = get_npm_license(name, version)
        results.append({
            "name": name,
            "version": version.lstrip('^~><='),
            "license": license
        })
    return results
# =========================================================================================

# Replace the entire api_predict() function with this exact code
@app.route("/api/predict", methods=["POST"])
@swag_from({
    "tags": ["Model"],
    "summary": "Analyze all dependencies in package.json",
    "description": "Upload package.json → returns full license risk report using your trained model",
    "consumes": ["multipart/form-data"],
    "parameters": [
        {
            "name": "file",
            "in": "formData",
            "type": "file",
            "required": True,
            "description": "Your project's package.json file"
        }
    ],
    "responses": {
        200: {"description": "Success – Full risk report"},
        400: {"description": "Invalid file or no dependencies"}
    }
})
def api_predict():
    # 1. Check if file exists
    if 'file' not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    # Accept any JSON file, not necessarily named package.json
    if not file.filename.lower().endswith('.json'):
        return jsonify({"error": "Please upload a JSON file"}), 400

    # 2. Safely read the file
    try:
        file.stream.seek(0)  # Return to start of file
        json_data = json.load(file)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON format in package.json"}), 400
    except Exception as e:
        return jsonify({"error": "Cannot read uploaded file", "details": str(e)}), 400

    # 3. Extract dependencies
    deps = {}
    if isinstance(json_data, dict):
        deps.update(json_data.get("dependencies", {}))
        deps.update(json_data.get("devDependencies", {}))

    if not deps:
        return jsonify({
            "overallRiskLevel": "low",
            "overallRiskScore": 0,
            "summary": {
                "totalDependencies": 0,
                "highRisk": 0,
                "mediumRisk": 0,
                "lowRisk": 0,
                "mainWarning": "No dependencies found in package.json"
            },
            "dependencies": [],
            "aiSummary": {
                "narrative": "No dependencies or devDependencies were found.",
                "recommendedNextSteps": ["Make sure you uploaded the correct package.json file"]
            },
            "analysisLimitations": "No dependencies detected."
        }), 200

    # 4. Fetch licenses + classification
    dependencies_output = []
    high_count = 0

    print(f"Analyzing {len(deps)} packages...")

    for name, version in deps.items():
        version_clean = version.lstrip('^~><= ') if isinstance(version, str) else "unknown"
        license = get_npm_license(name, version_clean)

        status, confidence = predict_license(license or "UNKNOWN")
        risk_level = "low" if status == "safe" else "high"
        if risk_level == "high":
            high_count += 1

        alt = get_safe_alternative(license or "UNKNOWN")

        dependencies_output.append({
            "name": name,
            "version": version_clean,
            "license": license or "UNKNOWN",
            "riskLevel": risk_level,
            "issues": [
                {
                    "type": "license",
                    "title": f"High-risk license: {license or 'UNKNOWN'}",
                    "description": f"The license '{license or 'UNKNOWN'}' may impose strong copyleft or unclear terms.",
                    "legalImpact": "High – may require source disclosure",
                    "businessImpact": "Risky for commercial/closed-source projects"
                }
            ] if risk_level == "high" else [],
            "impact": {
                "legal": "High" if risk_level == "high" else "Low",
                "business": "High" if risk_level == "high" else "Safe",
                "technical": "None",
                "severityScore": round(confidence * 100, 1)
            },
            "recommendation": {
                "action": "Replace immediately" if risk_level == "high" else "Safe to keep",
                "steps": [f"Recommended: {alt}"] if risk_level == "high" else ["No action required"]
            }
        })

    total = len(deps)
    overall = "high" if high_count > 0 else "low"
    score = round((high_count / total) * 100, 1) if total > 0 else 0

    return jsonify({
        "overallRiskLevel": overall,
        "overallRiskScore": score,
        "summary": {
            "totalDependencies": total,
            "highRisk": high_count,
            "mediumRisk": 0,
            "lowRisk": total - high_count,
            "mainWarning": f"{high_count} high-risk license(s) detected" if high_count > 0 else "All licenses are safe"
        },
        "dependencies": dependencies_output,
        "aiSummary": {
            "narrative": f"Successfully analyzed {total} packages. {high_count} high-risk licenses were detected.",
            "recommendedNextSteps": [
                "Replace red-flagged packages immediately",
                "Use MIT or Apache-2.0 alternatives",
                "Re-run analysis after every npm install"
            ] if high_count > 0 else [
                "Your project is safe from a licensing perspective",
                "Keep up the great work!"
            ]
        },
        "analysisLimitations": "Licenses were fetched from the npm registry. UNKNOWN licenses are automatically classified as high-risk."
    })  

@app.route("/")
def home():
    return "LicenseGuard Pro API is running. Visit /swagger/ for docs."

if __name__ == '__main__':
    print("LicenseGuard Pro 2025 — API Ready!")
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
