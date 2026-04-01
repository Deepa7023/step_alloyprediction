"""
Advanced B-Rep Analysis Engine (OCCT-based)
Includes: Metal Auto-Detection from STEP file metadata
"""

import logging
import re
import os
import gc
from typing import Dict, Any, Optional

# Global state for OCP availability and initialization
OCP_AVAILABLE = None 

def initialize_ocp():
    """Lazy-loader for OCP to save memory at startup."""
    global OCP_AVAILABLE, STEPControl_Reader, IFSelect_RetDone, Bnd, BRepGProp, GProp, BRepCheck, BRepBndLib, TopExp, TopAbs
    if OCP_AVAILABLE is not None:
        return OCP_AVAILABLE
    
    try:
        from OCP.STEPControl import STEPControl_Reader
        from OCP.IFSelect import IFSelect_RetDone
        import OCP.Bnd as Bnd
        import OCP.BRepGProp as BRepGProp
        import OCP.GProp as GProp
        import OCP.BRepCheck as BRepCheck
        import OCP.BRepBndLib as BRepBndLib
        import OCP.TopExp as TopExp
        import OCP.TopAbs as TopAbs
        
        OCP_AVAILABLE = True
        return True
    except Exception as e:
        OCP_AVAILABLE = False
        logging.getLogger(__name__).error(f"OCP LAZY-LOAD FAILED: {e}. Priority analysis disabled.")
        return False

logger = logging.getLogger(__name__)

# ─── Metal Keyword Detection Map ────────────────────────────────────────────
METAL_KEYWORDS = {
    "A380": "Aluminum_A380",
    "A383": "Aluminum_A380",
    "A360": "Aluminum_A380",
    "ADC12": "Aluminum_A380",
    "ALUMINUM": "Aluminum_A380",
    "ALUMINIUM": "Aluminum_A380",
    "AL": "Aluminum_A380",
    "6061": "Aluminum_A380",
    "6063": "Aluminum_A380",
    "ZINC": "Zinc_ZD3",
    "ZAMAK": "Zinc_ZD3",
    "ZA": "Zinc_ZD3",
    "ZDC": "Zinc_ZD3",
    "MAGNESIUM": "Magnesium_AZ91D",
    "AZ91": "Magnesium_AZ91D",
    "AM60": "Magnesium_AZ91D",
    "MG": "Magnesium_AZ91D",
}

def detect_metal_from_step(file_path: str) -> Optional[str]:
    try:
        with open(file_path, 'r', errors='ignore') as f:
            content = f.read(8192)  # Read first 8KB
        content_upper = content.upper()
        for keyword, metal_name in METAL_KEYWORDS.items():
            if keyword in content_upper:
                return metal_name
    except Exception as e:
        logger.warning(f"Metal detection scan failed: {e}")
    return None

class PreciseSTEPAnalyzer:
    """Robust OCP-based STEP analyzer with Lazy-Loading and multi-level namespace search."""
    
    def __init__(self):
        pass

    def _get_ocp_method(self, parent, method_name):
        """
        NUCLEAR DISCOVERY v2: Searches for attributes with Prefix support (e.g. BRepGProp_VolumeProperties).
        """
        # Get base name for prefixing
        prefix = ""
        if hasattr(parent, "__name__"):
            prefix = parent.__name__.split('.')[-1]
            
        candidates = [
            method_name, 
            f"{method_name}_", 
            f"{prefix}_{method_name}", # E.g. BRepGProp_VolumeProperties
            f"{prefix}_{method_name}_",
            method_name.lower(),
            f"{prefix}_{method_name.lower()}"
        ]
        
        # 1. Standard Search
        for cand in candidates:
            if hasattr(parent, cand):
                return getattr(parent, cand)
                
        # 2. Namespace Scan (Internal same-name class)
        if prefix and hasattr(parent, prefix):
            internal = getattr(parent, prefix)
            for cand in candidates:
                if hasattr(internal, cand):
                    return getattr(internal, cand)

        # 3. Aggressivedir() Scan
        try:
            available = dir(parent)
            # Find any attribute that CONTAINS the method name
            for attr in available:
                if method_name.lower() in attr.lower():
                    logger.info(f"OCP_DISCOVERY: Pattern Match for '{method_name}' -> '{attr}' in {parent}")
                    return getattr(parent, attr)
        except:
            pass

        # 4. Ultimate Failure: Log dir() for remote debugging
        logger.error(f"OCP Attribute Error: {method_name} NOT FOUND in {parent}. Available: {dir(parent)[:50]}...")
        raise AttributeError(f"OCP Attribute Error: {method_name} NOT FOUND in {parent}")

    def analyze(self, file_path: str) -> Dict[str, Any]:
        """Entry point. Returns 'fallback' status on ANY error to prevent crash."""
        if not initialize_ocp():
             return {"status": "fallback", "reason": "OCP_LOAD_FAILURE"}

        shape = None
        reader = None
        
        try:
            reader = STEPControl_Reader()
            if reader.ReadFile(file_path) != IFSelect_RetDone:
                return {"status": "fallback", "reason": "FILE_READ_FAILED"}
            
            if reader.TransferRoots() == 0:
                return {"status": "fallback", "reason": "TRANSFER_ROOTS_FAILED"}

            shape = reader.OneShape()
            if shape.IsNull():
                return {"status": "fallback", "reason": "SHAPE_NULL"}

            # Get the GProps class (it might be under GProp or GProp.GProp_GProps)
            gprops_klass = self._get_ocp_method(GProp, "GProp_GProps")
            
            # 1. Precise Geometrics
            vol_props = gprops_klass()
            self._get_ocp_method(BRepGProp, "VolumeProperties")(shape, vol_props, False, False, False)
            
            surf_props = gprops_klass()
            self._get_ocp_method(BRepGProp, "SurfaceProperties")(shape, surf_props, False, False)

            # Bounding Box (Uses Bnd.Bnd_Box)
            bbox = Bnd.Bnd_Box()
            self._get_ocp_method(bbox, "SetGap")(0.0)
            self._get_ocp_method(BRepBndLib, "Add")(shape, bbox, True)
            
            # Robust Corner Retrieval
            try:
                # Some OCP versions have Get(), others have get(), others have CornerMin
                if hasattr(bbox, "Get"): res = bbox.Get()
                elif hasattr(bbox, "get"): res = bbox.get()
                else: res = None

                if res and isinstance(res, tuple) and len(res) == 6:
                    xmin, ymin, zmin, xmax, ymax, zmax = res
                else:
                    c_min = self._get_ocp_method(bbox, "CornerMin")()
                    c_max = self._get_ocp_method(bbox, "CornerMax")()
                    xmin, ymin, zmin = c_min.X(), c_min.Y(), c_min.Z()
                    xmax, ymax, zmax = c_max.X(), c_max.Y(), c_max.Z()
            except:
                xmin, ymin, zmin, xmax, ymax, zmax = 0, 0, 0, 0.01, 0.01, 0.01

            dx, dy, dz = abs(xmax-xmin), abs(ymax-ymin), abs(zmax-zmin)

            # 2. Topology and Validation
            topology = self._get_topology_counts(shape)
            is_valid = self._get_ocp_method(BRepCheck, "BRepCheck_Analyzer")(shape).IsValid()

            result = {
                "status": "success",
                "precise_volume_cm3": round(vol_props.Mass() / 1000.0, 4),
                "precise_surface_cm2": round(surf_props.Mass() / 100.0, 4),
                "projected_area_mm2": round(max(dx*dy, dy*dz, dx*dz), 2),
                "dimensions": {"x": round(dx, 2), "y": round(dy, 2), "z": round(dz, 2)},
                "topology": topology,
                "validation": {"is_manifold": is_valid, "integrity_score": 100 if is_valid else 75}
            }
            
            # Immediate Reclamation
            del shape, reader
            gc.collect()
            return result

        except Exception as e:
            logger.error(f"OCP Robustness Error: {str(e)}", exc_info=True)
            return {"status": "fallback", "reason": f"OCP_API_INCOMPATIBILITY: {str(e)}"}

    def _get_topology_counts(self, shape) -> Dict[str, int]:
        counts = {"solids": 0, "shells": 0, "faces": 0, "edges": 0, "vertices": 0}
        try:
            exp = TopExp.TopExp_Explorer()
            
            # Map topology types
            types = {
                TopAbs.TopAbs_SOLID: "solids",
                TopAbs.TopAbs_FACE: "faces",
                TopAbs.TopAbs_EDGE: "edges",
                TopAbs.TopAbs_VERTEX: "vertices"
            }
            
            for t_abs, key in types.items():
                exp.Init(shape, t_abs)
                while exp.More():
                    counts[key] += 1
                    exp.Next()
                    
        except: pass
        return counts
