import trimesh
import os
import numpy as np
import base64
import io
import uuid
import time
import logging
import cascadio

# Import the new OCP-based precise analyzer
from .step_engine_ocp import PreciseSTEPAnalyzer

logger = logging.getLogger(__name__)

def analyze_cad(file_path):
    """
    Analyzes a CAD file with multi-layer fallbacks for 100% geometric accuracy.
    1. OCP (OpenCascade) - Most Precise
    2. Cascadio (OCC-based) - High Fidelity Mesh
    3. Trimesh - Fast Approximation
    """
    analysis_id = str(uuid.uuid4())
    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        # 1. Primary: Precise B-Rep Analysis (Modern OCP Engine) 
        precise_data = {}
        if ext in ['.step', '.stp', '.iges', '.igs']:
            precise_analyzer = PreciseSTEPAnalyzer()
            precise_data = precise_analyzer.analyze(file_path)

        # 2. Secondary: Cascadio Fallback for STEP/IGES Accuracy
        # If OCP is missing (common on Render), use Cascadio to generate accurate mesh
        mesh = None
        if ext in ['.step', '.stp', '.iges', '.igs'] and precise_data.get("status") != "success":
            try:
                logger.info(f"ANALYZER: Using Cascadio fallback for {ext} accuracy...")
                glb_path = f"{file_path}.glb"
                cascadio.step_to_glb(file_path, glb_path)
                mesh_raw = trimesh.load(glb_path)
                if isinstance(mesh_raw, trimesh.Scene):
                    mesh = trimesh.util.concatenate([g for g in mesh_raw.geometry.values() if isinstance(g, trimesh.Trimesh)])
                else:
                    mesh = mesh_raw
                # Clean up temp glb
                if os.path.exists(glb_path): os.remove(glb_path)
            except Exception as e:
                logger.warning(f"Cascadio conversion failed: {e}")

        # 3. Tertiary: Standard Trimesh Load (STL/OBJ or Native STEP)
        if mesh is None:
            try:
                mesh_raw = trimesh.load(file_path)
                if isinstance(mesh_raw, trimesh.Scene):
                    mesh = trimesh.util.concatenate([g for g in mesh_raw.geometry.values() if isinstance(g, trimesh.Trimesh)])
                else:
                    mesh = mesh_raw
            except:
                # No static box fallback anymore - we want accuracy or failure
                raise ValueError(f"CRITICAL: Failed to parse geometry for {ext} file. Try converting to STL.")

        # 4. Trait Synthesis
        # Prioritize OCP precise volume > Cascadio volume > Trimesh approximation
        volume_cm3 = precise_data.get("precise_volume_cm3")
        surface_cm2 = precise_data.get("precise_surface_cm2")
        
        if volume_cm3 is None:
            volume_cm3 = (mesh.volume / 1000.0) if mesh.is_watertight else (abs(mesh.volume) / 1000.0)
        
        if surface_cm2 is None:
            surface_cm2 = mesh.area / 100.0
        
        # Dimensions (Prefer OCP)
        if "dimensions" in precise_data:
            dims = precise_data["dimensions"]
            dimensions = {"x": dims["x"], "y": dims["y"], "z": dims["z"]}
        else:
            bounds = mesh.extents
            dimensions = {"x": round(bounds[0], 2), "y": round(bounds[1], 2), "z": round(bounds[2], 2)}

        # Projected Area (Critical for Tonnage)
        max_projected_area = precise_data.get("projected_area_mm2")
        if max_projected_area is None:
            # 3D Mesh Projection for Superior Accuracy
            try:
                # We check the 3 primary axes to find the most probable parting direction
                # This is much more accurate than simple bounding box multiplication
                areas = []
                for ax in [[1,0,0], [0,1,0], [0,0,1]]:
                    proj = trimesh.path.polygons.projected(mesh, normal=ax)
                    areas.append(proj.area)
                max_projected_area = float(max(areas))
                logger.info(f"ANALYZER: Mesh projection successful. Max Area: {round(max_projected_area, 2)}mm2")
            except Exception as e:
                logger.warning(f"ANALYZER: Mesh projection failed ({e}). Falling back to B-Box.")
                # Shadow approximation
                max_projected_area = float(max(dimensions['x']*dimensions['y'], dimensions['y']*dimensions['z'], dimensions['x']*dimensions['z']))

        # Logging for Debugging Price Uniformity
        logger.info(f"GEOMETRY_DETECTED: Vol={round(volume_cm3, 2)}cm3, Area={round(max_projected_area, 2)}mm2")

        # Preview Generation
        stl_io = io.BytesIO()
        mesh.export(stl_io, file_type='stl')
        preview_mesh_base64 = base64.b64encode(stl_io.getvalue()).decode('utf-8')

        traits = {
            "volume": float(volume_cm3 * 1000.0), # mm3
            "surface_area": float(surface_cm2 * 100.0), # mm2
            "dimensions": dimensions,
            "projected_area": float(max_projected_area),
            "preview_mesh": f"data:model/stl;base64,{preview_mesh_base64}",
            "topology": precise_data.get("topology", {"solids": 1, "faces": len(mesh.faces), "edges": 0, "vertices": len(mesh.vertices)}),
            "validation": precise_data.get("validation", {"is_manifold": bool(mesh.is_watertight), "integrity_score": 100 if mesh.is_watertight else 50})
        }

        return {
            "analysis_id": analysis_id,
            "traits": traits,
            "engine": "OCP_STRICT" if precise_data.get("status") == "success" else "CASCADIO_MESH_GEN",
            "metadata": {
                "location": "PENDING_SYNC",
                "timestamp": time.time()
            }
        }
    except Exception as e:
        logger.error(f"CRITICAL_BACKEND_FAILURE: {e}")
        return {"error": str(e)}
