"""
Advanced B-Rep Analysis Engine (OCCT-based)
Includes: Metal Auto-Detection from STEP file metadata
"""

import logging
import re
import os
from typing import Dict, Any, Optional

# Global state for OCP availability and initialization
OCP_AVAILABLE = None 

def initialize_ocp():
    """Lazy-loader for OCP to save memory at startup."""
    global OCP_AVAILABLE
    if OCP_AVAILABLE is not None:
        return OCP_AVAILABLE
    
    try:
        from OCP.STEPControl import STEPControl_Reader
        from OCP.IFSelect import IFSelect_RetDone
        from OCP.Bnd import Bnd_Box
        from OCP.BRepGProp import BRepGProp
        from OCP.GProp import GProp_GProps
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.TopExp import TopExp_Explorer
        from OCP.TopAbs import TopAbs_SOLID, TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX
        from OCP.BRepBndLib import BRepBndLib
        OCP_AVAILABLE = True
        return True
    except Exception as e:
        OCP_AVAILABLE = False
        logging.getLogger(__name__).error(f"OCP LAZY-LOAD FAILED: {e}. Priority analysis disabled.")
        return False

logger = logging.getLogger(__name__)

# ─── Metal Keyword Detection Map ────────────────────────────────────────────
# Maps common STEP file material keywords → known HPDC metal names
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
    """
    Scans STEP file text for material/product keywords to auto-detect metal.
    Returns a known metal name or None if not detectable.
    """
    try:
        with open(file_path, 'r', errors='ignore') as f:
            content = f.read(8192)  # Read first 8KB (headers only)
        
        content_upper = content.upper()
        for keyword, metal_name in METAL_KEYWORDS.items():
            if keyword in content_upper:
                logger.info(f"Metal auto-detected: '{keyword}' → '{metal_name}'")
                return metal_name
    except Exception as e:
        logger.warning(f"Metal detection scan failed: {e}")
    
    return None  # Cannot determine from file


class PreciseSTEPAnalyzer:
    """Robust OCP-based STEP analyzer with Lazy-Loading to save memory."""
    
    def __init__(self):
        # We don't initialize on __init__ anymore
        pass

    def _get_ocp_method(self, obj, method_name):
        """Helper to find OCP method across version-specific naming (e.g. VolumeProperties vs VolumeProperties_)"""
        for name in [method_name, f"{method_name}_"]:
            if hasattr(obj, name):
                return getattr(obj, name)
        raise AttributeError(f"OCP Object {type(obj)} has no attribute {method_name} or {method_name}_")

    def analyze(self, file_path: str) -> Dict[str, Any]:
        if not initialize_ocp():
             return {"status": "skipped", "reason": "OCP_LOAD_FAILURE_OR_NOT_INSTALLED"}

        # Local imports for lazy-loading
        from OCP.STEPControl import STEPControl_Reader
        from OCP.IFSelect import IFSelect_RetDone
        from OCP.Bnd import Bnd_Box
        from OCP.BRepGProp import BRepGProp
        from OCP.GProp import GProp_GProps
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.BRepBndLib import BRepBndLib

        import gc

        try:
            reader = STEPControl_Reader()
            if reader.ReadFile(file_path) != IFSelect_RetDone:
                # Cleanup if read fails
                del reader
                gc.collect()
                raise ValueError("Invalid STEP file")
            
            if reader.TransferRoots() == 0:
                del reader
                gc.collect()
                raise ValueError("No transferable roots")

            shape = reader.OneShape()

            # 1. Precise Geometrics
            vol_props = GProp_GProps()
            # Try both naming conventions: VolumeProperties and VolumeProperties_
            self._get_ocp_method(BRepGProp, "VolumeProperties")(shape, vol_props, False, False, False)
            
            surf_props = GProp_GProps()
            self._get_ocp_method(BRepGProp, "SurfaceProperties")(shape, surf_props, False, False)

            bbox = Bnd_Box()
            bbox.SetGap(0.0)
            BRepBndLib.Add(shape, bbox, True)
            
            # Robust Corner Retrieval
            try:
                xmin, ymin, zmin, xmax, ymax, zmax = 0, 0, 0, 0, 0, 0
                
                # Check for either bbox.Get() or bbox.get() or bbox.CornerMin/Max
                if hasattr(bbox, "Get"):
                    res = bbox.Get()
                elif hasattr(bbox, "get"):
                    res = bbox.get()
                else:
                    res = None

                if res and isinstance(res, tuple) and len(res) == 6:
                    xmin, ymin, zmin, xmax, ymax, zmax = res
                else:
                    # Fallback to CornerMin/Max with version detection
                    c_min = self._get_ocp_method(bbox, "CornerMin")()
                    c_max = self._get_ocp_method(bbox, "CornerMax")()
                    xmin, ymin, zmin = c_min.X(), c_min.Y(), c_min.Z()
                    xmax, ymax, zmax = c_max.X(), c_max.Y(), c_max.Z()
            except Exception as e:
                print(f"BBox Retrieval Debug: {str(e)}")
                xmin, ymin, zmin, xmax, ymax, zmax = 0, 0, 0, 0.01, 0.01, 0.01

            dx = abs(xmax - xmin)
            dy = abs(ymax - ymin)
            dz = abs(zmax - zmin)

            # 2. Topology Check
            topology = self._get_topology_counts(shape)

            # 3. Validation (Geometric Integrity)
            analyzer = BRepCheck_Analyzer(shape)
            is_valid = analyzer.IsValid()

            # Projected Area Calculation (Max Principal Shadow)
            proj_area = max(dx * dy, dy * dz, dx * dz)

            result = {
                "status": "success",
                "precise_volume_cm3": round(vol_props.Mass() / 1000.0, 4),
                "precise_surface_cm2": round(surf_props.Mass() / 100.0, 4),
                "projected_area_mm2": round(proj_area, 2),
                "dimensions": {
                    "x": round(dx, 2),
                    "y": round(dy, 2),
                    "z": round(dz, 2)
                },
                "topology": topology,
                "validation": {
                    "is_manifold": is_valid,
                    "integrity_score": 100 if is_valid else 75
                }
            }

            # AGGRESSIVE CLEANUP: Explicitly delete heavy OCP objects
            del shape
            del reader
            del analyzer
            del vol_props
            del surf_props
            del bbox
            gc.collect()

            return result
        except Exception as e:
            # Emergency cleanup on error
            try:
                del shape
            except: pass
            try:
                del reader
            except: pass
            gc.collect()
            
            logger.error(f"OCP Analysis Error on {file_path}: {e}", exc_info=True)
            return {"status": "error", "reason": f"OCP_FAIL: {str(e)}"}

    def _get_topology_counts(self, shape) -> Dict[str, int]:
        # Local imports for lazy-loading
        from OCP.TopExp import TopExp_Explorer
        from OCP.TopAbs import TopAbs_SOLID, TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX

        counts = {"solids": 0, "shells": 0, "faces": 0, "edges": 0, "vertices": 0}
        exp = TopExp_Explorer()
        
        exp.Init(shape, TopAbs_SOLID)
        while exp.More():
            counts["solids"] += 1
            exp.Next()
            
        exp.Init(shape, TopAbs_FACE)
        while exp.More():
            counts["faces"] += 1
            exp.Next()
 
        exp.Init(shape, TopAbs_EDGE)
        while exp.More():
            counts["edges"] += 1
            exp.Next()

        exp.Init(shape, TopAbs_VERTEX)
        while exp.More():
            counts["vertices"] += 1
            exp.Next()

        import gc
        del exp
        gc.collect()
        
        return counts
