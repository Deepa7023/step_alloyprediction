"""
HPDC COST ENGINE — Excel / Plant-Normalized Costing (FINAL)

This model intentionally matches OEM Excel-style "normal cost" values.
It does NOT try to infer physics-perfect costs.

Principles:
- CAD geometry = design truth
- Excel cost = calibrated manufacturing truth
- Prices are INR-based (NO USD, NO FX here)
"""

from typing import Dict

# ---------------------------------------------------
# Alloy reference densities (g/cm³)
# Used only to compute CAD solid reference weight
# ---------------------------------------------------
ALLOY_DENSITY = {
    "Aluminum_A380": 2.70,
    "Aluminum_ADC12": 2.70,
    "Aluminum_A356": 2.68,
    "Zinc_ZD3": 6.60,
    "Magnesium_AZ91D": 1.81,
}

# ---------------------------------------------------
# EXCEL-CALIBRATED NORMALIZATION FACTORS
# ---------------------------------------------------

# CAD solid → effective casting metal
# 4.7 kg CAD ≈ 1.9 kg Excel → ~0.40
CASTING_UTILIZATION_FACTOR = 0.40

# Gross weight allowance (runners + overflow)
GROSS_WEIGHT_FACTOR = 1.10

# Press-effective projected area
# Excel press sizing implies ~45–50% of envelope
PROJECTED_AREA_UTILIZATION = 0.48

# Surface area used only for finishing
SURFACE_AREA_UTILIZATION = 0.70

# Final price normalization
# Brings theoretical cost down to Excel “normal cost”
EXCEL_COST_CALIBRATION_FACTOR = 0.50


# ===================================================
# GEOMETRY → EXCEL-STYLE NORMALIZATION
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
    # 2. EXCEL NET WEIGHT
    # -----------------------------------------------
    net_weight_kg = cad_weight_kg * CASTING_UTILIZATION_FACTOR

    # -----------------------------------------------
    # 3. EXCEL GROSS WEIGHT
    # -----------------------------------------------
    gross_weight_kg = net_weight_kg * GROSS_WEIGHT_FACTOR

    # -----------------------------------------------
    # 4. EXCEL PROJECTED AREA (PRESS EFFECTIVE)
    # -----------------------------------------------
    envelope_projected_area_mm2 = dx * dy
    effective_projected_area_mm2 = (
        envelope_projected_area_mm2 * PROJECTED_AREA_UTILIZATION
    )

    # -----------------------------------------------
    # 5. EFFECTIVE SURFACE AREA (SECONDARY)
    # -----------------------------------------------
    effective_surface_area_mm2 = (
        cad_surface_area_mm2 * SURFACE_AREA_UTILIZATION
    )

    return {
        # CAD transparency (optional display)
        "cad_weight_kg": round(cad_weight_kg, 3),
        "cad_projected_area_mm2": round(envelope_projected_area_mm2, 0),
        "cad_surface_area_mm2": round(cad_surface_area_mm2, 0),

        # Excel-style values
        "net_weight_kg": round(net_weight_kg, 3),
        "gross_weight_kg": round(gross_weight_kg, 3),
        "effective_projected_area_mm2": round(effective_projected_area_mm2, 0),
        "effective_surface_area_mm2": round(effective_surface_area_mm2, 0),
    }


# ===================================================
# FINAL PART COST — NORMAL (NON-AGENT)
# ===================================================
def calculate_hpdc_cost(
    cad_traits: Dict,
    alloy: str,
    material_price_per_kg: float,   # INR / kg
    press_cost_per_mm2: float,       # INR / mm²
    conversion_cost_per_kg: float,   # INR / kg
) -> Dict[str, float]:

    geom = derive_costing_geometry(
        cad_volume_mm3=cad_traits["volume_mm3"],
        cad_surface_area_mm2=cad_traits["surface_area_mm2"],
        dx=cad_traits["DX"],
        dy=cad_traits["DY"],
        dz=cad_traits["DZ"],
        alloy=alloy,
    )

    # -----------------------------------------------
    # THEORETICAL COST
    # -----------------------------------------------
    material_cost = geom["gross_weight_kg"] * material_price_per_kg
    press_cost = geom["effective_projected_area_mm2"] * press_cost_per_mm2
    conversion_cost = geom["net_weight_kg"] * conversion_cost_per_kg

    raw_total_cost = material_cost + press_cost + conversion_cost

    # -----------------------------------------------
    # EXCEL NORMALIZATION (FINAL FIX)
    # -----------------------------------------------
    total_cost = raw_total_cost * EXCEL_COST_CALIBRATION_FACTOR

    return {
        **geom,
        "material_cost": round(material_cost, 2),
        "press_cost": round(press_cost, 2),
        "conversion_cost": round(conversion_cost, 2),
        "raw_total_cost": round(raw_total_cost, 2),
        "total_cost": round(total_cost, 2),
    }
``
