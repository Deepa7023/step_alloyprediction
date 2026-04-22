import trimesh
import os
import numpy as np
import uuid
import time
import logging
import re

from .step_engine_ocp import METAL_KEYWORDS, PreciseSTEPAnalyzer, detect_metal_from_step

logger = logging.getLogger(__name__)

BREP_EXTENSIONS = [".step", ".stp", ".iges", ".igs"]
MESH_EXTENSIONS = [".stl", ".obj", ".ply", ".glb", ".gltf", ".3mf", ".off", ".dae"]
SUPPORTED_CAD_EXTENSIONS = BREP_EXTENSIONS + MESH_EXTENSIONS


def _load_mesh(file_path):
    mesh_raw = trimesh.load(file_path)
    if isinstance(mesh_raw, trimesh.Scene):
        parts = [g for g in mesh_raw.geometry.values() if isinstance(g, trimesh.Trimesh)]
        if parts:
            return trimesh.util.concatenate(parts)
    elif isinstance(mesh_raw, trimesh.Trimesh):
        return mesh_raw
    return None


def _analyze_step_lightweight(file_path):
    """
    Render-safe STEP fallback.

    It reads CARTESIAN_POINT coordinates from the STEP text and derives a
    bounding box. Volume/surface are estimated from that box because exact B-Rep
    mass properties require heavy CAD kernels that can crash small Render workers.
    """
    point_pattern = re.compile(
        r"CARTESIAN_POINT\s*\([^,]*,\s*\(\s*([-+0-9.Ee]+)\s*,\s*([-+0-9.Ee]+)\s*,\s*([-+0-9.Ee]+)\s*\)\s*\)",
        re.IGNORECASE,
    )
    points = []
    with open(file_path, "r", errors="ignore") as handle:
        for line in handle:
            match = point_pattern.search(line)
            if match:
                points.append(tuple(float(value) for value in match.groups()))

    if len(points) < 2:
        raise ValueError(
            "STEP_LIGHTWEIGHT_PARSE_FAILURE: No usable CARTESIAN_POINT geometry was found. "
            "Export this part as binary STL/OBJ, or upload a STEP file with explicit B-Rep coordinates."
        )

    arr = np.array(points, dtype=float)
    mins = arr.min(axis=0)
    maxs = arr.max(axis=0)
    extents = np.maximum(maxs - mins, 0.001)
    x, y, z = [round(float(value), 2) for value in extents]

    bbox_volume_mm3 = float(x * y * z)
    bbox_surface_mm2 = float(2 * ((x * y) + (y * z) + (x * z)))
    fill_factor = 0.35

    return {
        "volume": bbox_volume_mm3 * fill_factor,
        "surface_area": bbox_surface_mm2 * 0.75,
        "dimensions": {"x": x, "y": y, "z": z},
        "projected_area": float(max(x * y, y * z, x * z)),
        "topology": {
            "solids": 1,
            "faces": 0,
            "edges": 0,
            "vertices": len(points),
        },
        "validation": {
            "is_manifold": False,
            "integrity_score": 45,
            "note": "Render-safe STEP estimate from coordinate bounding box",
        },
    }


def _brep_enabled():
    return os.getenv("CAD_BREP_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def detect_metal_hint(file_path):
    text = os.path.basename(file_path).upper()
    try:
        with open(file_path, "r", errors="ignore") as handle:
            text = f"{text}\n{handle.read(16384).upper()}"
    except Exception:
        pass

    for keyword, metal_name in METAL_KEYWORDS.items():
        if keyword in text:
            return metal_name
    return None


def analyze_cad(file_path):
    """
    Analyzes a CAD file with dual-engine fallback:
      1. Trimesh for mesh formats (Render-safe default)
      2. Optional OCP/GMSH B-Rep analysis when CAD_BREP_ENABLED=true
    """
    analysis_id = str(uuid.uuid4())
    ext = os.path.splitext(file_path)[1].lower()
    mesh = None
    precise_data = {}
    detected_metal = None

    try:
        if ext not in SUPPORTED_CAD_EXTENSIONS:
            raise ValueError(
                f"UNSUPPORTED_CAD_FORMAT: {ext or 'unknown'} is not supported. "
                f"Supported formats: {', '.join(SUPPORTED_CAD_EXTENSIONS)}"
            )

        # ── Step 0: Metal Detection (Metadata) ──────────────────────────
        detected_metal = detect_metal_hint(file_path)
        if not detected_metal and ext in ['.step', '.stp']:
            detected_metal = detect_metal_from_step(file_path)
            if detected_metal:
                logger.info(f"METAL_DETECT: Auto-detected {detected_metal}")

        if ext in BREP_EXTENSIONS and not _brep_enabled():
            traits = _analyze_step_lightweight(file_path)
            return {
                "analysis_id": analysis_id,
                "traits": traits,
                "engine": "STEP_LIGHTWEIGHT_RENDER_SAFE",
                "detected_metal": detected_metal,
                "metadata": {"location": "PENDING_SYNC", "timestamp": time.time()},
            }

        # ── Step 1: Precise Analysis (STEP/IGES only) ────────────────────
        if ext in BREP_EXTENSIONS:
            analyzer = PreciseSTEPAnalyzer()
            precise_data = analyzer.analyze(file_path)

            if precise_data.get("status") == "success":
                logger.info(f"PRECISE_ENGINE: Analysis succeeded.")
            else:
                logger.warning(f"PRECISE_ENGINE: Failed ({precise_data.get('reason')})")

        # ── Step 2: Trimesh Load (for preview mesh) ──────────────────────
        try:
            mesh = _load_mesh(file_path)
        except Exception as e:
            logger.warning(f"Trimesh load failed: {e}")

        # ── Step 3: Failure handling ─────────────────────────────────────
        if mesh is None and precise_data.get("status") != "success":
            reason = precise_data.get("reason", "No engine could parse this file")
            raise ValueError(
                f"GEOMETRY_PARSE_FAILURE: File {ext} could not be analyzed. "
                f"Engine report: {reason}. Please ensure it is a valid 3D file."
            )

        # ── Step 4: Trait Synthesis ──────────────────────────────────────
        volume_cm3 = precise_data.get("precise_volume_cm3")
        surface_cm2 = precise_data.get("precise_surface_cm2")

        if volume_cm3 is None and mesh is not None:
            volume_cm3 = abs(mesh.volume) / 1000.0
        if surface_cm2 is None and mesh is not None:
            surface_cm2 = mesh.area / 100.0
        if volume_cm3 is None:
            volume_cm3 = 0.001
        if surface_cm2 is None:
            surface_cm2 = 0.01

        # Dimensions
        if "dimensions" in precise_data:
            dims = precise_data["dimensions"]
            dimensions = {"x": dims["x"], "y": dims["y"], "z": dims["z"]}
        elif mesh is not None:
            b = mesh.extents
            dimensions = {"x": round(float(b[0]), 2), "y": round(float(b[1]), 2), "z": round(float(b[2]), 2)}
        else:
            dimensions = {"x": 1.0, "y": 1.0, "z": 1.0}

        # Auto-Scale (meter → mm)
        scale_factor = 1.0
        if max(dimensions.values()) < 1.0 and max(dimensions.values()) > 0:
            logger.info(f"ANALYZER: Auto-scaling 1000x (meter→mm)")
            scale_factor = 1000.0
            dimensions = {k: v * scale_factor for k, v in dimensions.items()}
            volume_cm3 *= (scale_factor ** 3) / 1e6
            surface_cm2 *= (scale_factor ** 2) / 100.0

        # Projected Area
        max_projected_area = precise_data.get("projected_area_mm2")
        if max_projected_area is not None:
            max_projected_area *= (scale_factor ** 2)

        if max_projected_area is None:
            if mesh is not None:
                try:
                    areas = []
                    for ax in [[1,0,0], [0,1,0], [0,0,1]]:
                        proj = trimesh.path.polygons.projected(mesh, normal=ax)
                        areas.append(proj.area * (scale_factor ** 2))
                    max_projected_area = float(max(areas))
                except Exception:
                    max_projected_area = float(max(
                        dimensions['x']*dimensions['y'],
                        dimensions['y']*dimensions['z'],
                        dimensions['x']*dimensions['z']
                    ))
            else:
                max_projected_area = float(max(
                    dimensions['x']*dimensions['y'],
                    dimensions['y']*dimensions['z'],
                    dimensions['x']*dimensions['z']
                ))

        logger.info(f"GEOMETRY: Vol={round(volume_cm3,2)}cm3, ProjArea={round(max_projected_area,2)}mm2")

        # ── Step 5: Preview ──────────────────────────────────────────────
        topology = precise_data.get("topology", {
            "solids": 1, "faces": len(mesh.faces) if mesh else 0,
            "edges": 0, "vertices": len(mesh.vertices) if mesh else 0
        })
        validation = precise_data.get("validation", {
            "is_manifold": bool(mesh.is_watertight) if mesh else False,
            "integrity_score": 100 if (mesh and mesh.is_watertight) else 50
        })

        traits = {
            "volume": float(volume_cm3 * 1000.0),
            "surface_area": float(surface_cm2 * 100.0),
            "dimensions": dimensions,
            "projected_area": float(max_projected_area),
            "topology": topology,
            "validation": validation,
        }

        engine_name = "OCP_PRECISE" if precise_data.get("status") == "success" else "MESH_FALLBACK"

        return {
            "analysis_id": analysis_id,
            "traits": traits,
            "engine": engine_name,
            "detected_metal": detected_metal,
            "metadata": {"location": "PENDING_SYNC", "timestamp": time.time()}
        }

    except Exception as e:
        logger.error(f"CRITICAL_FAILURE: {e}", exc_info=True)
        return {"error": str(e)}
