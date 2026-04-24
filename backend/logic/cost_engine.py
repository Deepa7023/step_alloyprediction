"""
HPDC COST ENGINE — Excel-Calibrated Manufacturing Reality

Key principles:
- CAD geometry = design truth
- HPDC costing uses effective casting geometry, not CAD solid
- Weight and area must be calibrated to supplier practice
"""

from typing import Dict

# ---------------------------------------------------
# Alloy densities (g/cm³)
# ---------------------------------------------------
ALLOY_DENSITY = {
    "Aluminum_A380": 2.70,
    "Aluminum_ADC12": 2.70,
    "Aluminum_A356": 2.68,
    "Zinc_ZD3": 6.60,
    "Magnesium_AZ91D": 1.81,
}

# ---------------------------------------------------
# HPDC CALIBRATION FACTORS (MATCH EXCEL)
# ---------------------------------------------------

# How much of CAD solid actually becomes casting metal
# Open housings / brackets dominate your Excel set
CASTING_SHELL_FACTOR = 0.75

# How much of that metal is chargeable after yield, trimming
CHARGEABLE_YIELD_FACTOR = 0.55

# Extra metal for runners + overflow
GROSS_WEIGHT_FACTOR = 1.10

# Effective press-facing projected area (not envelope)
PROJECTED_AREA_UTILIZATION = 0.48

# Effective surface for finishing
SURFACE_AREA_UTILIZATION = 0.70


# ===================================================
# GEOMETRY → HPDC NORMALIZATION
# ===================================================
def derive_costing_geometry(
    cad_volume_mm3: float,
    cad_surface_area_mm2: float,
    dx: float,
    dy: float,
    dz: float,
    alloy: str,
) -> Dict[str, float]:

    density = ALLOY_DENSITY.get(alloy, 2.70)

    # -----------------------------------------------
    # 1. CAD SOLID WEIGHT (REFERENCE ONLY)
    # -----------------------------------------------
    cad_weight_kg = (cad_volume_mm3 / 1e6) * density

    # -----------------------------------------------
    # 2. NET HPDC WEIGHT (EXCEL REALITY)
    # -----------------------------------------------
    net_hpdc_weight_kg = (
        cad_weight_kg
        * CASTING_SHELL_FACTOR
        * CHARGEABLE_YIELD_FACTOR
    )

    # -----------------------------------------------
    # 3. GROSS HPDC WEIGHT
    # -----------------------------------------------
    gross_hpdc_weight_kg = net_hpdc_weight_kg * GROSS_WEIGHT_FACTOR

    # -----------------------------------------------
    # 4. EFFECTIVE PROJECTED AREA
    # -----------------------------------------------
    cad_die_face_area_mm2 = dx * dy
    effective_projected_area_mm2 = (
        cad_die_face_area_mm2 * PROJECTED_AREA_UTILIZATION
    )

    # -----------------------------------------------
    # 5. EFFECTIVE SURFACE AREA
    # -----------------------------------------------
    effective_surface_area_mm2 = (
        cad_surface_area_mm2 * SURFACE_AREA_UTILIZATION
    )

    return {
        # CAD transparency
        "cad_weight_kg": round(cad_weight_kg, 3),
        "cad_projected_area_mm2": round(cad_die_face_area_mm2, 0),
        "cad_surface_area_mm2": round(cad_surface_area_mm2, 0),

        # HPDC-real geometry
        "net_weight_kg": round(net_hpdc_weight_kg, 3),
        "gross_weight_kg": round(gross_hpdc_weight_kg, 3),
        "effective_projected_area_mm2": round(effective_projected_area_mm2, 0),
        "effective_surface_area_mm2": round(effective_surface_area_mm2, 0),
    }


# ===================================================
# COST CALCULATION
# ===================================================
def calculate_hpdc_cost(
    cad_traits: Dict,
    alloy: str,
    material_price_per_kg: float,
    press_rate_per_mm2: float,
    conversion_rate_per_kg: float,
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
    press_cost = geom["effective_projected_area_mm2"] * press_rate_per_mm2
    conversion_cost = geom["net_weight_kg"] * conversion_rate_per_kg

    total_cost = material_cost + press_cost + conversion_cost

    return {
        **geom,
        "material_cost": round(material_cost, 2),
        "press_cost": round(press_cost, 2),
        "conversion_cost": round(conversion_cost, 2),
        "total_cost": round(total_cost, 2),
    }
``
