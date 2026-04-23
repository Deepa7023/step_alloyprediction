import os
import uuid
import logging

from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

from .logic.cad_analyzer import SUPPORTED_CAD_EXTENSIONS, analyze_cad
from .logic.cost_engine import METAL_PROPERTIES, calculate_hpdc_cost
from .logic.step_engine_ocp import METAL_KEYWORDS


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
INR_RATE = 83.5

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 60 * 1024 * 1024


def _allowed_file(filename):
    return os.path.splitext(filename or "")[1].lower() in SUPPORTED_CAD_EXTENSIONS


def _float_form(name, default):
    try:
        return float(request.form.get(name, default))
    except (TypeError, ValueError):
        return default


def _int_form(name, default):
    try:
        return int(request.form.get(name, default))
    except (TypeError, ValueError):
        return default


def _detect_alloy_hint(file_path, filename, analyzer_detected):
    if analyzer_detected in METAL_PROPERTIES:
        return analyzer_detected, "CAD metadata"

    text = filename.upper()
    try:
        with open(file_path, "r", errors="ignore") as handle:
            text = f"{text}\n{handle.read(16384).upper()}"
    except Exception:
        pass

    for keyword, alloy in METAL_KEYWORDS.items():
        if alloy in METAL_PROPERTIES and keyword in text:
            return alloy, "File metadata"

    return "Aluminum_A380", "Default fallback"


def _cad_error_response(message, status=422):
    lower = str(message).lower()
    if "step_lightweight_parse_failure" in lower:
        hint = "This STEP file does not expose enough coordinate geometry for the lightweight Render parser. Export it as binary STL or OBJ and upload again."
    elif "geometry_parse_failure" in lower or "could not be analyzed" in lower:
        hint = "This CAD file could not be parsed on the server. Try exporting the model as binary STL, OBJ, or a clean AP214/AP242 STEP file."
    elif "unsupported" in lower:
        hint = "Use STEP, STP, IGES, IGS, STL, OBJ, PLY, GLB, GLTF, 3MF, OFF, or DAE."
    else:
        hint = "Please try a smaller or simplified CAD file. For Render free tier, STL/OBJ files are the most reliable."

    return jsonify({
        "error": "CAD file could not be processed.",
        "detail": str(message),
        "hint": hint,
    }), status


@app.get("/")
def index():
    return render_template(
        "index.html",
        default_metal="Aluminum_A380",
        supported=", ".join(SUPPORTED_CAD_EXTENSIONS),
    )


@app.get("/api/health")
def health():
    return jsonify({"status": "healthy", "app": "simple-flask-hpdc", "version": "auto-alloy"})


@app.post("/api/analyze")
def analyze():
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "Upload a CAD file first."}), 400

    if not _allowed_file(file.filename):
        return jsonify({"error": "Unsupported CAD format."}), 400

    filename = secure_filename(file.filename)
    saved_name = f"{uuid.uuid4().hex}_{filename}"
    file_path = os.path.join(UPLOAD_FOLDER, saved_name)
    file.save(file_path)

    result = analyze_cad(file_path)
    if "error" in result:
        logger.warning("CAD analysis failed for %s: %s", file.filename, result["error"])
        return _cad_error_response(result["error"])

    traits = result["traits"]
    detected_metal = result.get("detected_metal")
    metal, alloy_source = _detect_alloy_hint(file_path, file.filename, detected_metal)
    annual_volume = _int_form("annual_volume", 10000)
    sliders = _int_form("sliders", 0)
    port_cost_inr = _float_form("port_cost_inr", 0)
    port_cost_usd = port_cost_inr / INR_RATE

    cost = calculate_hpdc_cost(
        traits=traits,
        metal=metal,
        annual_volume=annual_volume,
        sliders=sliders,
        location_multiplier=1.0,
        port_cost=port_cost_usd,
    )

    breakdown_inr = cost.get("inr_breakdown") or {
        "Material": round(cost["material_cost"] * INR_RATE, 2),
        "Machine conversion": round(cost["machine_cost"] * INR_RATE, 2),
        "Tooling amortization": round(cost["amortization"] * INR_RATE, 2),
        "Port / handling": round(cost["port_cost"] * INR_RATE, 2),
    }

    response = {
        "file": file.filename,
        "engine": result["engine"],
        "geometry": {
            "volume_mm3": round(traits.get("volume", 0), 2),
            "surface_area_mm2": round(traits.get("surface_area", 0), 2),
            "projected_area_mm2": round(traits.get("projected_area", 0), 2),
            "dimensions_mm": traits.get("dimensions", {}),
            "topology": traits.get("topology", {}),
            "validation": traits.get("validation", {}),
        },
        "cost": {
            "alloy": cost["alloy"],
            "alloy_source": alloy_source,
            "detected_alloy": metal if alloy_source != "Default fallback" else None,
            "annual_volume": cost["annual_volume"],
            "quote_basis": cost.get("quote_basis", "Reference model"),
            "weight_g": cost["weight_g"],
            "costing_weight_kg": cost.get("costing_weight_kg"),
            "gross_melt_kg": cost.get("gross_melt_kg"),
            "yield_factor": cost.get("yield_factor"),
            "tooling_estimate_inr": cost.get("tooling_estimate_inr", round(cost["tooling_estimate"] * INR_RATE, 2)),
            "tooling_rows_58_60": cost.get("tooling_rows_58_60", []),
            "quote_sheet_rows": cost.get("quote_sheet_rows", []),
            "spreadsheet_constants": cost.get("spreadsheet_constants", {}),
            "breakdown_inr": breakdown_inr,
            "per_part_cost_inr": round(cost["total_unit_cost"] * INR_RATE, 2),
            "range_inr": {
                "min": round(cost["fluctuation_range"]["min"] * INR_RATE, 2),
                "max": round(cost["fluctuation_range"]["max"] * INR_RATE, 2),
                "percent": cost["fluctuation_range"]["percent"],
            },
        },
    }
    return jsonify(response)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=False, use_reloader=False)
