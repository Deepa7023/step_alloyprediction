import trimesh
import os
import numpy as np
import base64
import io
import uuid
import time
import logging
import tempfile

from .step_engine_ocp import PreciseSTEPAnalyzer, detect_metal_from_step

logger = logging.getLogger(__name__)

SUPPORTED_CAD_EXTENSIONS = [
    ".step", ".stp", ".iges", ".igs",
    ".stl", ".obj", ".ply", ".glb", ".gltf",
    ".3mf", ".off", ".dae"
]


def _load_mesh(file_path):
    mesh_raw = trimesh.load(file_path)
    if isinstance(mesh_raw, trimesh.Scene):
        parts = [g for g in mesh_raw.geometry.values() if isinstance(g, trimesh.Trimesh)]
        if parts:
            return trimesh.util.concatenate(parts)
    elif isinstance(mesh_raw, trimesh.Trimesh):
        return mesh_raw
    return None


def _mesh_brep_with_gmsh(file_path):
    temp_stl = None
    try:
        import gmsh

        gmsh.initialize()
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("PreviewMesh")
        gmsh.merge(file_path)
        gmsh.option.setNumber("Mesh.Algorithm", 6)
        gmsh.option.setNumber("Mesh.CharacteristicLengthMin", 2)
        gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 12)
        gmsh.model.mesh.generate(2)
        temp_stl = os.path.join(tempfile.gettempdir(), f"preview_{uuid.uuid4().hex}.stl")
        gmsh.write(temp_stl)
        gmsh.finalize()
        return _load_mesh(temp_stl)
    except Exception as e:
        logger.warning(f"GMSH preview mesh failed: {e}")
        try:
            import gmsh
            gmsh.finalize()
        except Exception:
            pass
        return None
    finally:
        if temp_stl and os.path.exists(temp_stl):
            try:
                os.remove(temp_stl)
            except Exception:
                pass


def analyze_cad(file_path):
    """
    Analyzes a CAD file with dual-engine fallback:
      1. OCP (cadquery-ocp) — Precise B-Rep analysis
      2. GMSH — Mesh-based approximation  
      3. Trimesh — For preview mesh and non-STEP formats
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
        if ext in ['.step', '.stp']:
            detected_metal = detect_metal_from_step(file_path)
            if detected_metal:
                logger.info(f"METAL_DETECT: Auto-detected {detected_metal}")

        # ── Step 1: Precise Analysis (STEP/IGES only) ────────────────────
        if ext in ['.step', '.stp', '.iges', '.igs']:
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

        if mesh is None and ext in ['.step', '.stp', '.iges', '.igs']:
            mesh = _mesh_brep_with_gmsh(file_path)

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
        preview_b64 = ""
        if mesh is not None:
            buf = io.BytesIO()
            mesh.export(buf, file_type='stl')
            preview_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

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
            "preview_mesh": f"data:model/stl;base64,{preview_b64}" if preview_b64 else "",
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
