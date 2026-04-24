"""
HPDC COST ENGINE — Commercial & Manufacturing Realistic
-------------------------------------------------------
Uses CAD geometry as input but applies HPDC normalization
to avoid overestimated weight, area, and price.
"""

from typing import Dict


# -----------------------------
# Alloy densities (g/cm3)
# -----------------------------
ALLOY_DENSITY = {
    "Aluminum_A380": 2.7,
    "Aluminum_ADC12": 2.72,
    "Aluminum_A356": 2.68,
    "Zinc_ZD3": 6.6,
    "Magnesium_AZ91D": 1.81,
}


def derive_costing_geometry(
    cad_volume_mm3: float,
    cad_surface_area_mm2: float,
    dx: float,
    dy: float,
    dz: float,
    alloy: str
) -> Dict[str, float]:
    """
    Converts CAD geometry into manufacturing‑realistic HPDC geometry
    """

    # ----------------------------------------------------
    # 1. CAD solid weight (truth, not charged weight)
    # ----------------------------------------------------
    density = ALLOY_DENSITY.get(alloy, 2.7)   # default aluminum
    cad_weight_kg = (cad_volume_mm3 / 1e6) * density

    # ----------------------------------------------------
    # 2. Chargeable HPDC weight (REALITY FIX ✅)
    # ----------------------------------------------------
    EFFECTIVE_DENSITY_FACTOR = 0.95   # porosity
    CHARGEABLE_WEIGHT_FACTOR = 0.85   # thin walls, runners trimmed

    chargeable_weight_kg = (
        cad_weight_kg
        * EFFECTIVE_DENSITY_FACTOR
        * CHARGEABLE_WEIGHT_FACTOR
    )

    # ----------------------------------------------------
    # 3. Effective projected area (PRESS REALITY ✅)
    # ----------------------------------------------------
    # Assume die opens in Z direction
    cad_die_face_area = dx * dy       # NOT bounding box max

    PROJECTED_AREA_FACTOR = 0.70      # ribs, pockets, cutouts
    effective_projected_area_mm2 = cad_die_face_area * PROJECTED_AREA_FACTOR

    # ----------------------------------------------------
    # 4. Effective surface area (PROCESS REALITY ✅)
    # ----------------------------------------------------
    SURFACE_AREA_FACTOR = 0.72        # cosmetics & fillets ignored
    effective_surface_area_mm2 = cad_surface_area_mm2 * SURFACE_AREA_FACTOR

    return {
        # CAD truth (for display)
        "cad_weight_kg": round(cad_weight_kg, 2),
        "cad_surface_area_mm2": round(cad_surface_area_mm2, 0),
        "cad_projected_area_mm2": round(cad_die_face_area, 0),

        # Costing truth (USED BELOW)
        "chargeable_weight_kg": round(chargeable_weight_kg, 2),
        "effective_projected_area_mm2": round(effective_projected_area_mm2, 0),
        "effective_surface_area_mm2": round(effective_surface_area_mm2, 0),
    }


# ============================================================
# MAIN COST FUNCTION
# ============================================================
def calculate_hpdc_cost(
    cad_traits: Dict,
    alloy: str,
    price_per_kg: float,
    press_rate_per_mm2: float,
    conversion_rate_per_kg: float
) -> Dict[str, float]:

    # STEP A: Manufacturing normalization
    geom = derive_costing_geometry(
        cad_volume_mm3=cad_traits["volume_mm3"],
        cad_surface_area_mm2=cad_traits["surface_area_mm2"],
        dx=cad_traits["DX"],
        dy=cad_traits["DY"],
        dz=cad_traits["DZ"],
        alloy=alloy
    )

    # STEP B: Cost calculations (REALISTIC ✅)
    material_cost = geom["chargeable_weight_kg"] * price_per_kg
    press_cost = geom["effective_projected_area_mm2"] * press_rate_per_mm2
    conversion_cost = geom["chargeable_weight_kg"] * conversion_rate_per_kg

    total_cost = material_cost + press_cost + conversion_cost

    return {
        # Geometry (for UI transparency)
        **geom,

        # Cost breakdown
        "material_cost": round(material_cost, 2),
        "press_cost": round(press_cost, 2),
        "conversion_cost": round(conversion_cost, 2),
        "total_cost": round(total_cost, 2),
    }
