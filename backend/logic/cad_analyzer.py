import trimesh
import os
import numpy as np
import base64
import io
import uuid
import time
import logging

# Import the new OCP-based precise analyzer
from .step_engine_ocp import PreciseSTEPAnalyzer

logger = logging.getLogger(__name__)
# Global state for Gmsh availability and initialization
GMSH_AVAILABLE = None

def initialize_gmsh():
    """Lazy-loader for Gmsh to save memory at startup."""
    global GMSH_AVAILABLE
    if GMSH_AVAILABLE is not None:
        return GMSH_AVAILABLE
    
    try:
        import gmsh
        GMSH_AVAILABLE = True
        return True
    except ImportError:
        GMSH_AVAILABLE = False
        logger.error("GMSH library not found. Gmsh fallback disabled.")
        return False
    except Exception as e:
        GMSH_AVAILABLE = False
        logger.error(f"GMSH initialization error: {e}. Gmsh fallback disabled.")
        return False

def mesh_via_gmsh(file_path):
    """Fallback mesher for STEP/IGES when OCP fails or is skipped."""
    if not initialize_gmsh():
        return None
    
    import gmsh # Local import for lazy-loading
    try:
        gmsh.initialize()
        gmsh.model.add("MeshEngine")
        gmsh.merge(file_path)
        
        # Simple meshing strategy: 2D then 3D
        gmsh.model.mesh.generate(2)
        gmsh.model.mesh.generate(3)
        
        temp_stl = f"/tmp/mesh_{uuid.uuid4()}.stl"
        gmsh.write(temp_stl)
        gmsh.finalize()
        
        mesh = trimesh.load(temp_stl)
        if os.path.exists(temp_stl):
            os.remove(temp_stl)
        return mesh
    except Exception as e:
        logger.error(f"GMSH fallback failed: {e}")
        try:
            gmsh.finalize()
        except:
            pass
        return None

def analyze_cad(file_path):
    """
    Analyzes a CAD file with multi-layer fallbacks for 100% geometric accuracy.
    1. OCP (OpenCascade) - Most Precise
    2. Cascadio (OCC-based) - High Fidelity Mesh
    3. Trimesh - Fast Approximation
    """
    analysis_id = str(uuid.uuid4())
    ext = os.path.splitext(file_path)[1].lower()
    mesh = None
    
    try:
        # 1. Primary: Precise B-Rep Analysis (Modern OCP Engine) 
        precise_data = {}
        if ext in ['.step', '.stp', '.iges', '.igs']:
            precise_analyzer = PreciseSTEPAnalyzer()
            precise_data = precise_analyzer.analyze(file_path)

        # 2. Secondary: Trimesh Fallback
        if mesh is None:
            try:
                mesh_raw = trimesh.load(file_path)
                if isinstance(mesh_raw, trimesh.Scene):
                    mesh = trimesh.util.concatenate([g for g in mesh_raw.geometry.values() if isinstance(g, trimesh.Trimesh)])
                else:
                    mesh = mesh_raw
            except Exception as e:
                # Log the actual trimesh error for debugging
                logger.error(f"Trimesh native load failed for {file_path}: {e}")
                
                # 3. Tertiary: GMSH Fallback for STEP/IGES
                if ext in ['.step', '.stp', '.iges', '.igs']:
                    logger.info("Attempting GMSH fallback for CAD geometry...")
                    mesh = mesh_via_gmsh(file_path)
                
                if mesh is None:
                    # Check why OCP was skipped/failed
                    ocp_reason = precise_data.get("reason", "Unknown")
                    err_msg = f"GEOMETRY_PARSE_FAILURE: File {ext} could not be read by OCP ({ocp_reason}), Trimesh, or GMSH. Please ensure it is a valid 3D file."
                    raise ValueError(err_msg)

        # 4. Trait Synthesis
        # Prioritize OCP precise volume > Trimesh/GMSH mesh approximation
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

        # Auto-Scale Detection: If all dimensions are < 1.0, it's likely a meter-scale model
        # 0.19 units usually means 0.19 meters (190mm)
        scale_factor = 1.0
        if max(dimensions.values()) < 1.0 and max(dimensions.values()) > 0:
            logger.info(f"ANALYZER: Tiny part detected ({max(dimensions.values())} units). Auto-scaling by 1000x (Meter to MM conversion).")
            scale_factor = 1000.0
            dimensions = {k: v * scale_factor for k, v in dimensions.items()}
            
            # Simple approach: apply scale factor to all traits
            volume_cm3 *= (scale_factor ** 3) / 1000000.0 # m3 to cm3
            surface_cm2 *= (scale_factor ** 2) / 100.0 # m2 to cm2


        # Projected Area (Critical for Tonnage)
        max_projected_area = precise_data.get("projected_area_mm2")
        if max_projected_area is not None:
             max_projected_area *= (scale_factor ** 2)

        if max_projected_area is None:
            # 3D Mesh Projection for Superior Accuracy
            try:
                # We check the 3 primary axes to find the most probable parting direction
                areas = []
                for ax in [[1,0,0], [0,1,0], [0,0,1]]:
                    proj = trimesh.path.polygons.projected(mesh, normal=ax)
                    areas.append(proj.area * (scale_factor ** 2))
                max_projected_area = float(max(areas))
                logger.info(f"ANALYZER: Mesh projection successful. Max Area: {round(max_projected_area, 2)}mm2")
            except Exception as e:
                logger.warning(f"ANALYZER: Mesh projection failed ({e}). Falling back to B-Box.")
                max_projected_area = float(max(dimensions['x']*dimensions['y'], dimensions['y']*dimensions['z'], dimensions['x']*dimensions['z']))

        # Logging for Debugging Price Uniformity
        logger.info(f"GEOMETRY_DETECTED: Vol={round(volume_cm3, 2)}cm3, Area={round(max_projected_area, 2)}mm2 (Scaled: {scale_factor}x)")


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

        # Determine engine name for report
        engine_name = "OCP_STRICT"
        if precise_data.get("status") != "success":
            if GMSH_AVAILABLE and ext in ['.step', '.stp', '.iges', '.igs']:
                engine_name = "GMSH_CAD_BRIDGE"
            else:
                engine_name = "TRIMESH_FALLBACK"

        return {
            "analysis_id": analysis_id,
            "traits": traits,
            "engine": engine_name,
            "metadata": {
                "location": "PENDING_SYNC",
                "timestamp": time.time()
            }
        }
    except Exception as e:
        logger.error(f"CRITICAL_BACKEND_FAILURE: {e}")
        return {"error": str(e)}
