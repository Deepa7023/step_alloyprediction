import os
import io
import uuid
import time
import base64
import logging
import trimesh

from .step_engine_ocp import PreciseSTEPAnalyzer, detect_metal_from_step

logger = logging.getLogger(__name__)

SUPPORTED_CAD_EXTENSIONS = [
    ".step", ".stp", ".iges", ".igs",
    ".stl", ".obj", ".ply", ".glb",
    ".gltf", ".3mf", ".off", ".dae"
]


# ------------------------------------------------------
# Mesh is for PREVIEW ONLY
# ------------------------------------------------------
def _load_mesh_preview(file_path):
    try:
        mesh = trimesh.load(file_path)
        if isinstance(mesh, trimesh.Scene):
            parts = [g for g in mesh.geometry.values() if isinstance(g, trimesh.Trimesh)]
            if parts:
                return trimesh.util.concatenate(parts)
        elif isinstance(mesh, trimesh.Trimesh):
            return mesh
    except Exception:
        pass
    return None


# ======================================================
# MAIN CAD ANALYSIS (COST‑SAFE)
# ======================================================
def analyze_cad(file_path):
    """
    Cost‑safe CAD analysis:
    • OCP (analytic geometry) → REQUIRED for costing
    • Mesh → preview only
    """

    analysis_id = str(uuid.uuid4())
    ext = os.path.splitext(file_path)[1].lower()

    if ext not in SUPPORTED_CAD_EXTENSIONS:
        return {"error": f"Unsupported CAD format: {ext}"}

    detected_metal = None
    if ext in [".step", ".stp"]:
        detected_metal = detect_metal_from_step(file_path)

    # --------------------------------------------------
    # STEP 1: OCP PRECISE GEOMETRY (MANDATORY)
    # --------------------------------------------------
    precise = PreciseSTEPAnalyzer()
    precise_data = precise.analyze(file_path)

    if precise_data.get("status") != "success":
        return {
            "error": "GEOMETRY_NOT_COST_SAFE",
            "reason": precise_data.get("reason", "OCP analysis failed"),
            "message": "CAD kernel geometry required for HPDC costing."
        }

    # --------------------------------------------------
    # STEP 2: GEOMETRY FROM OCP (SOURCE OF TRUTH)
    # --------------------------------------------------
    volume_cm3 = precise_data["precise_volume_cm3"]
    surface_cm2 = precise_data["precise_surface_cm2"]
    projected_mm2 = precise_data["projected_area_mm2"]
    dims = precise_data["dimensions"]

    # Unit normalization
    volume_mm3 = volume_cm3 * 1000.0
    surface_mm2 = surface_cm2 * 100.0

    dimensions = {
        "x": float(dims["x"]),
        "y": float(dims["y"]),
        "z": float(dims["z"]),
    }

    # --------------------------------------------------
    # STEP 3: PREVIEW MESH (UI ONLY)
    # --------------------------------------------------
    preview_b64 = ""
    mesh = _load_mesh_preview(file_path)
    if mesh is not None:
        buf = io.BytesIO()
        mesh.export(buf, file_type="stl")
        preview_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    # --------------------------------------------------
    # STEP 4: TRAITS (COST‑SAFE CONTRACT)
    # --------------------------------------------------
    traits = {
        "volume": volume_mm3,                       # mm³ ✅
        "surface_area": surface_mm2,               # mm² ✅ OCP
        "projected_area": projected_mm2,            # mm² ✅ OCP
        "dimensions": dimensions,                   # mm ✅
        "preview_mesh": (
            f"data:model/stl;base64,{preview_b64}" if preview_b64 else ""
        ),
        "geometry_source": {
            "volume": "OCP",
            "surface_area": "OCP",
            "projected_area": "OCP",
            "dimensions": "OCP"
        }
    }

    logger.info(
        f"OCP_GEOMETRY_OK | Vol={round(volume_mm3,1)}mm³ | "
        f"Surf={round(surface_mm2,1)}mm² | Proj={round(projected_mm2,1)}mm²"
    )

    return {
        "analysis_id": analysis_id,
        "traits": traits,
        "engine": "OCP_CAD_KERNEL",
        "detected_metal": detected_metal,
        "metadata": {
            "timestamp": time.time(),
            "cost_safe": True
        }
    }
