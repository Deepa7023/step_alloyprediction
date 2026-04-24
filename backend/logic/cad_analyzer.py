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


# --------------------------------------------------
# Mesh preview ONLY (never used for geometry/cost)
# --------------------------------------------------
def _load_mesh_preview(file_path):
    try:
        mesh = trimesh.load(file_path)
        if isinstance(mesh, trimesh.Scene):
            parts = [
                g for g in mesh.geometry.values()
                if isinstance(g, trimesh.Trimesh)
            ]
            if parts:
                return trimesh.util.concatenate(parts)
        elif isinstance(mesh, trimesh.Trimesh):
            return mesh
    except Exception:
        pass
    return None


# ==================================================
# CAD-KERNEL-ALIGNED GEOMETRY ANALYSIS
# ==================================================
def analyze_cad(file_path):
    """
    Geometry extraction aligned with CAD viewers:
    • DX / DY / DZ from CAD kernel
    • Surface area in mm² (CAD kernel)
    • Projected area in mm² (CAD kernel)
    • Mesh strictly preview-only
    """

    analysis_id = str(uuid.uuid4())
    ext = os.path.splitext(file_path)[1].lower()

    if ext not in SUPPORTED_CAD_EXTENSIONS:
        return {"error": f"Unsupported CAD format: {ext}"}

    # -----------------------------
    # STEP metadata (optional)
    # -----------------------------
    detected_metal = None
    if ext in [".step", ".stp"]:
        detected_metal = detect_metal_from_step(file_path)

    # -----------------------------
    # CAD kernel analysis (MANDATORY)
    # -----------------------------
    analyzer = PreciseSTEPAnalyzer()
    precise = analyzer.analyze(file_path)

    if precise.get("status") != "success":
        return {
            "error": "GEOMETRY_NOT_COST_SAFE",
            "reason": precise.get("reason", "CAD-kernel analysis failed"),
            "message": "Exact CAD geometry required for HPDC costing."
        }

    # -----------------------------
    # CAD-kernel geometry (source of truth)
    # -----------------------------
    dims = precise["dimensions"]

    DX = round(float(dims["x"]), 2)
    DY = round(float(dims["y"]), 2)
    DZ = round(float(dims["z"]), 2)

    volume_mm3 = precise["precise_volume_cm3"] * 1000.0
    surface_mm2 = precise["precise_surface_cm2"] * 100.0
    projected_mm2 = float(precise["projected_area_mm2"])

    # -----------------------------
    # Mesh preview (UI only)
    # -----------------------------
    preview_b64 = ""
    mesh = _load_mesh_preview(file_path)
    if mesh is not None:
        buf = io.BytesIO()
        mesh.export(buf, file_type="stl")
        preview_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    # -----------------------------
    # FINAL TRAITS (COST SAFE)
    # -----------------------------
    traits = {
        # ✅ Explicit CAD-viewer dimensions
        "DX": DX,
        "DY": DY,
        "DZ": DZ,

        # ✅ Cost‑critical geometry (mm units only)
        "volume": round(volume_mm3, 2),            # mm³
        "surface_area": round(surface_mm2, 2),     # mm²
        "projected_area": round(projected_mm2, 2), # mm²

        # Preview only
        "preview_mesh": (
            f"data:model/stl;base64,{preview_b64}" if preview_b64 else ""
        ),

        # Geometry authority (agent trust)
        "geometry_source": {
            "DX": "OCP",
            "DY": "OCP",
            "DZ": "OCP",
            "volume": "OCP",
            "surface_area": "OCP",
            "projected_area": "OCP"
        }
    }

    logger.info(
        f"CAD_GEOMETRY_OK | DX={DX} DY={DY} DZ={DZ} | "
        f"Surface={surface_mm2:.2f} mm² | "
        f"Projected={projected_mm2:.2f} mm²"
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
``
