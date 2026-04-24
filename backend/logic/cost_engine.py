"""
HPDC COST ENGINE — Excel-Matching Logic (FINAL)

This model is intentionally aligned with Excel / plant reality.
It does NOT try to derive cost from CAD solid volume.

Key idea:
Excel weight ≈ bounding box shell weight
"""

from typing import Dict

# ---------------------------------------------------
# Alloy densities (g/cm³)
# ---------------------------------------------------
ALLOY_DENSITY = {
    "Aluminum_A380": 2.70,
    "Aluminum_ADC12": 2.70,
    "Aluminum_A356": 2.68,
}

# ---------------------------------------------------
# EXCEL-STYLE ASSUMPTIONS
# ---------------------------------------------------

# Typical HPDC aluminum housing wall thickness (mm)
ASSUMED_WALL_THICKNESS_MM = 2.8

# Grossing factor (runner + overflow)
GROSS_WEIGHT_FACTOR = 1.10

# Projected area utilization (press effective)
PROJECTED_AREA_UTILIZATION = 0.48

# Surface area utilization (costing only)
SURFACE_AREA_UTILIZATION = 0.82


# ===================================================
# GEOMETRY → EXCEL STYLE COSTING
# ===================================================
def derive_costing_geometry(
    cad_volume_mm3: float,           # kept only for reference
    cad_surface_area_mm2: float,
    dx: float,
    dy: float,
    dz: float,
    alloy: str,
) -> Dict[str, float]:

    density = ALLOY_DENSITY.get(alloy, 2.7)

    # ------------------------------------------------
    # 1. CAD SOLID WEIGHT (REFERENCE ONLY)
    # ------------------------------------------------
    cad_weight_kg = (cad_volume_mm3 / 1e6) * density

    # ------------------------------------------------
    # 2. EXCEL NET WEIGHT (KEY FIX ✅)
    # ------------------------------------------------
    # Envelope volume × shell thickness
    envelope_volume_mm3 = 2 * (
        dx * dy + dy * dz + dx * dz
    ) * ASSUMED_WALL_THICKNESS_MM

    net_weight_kg = (envelope_volume_mm3 / 1e6) * density

    # ------------------------------------------------
    # 3. GROSS WEIGHT
    # ------------------------------------------------
    gross_weight_kg = net_weight_kg * GROSS_WEIGHT_FACTOR

    # ------------------------------------------------
    # 4. PROJECTED AREA
    # ------------------------------------------------
    envelope_projected_area_mm2 = dx * dy
    effective_projected_area_mm2 = (
        envelope_projected_area_mm2 * PROJECTED_AREA_UTILIZATION
    )

    # ------------------------------------------------
    # 5. SURFACE AREAS
    # ------------------------------------------------
    real_surface_area_mm2 = cad_surface_area_mm2
    effective_surface_area_mm2 = cad_surface_area_mm2 * SURFACE_AREA_UTILIZATION

    return {
        # Reference
        "cad_weight_kg": round(cad_weight_kg, 3),

        # ✅ Excel-style weights
        "net_weight_kg": round(net_weight_kg, 3),
        "gross_weight_kg": round(gross_weight_kg, 3),

        # ✅ Areas
        "real_surface_area_mm2": round(real_surface_area_mm2, 2),
        "effective_surface_area_mm2": round(effective_surface_area_mm2, 2),
        "effective_projected_area_mm2": round(effective_projected_area_mm2, 2),
    }


# ===================================================
# FINAL COST (NORMAL / PLANT)
# ===================================================
def calculate_hpdc_cost(
    cad_traits: Dict,
    alloy: str,
    material_price_per_kg: float,   # INR/kg
    press_cost_per_mm2: float,       # INR/mm²
    conversion_cost_per_kg: float,   # INR/kg
) -> Dict[str, float]:

    geom = derive_costing_geometry(
        cad_volume_mm3=cad_traits["volume_mm3"],
        cad_surface_area_mm2=cad_traits["surface_area_mm2"],
        dx=cad_traits["DX"],
        dy=cad_traits["DY"],
        dz=cad_traits["DZ"],
        alloy=alloy,
    )

    material_cost = geom["gross_weight_kg"] * material_price_per_kg
    press_cost = geom["effective_projected_area_mm2"] * press_cost_per_mm2
    conversion_cost = geom["net_weight_kg"] * conversion_cost_per_kg

    total_cost = material_cost + press_cost + conversion_cost

    return {
        **geom,
        "material_cost": round(material_cost, 2),
        "press_cost": round(press_cost, 2),
        "conversion_cost": round(conversion_cost, 2),
        "total_cost": round(total_cost, 2),
    }
