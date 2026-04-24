"""
HPDC COST ENGINE — Excel / Plant-Normal (NON-AGENT)

This file is reverse-engineered from:
HPDC Comparison 1 - Copy.xlsx

It intentionally reproduces:
- Net Weight (Kg)
- Gross Weight (Kg)
- Part Cost (INR)

Important:
- CAD solid volume is NOT used for weight
- Weight uses bounding-box shell (Excel logic)
- All prices are INR-based
- Agent logic is intentionally excluded
"""

from typing import Dict


# ============================================================
# MATERIAL DATA
# ============================================================

ALLOY_DENSITY_G_PER_CM3 = {
    "EN AC-46000 D-F": 2.70,   # ADC12 / AlSi9Cu3 equivalent
    "ADC12": 2.70,
}


# ============================================================
# EXCEL-CALIBRATED CONSTANTS
# ============================================================

# HPDC shell thickness implicitly assumed in Excel (mm)
ASSUMED_WALL_THICKNESS_MM = 2.8

# Runner + overflow allowance
GROSS_WEIGHT_FACTOR = 1.10

# Press-effective projected area factor
PROJECTED_AREA_FACTOR = 0.48

# Surface area used only for costing (not display)
SURFACE_AREA_UTILIZATION = 0.82


# ============================================================
# PLANT-NORMAL COST RATES (INR)
# ============================================================

MATERIAL_RATE_INR_PER_KG = 380.0
PRESS_RATE_INR_PER_MM2 = 0.003
CONVERSION_RATE_INR_PER_KG = 55.0


# ============================================================
# CORE: EXCEL STYLE WEIGHTS
# ============================================================
def _derive_excel_weights(
    dx_mm: float,
    dy_mm: float,
    dz_mm: float,
    density_g_per_cm3: float,
) -> Dict[str, float]:

    # Bounding-box shell surface
    envelope_surface_mm2 = 2 * (
        dx_mm * dy_mm +
        dy_mm * dz_mm +
        dx_mm * dz_mm
    )

    # Shell volume ≈ surface × wall thickness
    envelope_volume_mm3 = envelope_surface_mm2 * ASSUMED_WALL_THICKNESS_MM

    # mm³ → cm³ → kg
    net_weight_kg = (envelope_volume_mm3 / 1000.0) * density_g_per_cm3 / 1000.0
    gross_weight_kg = net_weight_kg * GROSS_WEIGHT_FACTOR

    return {
        "net_weight_kg": round(net_weight_kg, 3),
        "gross_weight_kg": round(gross_weight_kg, 3),
    }


# ============================================================
# FINAL EXCEL COST FUNCTION (NON-AGENT)
# ============================================================
def calculate_excel_part_cost(
    cad_traits: Dict,
    alloy: str,
) -> Dict[str, float]:

    dx = cad_traits["DX"]
    dy = cad_traits["DY"]
    dz = cad_traits["DZ"]
    real_surface_area_mm2 = cad_traits["surface_area_mm2"]

    density = ALLOY_DENSITY_G_PER_CM3.get(alloy, 2.70)

    # --- Weights ---
    weights = _derive_excel_weights(dx, dy, dz, density)
    net_weight_kg = weights["net_weight_kg"]
    gross_weight_kg = weights["gross_weight_kg"]

    # --- Effective projected area for press sizing ---
    effective_projected_area_mm2 = dx * dy * PROJECTED_AREA_FACTOR

    # --- Effective surface (costing only) ---
    effective_surface_area_mm2 = real_surface_area_mm2 * SURFACE_AREA_UTILIZATION

    # --- Cost calculation (Excel normal) ---
    material_cost = gross_weight_kg * MATERIAL_RATE_INR_PER_KG
    press_cost = effective_projected_area_mm2 * PRESS_RATE_INR_PER_MM2
    conversion_cost = net_weight_kg * CONVERSION_RATE_INR_PER_KG

    total_cost = material_cost + press_cost + conversion_cost

    return {
        # ✅ Excel white-row outputs
        "net_weight_kg": net_weight_kg,
        "gross_weight_kg": gross_weight_kg,
        "part_cost_inr": round(total_cost, 2),

        # ✅ Geometry transparency
        "real_surface_area_mm2": round(real_surface_area_mm2, 2),
        "effective_surface_area_mm2": round(effective_surface_area_mm2, 2),
        "effective_projected_area_mm2": round(effective_projected_area_mm2, 2),

        # ✅ Optional cost breakdown (debug / audit)
        "cost_breakup": {
            "material_cost_inr": round(material_cost, 2),
            "press_cost_inr": round(press_cost, 2),
            "conversion_cost_inr": round(conversion_cost, 2),
        }
    }
