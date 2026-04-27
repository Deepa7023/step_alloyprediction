"""
STEP/IGES Geometry Engine — Dual Engine Architecture (V2.1)
Engine 1: OCP (cadquery-ocp) with CORRECT _s suffix API for static methods
Engine 2: GMSH fallback with built-in OCCT kernel
Includes: Metal Auto-Detection from STEP file metadata
"""

import logging
import os
import gc
import uuid
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# ─── Metal Keyword Detection Map ────────────────────────────────────────────
METAL_KEYWORDS = {
    "ADC12": "Aluminum_ADC12", "A356": "Aluminum_A356", "6061": "Aluminum_6061", "6063": "Aluminum_6061",
    "A380": "Aluminum_A380", "A383": "Aluminum_A380", "A360": "Aluminum_A380",
    "ALUMINUM": "Aluminum_A380", "ALUMINIUM": "Aluminum_A380", "AL ": "Aluminum_A380",
    "ZAMAK 5": "Zinc_Zamak5", "ZAMAK5": "Zinc_Zamak5",
    "ZINC": "Zinc_ZD3", "ZAMAK": "Zinc_ZD3", "ZA": "Zinc_ZD3", "ZDC": "Zinc_ZD3",
    "AM60": "Magnesium_AM60B", "AM60B": "Magnesium_AM60B",
    "MAGNESIUM": "Magnesium_AZ91D", "AZ91": "Magnesium_AZ91D", "AZ91D": "Magnesium_AZ91D", "MG": "Magnesium_AZ91D",
    "BRASS": "Copper_Brass", "BRONZE": "Copper_Brass", "COPPER": "Copper_Brass", "CU": "Copper_Brass",
    "STAINLESS": "Steel_Stainless", "STEEL": "Steel_Stainless", "SS304": "Steel_Stainless", "SS316": "Steel_Stainless",
}

def detect_metal_from_step(file_path: str) -> Optional[str]:
    try:
        with open(file_path, 'r', errors='ignore') as f:
            content = f.read(8192).upper()
        for keyword, metal_name in METAL_KEYWORDS.items():
            if keyword in content:
                return metal_name
    except Exception:
        pass
    return None


# ═══════════════════════════════════════════════════════════════════════════
#  ENGINE 1: OCP (cadquery-ocp) — Correct _s suffix API
# ═══════════════════════════════════════════════════════════════════════════

def _analyze_with_ocp(file_path: str) -> Dict[str, Any]:
    """
    Precise B-Rep analysis using cadquery-ocp.
    
    CRITICAL: In cadquery-ocp, all static C++ methods are exposed with a '_s' suffix.
    - BRepGProp.VolumeProperties_s()   NOT  BRepGProp.VolumeProperties()
    - BRepGProp.SurfaceProperties_s()  NOT  BRepGProp.SurfaceProperties()
    - BRepBndLib.Add_s()               NOT  BRepBndLib.Add()
    
    This is the documented pybind11 convention used by CadQuery itself.
    """
    try:
        from OCP.STEPControl import STEPControl_Reader
        from OCP.IFSelect import IFSelect_RetDone
        from OCP.GProp import GProp_GProps
        from OCP.BRepGProp import BRepGProp
        from OCP.BRepBndLib import BRepBndLib
        from OCP.Bnd import Bnd_Box
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.TopExp import TopExp_Explorer
        from OCP.TopAbs import (
            TopAbs_SOLID, TopAbs_SHELL, TopAbs_FACE, 
            TopAbs_EDGE, TopAbs_VERTEX
        )
    except ImportError as e:
        logger.warning(f"OCP import failed: {e}")
        return {"status": "fallback", "reason": f"OCP_IMPORT_FAILED: {e}"}

    reader = None
    shape = None
    try:
        # 1. Read STEP file
        reader = STEPControl_Reader()
        status = reader.ReadFile(file_path)
        if status != IFSelect_RetDone:
            return {"status": "fallback", "reason": "OCP_FILE_READ_FAILED"}

        if reader.TransferRoots() == 0:
            return {"status": "fallback", "reason": "OCP_TRANSFER_FAILED"}

        shape = reader.OneShape()
        if shape.IsNull():
            return {"status": "fallback", "reason": "OCP_SHAPE_NULL"}

        # 2. Volume (using _s suffix for static method)
        vol_props = GProp_GProps()
        BRepGProp.VolumeProperties_s(shape, vol_props)

        # 3. Surface Area (using _s suffix)
        surf_props = GProp_GProps()
        BRepGProp.SurfaceProperties_s(shape, surf_props)

        # 4. Bounding Box (using _s suffix)
        bbox = Bnd_Box()
        BRepBndLib.Add_s(shape, bbox)
        
        try:
            # Try tuple return first
            xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
        except Exception:
            # Fallback to direct attribute extraction if Get() requires references or fails
            try:
                xmin, ymin, zmin, xmax, ymax, zmax = (
                    bbox.CornerMin().X(), bbox.CornerMin().Y(), bbox.CornerMin().Z(),
                    bbox.CornerMax().X(), bbox.CornerMax().Y(), bbox.CornerMax().Z()
                )
            except:
                # Last resort: null box handling
                xmin, ymin, zmin, xmax, ymax, zmax = 0, 0, 0, 1, 1, 1

        dx = abs(xmax - xmin)
        dy = abs(ymax - ymin)
        dz = abs(zmax - zmin)

        # 5. Topology counts
        topology = {"solids": 0, "shells": 0, "faces": 0, "edges": 0, "vertices": 0}
        topo_map = {
            TopAbs_SOLID: "solids", TopAbs_SHELL: "shells",
            TopAbs_FACE: "faces", TopAbs_EDGE: "edges", TopAbs_VERTEX: "vertices"
        }
        for topo_type, key in topo_map.items():
            exp = TopExp_Explorer(shape, topo_type)
            while exp.More():
                topology[key] += 1
                exp.Next()

        # 6. Validation
        is_valid = BRepCheck_Analyzer(shape).IsValid()

        result = {
            "status": "success",
            "precise_volume_cm3": round(vol_props.Mass() / 1000.0, 4),
            "precise_surface_cm2": round(surf_props.Mass() / 100.0, 4),
            "projected_area_mm2": round(max(dx*dy, dy*dz, dx*dz), 2),
            "dimensions": {"x": round(dx, 2), "y": round(dy, 2), "z": round(dz, 2)},
            "topology": topology,
            "validation": {"is_manifold": is_valid, "integrity_score": 100 if is_valid else 75}
        }

        logger.info(f"OCP_SUCCESS: Vol={result['precise_volume_cm3']}cm3, Faces={topology['faces']}")
        return result

    except AttributeError as e:
        # Log EXACTLY what's available for debugging
        try:
            from OCP import BRepGProp as _mod
            logger.error(f"OCP AttributeError: {e}. BRepGProp dir: {[a for a in dir(_mod.BRepGProp) if 'olume' in a.lower() or a.startswith('V')]}")
        except:
            logger.error(f"OCP AttributeError: {e}")
        return {"status": "fallback", "reason": f"OCP_ATTR_ERROR: {e}"}

    except Exception as e:
        logger.error(f"OCP analysis error: {e}", exc_info=True)
        return {"status": "fallback", "reason": f"OCP_ERROR: {e}"}

    finally:
        del shape, reader
        gc.collect()


# ═══════════════════════════════════════════════════════════════════════════
#  ENGINE 2: GMSH Fallback
# ═══════════════════════════════════════════════════════════════════════════

def _analyze_with_gmsh(file_path: str) -> Dict[str, Any]:
    """
    Fallback STEP analysis using GMSH's built-in OCCT kernel.
    Converts STEP → STL mesh, then uses trimesh for analysis.
    """
    try:
        import gmsh
        import trimesh
    except ImportError as e:
        logger.warning(f"GMSH/Trimesh import failed: {e}")
        return {"status": "fallback", "reason": f"GMSH_IMPORT_FAILED: {e}"}

    temp_stl = None
    try:
        gmsh.initialize()
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("FallbackEngine")
        gmsh.merge(file_path)

        # Generate surface mesh
        gmsh.option.setNumber("Mesh.Algorithm", 6)
        gmsh.model.mesh.generate(2)

        temp_stl = f"/tmp/gmsh_{uuid.uuid4().hex[:8]}.stl"
        gmsh.write(temp_stl)
        gmsh.finalize()

        mesh = trimesh.load(temp_stl)
        if isinstance(mesh, trimesh.Scene):
            parts = [g for g in mesh.geometry.values() if isinstance(g, trimesh.Trimesh)]
            if not parts:
                return {"status": "fallback", "reason": "GMSH_EMPTY_MESH"}
            mesh = trimesh.util.concatenate(parts)

        if not hasattr(mesh, 'vertices') or len(mesh.vertices) == 0:
            return {"status": "fallback", "reason": "GMSH_NO_VERTICES"}

        dims = mesh.extents
        dx, dy, dz = float(dims[0]), float(dims[1]), float(dims[2])

        return {
            "status": "success",
            "precise_volume_cm3": round(abs(mesh.volume) / 1000.0, 4),
            "precise_surface_cm2": round(mesh.area / 100.0, 4),
            "projected_area_mm2": round(max(dx*dy, dy*dz, dx*dz), 2),
            "dimensions": {"x": round(dx, 2), "y": round(dy, 2), "z": round(dz, 2)},
            "topology": {"solids": 1, "faces": len(mesh.faces), "edges": 0, "vertices": len(mesh.vertices)},
            "validation": {"is_manifold": bool(mesh.is_watertight), "integrity_score": 90 if mesh.is_watertight else 65}
        }

    except Exception as e:
        logger.error(f"GMSH fallback failed: {e}", exc_info=True)
        try:
            gmsh.finalize()
        except:
            pass
        return {"status": "fallback", "reason": f"GMSH_ERROR: {e}"}
    finally:
        if temp_stl and os.path.exists(temp_stl):
            try: os.remove(temp_stl)
            except: pass
        gc.collect()


# ═══════════════════════════════════════════════════════════════════════════
#  PUBLIC API — PreciseSTEPAnalyzer (used by cad_analyzer.py)
# ═══════════════════════════════════════════════════════════════════════════

class PreciseSTEPAnalyzer:
    """
    Multi-engine STEP analyzer. Tries OCP first (precise B-Rep), 
    falls back to GMSH (mesh-based approximation).
    """

    def analyze(self, file_path: str) -> Dict[str, Any]:
        # Engine 1: OCP with correct _s suffix API
        logger.info("Attempting OCP engine (cadquery-ocp)...")
        result = _analyze_with_ocp(file_path)
        if result.get("status") == "success":
            return result

        ocp_reason = result.get("reason", "unknown")
        logger.warning(f"OCP failed: {ocp_reason}. Trying GMSH...")

        # Engine 2: GMSH fallback
        result = _analyze_with_gmsh(file_path)
        if result.get("status") == "success":
            return result

        gmsh_reason = result.get("reason", "unknown")
        logger.error(f"Both engines failed. OCP: {ocp_reason}, GMSH: {gmsh_reason}")
        return {"status": "fallback", "reason": f"OCP: {ocp_reason} | GMSH: {gmsh_reason}"}
