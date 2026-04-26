from typing import Dict


# ============================================================
# MATERIAL DATA
# ============================================================

ALLOY_DENSITY_G_PER_CM3 = {
    "EN AC-46000 D-F": 2.70,
    "ADC12": 2.70,
}


# ============================================================
# EXCEL-CALIBRATED CONSTANTS
# ============================================================

ASSUMED_WALL_THICKNESS_MM = 2.8
GROSS_WEIGHT_FACTOR = 1.10
PROJECTED_AREA_FACTOR = 0.48
SURFACE_AREA_UTILIZATION = 0.82


# ============================================================
# UPDATED COST RATES (NEAR-EXCEL, CLEAN)
# ============================================================

# ✅ Fixed alloy price
MATERIAL_RATE_INR_PER_KG = 212.78

PRESS_RATE_INR_PER_MM2 = 0.003

# ✅ Simplified but realistic conversion buckets (per part)
CONVERSION_BREAKUP = {
    "casting": 42.0,
    "finishing": 18.0,
    "inspection": 8.0,
}

# Light plant-level adjustments
REJECTION_RATE = 0.03
OVERHEAD_PERCENT = 0.10
PROFIT_PERCENT = 0.07


# ============================================================
# CORE: EXCEL STYLE WEIGHTS
# ============================================================

def _derive_excel_weights(
    dx_mm: float,
    dy_mm: float,
    dz_mm: float,
    density_g_per_cm3: float,
) -> Dict[str, float]:

    envelope_surface_mm2 = 2 * (
        dx_mm * dy_mm +
        dy_mm * dz_mm +
        dx_mm * dz_mm
    )

    envelope_volume_mm3 = envelope_surface_mm2 * ASSUMED_WALL_THICKNESS_MM

    net_weight_kg = (envelope_volume_mm3 / 1000.0) * density_g_per_cm3 / 1000.0
    gross_weight_kg = net_weight_kg * GROSS_WEIGHT_FACTOR

    return {
        "net_weight_kg": round(net_weight_kg, 3),
        "gross_weight_kg": round(gross_weight_kg, 3),
    }


# ============================================================
# FINAL EXCEL COST FUNCTION (UPDATED, SAME STRUCTURE)
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

    # --- Effective projected area ---
    effective_projected_area_mm2 = dx * dy * PROJECTED_AREA_FACTOR

    # --- Effective surface (info only) ---
    effective_surface_area_mm2 = real_surface_area_mm2 * SURFACE_AREA_UTILIZATION

    # ========================================================
    # COST CALCULATION (UPDATED)
    # ========================================================

    # Material
    material_cost = gross_weight_kg * MATERIAL_RATE_INR_PER_KG

    # Press
    press_cost = effective_projected_area_mm2 * PRESS_RATE_INR_PER_MM2

    # Conversion (grouped, not per kg)
    conversion_cost = sum(CONVERSION_BREAKUP.values())

    # Rejection (light)
    rejection_cost = material_cost * REJECTION_RATE

    # Subtotal
    subtotal = material_cost + press_cost + conversion_cost + rejection_cost

    # Overheads & Profit
    overhead_cost = subtotal * OVERHEAD_PERCENT
    profit_cost = subtotal * PROFIT_PERCENT

    total_cost = subtotal + overhead_cost + profit_cost

    return {
        # ✅ Excel-style outputs
        "net_weight_kg": net_weight_kg,
        "gross_weight_kg": gross_weight_kg,
        "part_cost_inr": round(total_cost, 2),

        # ✅ Geometry transparency
        "real_surface_area_mm2": round(real_surface_area_mm2, 2),
        "effective_surface_area_mm2": round(effective_surface_area_mm2, 2),
        "effective_projected_area_mm2": round(effective_projected_area_mm2, 2),

        # ✅ Cost breakdown (clean but useful)
        "cost_breakup": {
            "material_cost_inr": round(material_cost, 2),
            "press_cost_inr": round(press_cost, 2),
            "conversion_cost_inr": round(conversion_cost, 2),
            "rejection_cost_inr": round(rejection_cost, 2),
            "overhead_cost_inr": round(overhead_cost, 2),
            "profit_cost_inr": round(profit_cost, 2),
        }
    }
