"""
HPDC COST ENGINE — Calibrated to Supplier / Excel Reality

Key principle:
- CAD geometry is DESIGN truth
- HPDC costing uses MANUFACTURING / COMMERCIAL truth

So we convert CAD values using calibrated utilization factors.
"""

from typing import Dict

# ------------------------------------------------------------------
# Alloy theoretical densities (g/cm³)
# ------------------------------------------------------------------
ALLOY_DENSITY = {
    "Aluminum_A380": 2.70,
    "Aluminum_ADC12": 2.70,
    "Aluminum_A356": 2.68,
    "Zinc_ZD3": 6.60,
    "Magnesium_AZ91D": 1.81,
}

# ------------------------------------------------------------------
# HPDC CALIBRATION FACTORS (CRITICAL)
# ------------------------------------------------------------------

# Main driver: how much of CAD solid volume is actually chargeable
# Thin / open housings typical range: 0.35 – 0.45
CASTING_UTILIZATION_FACTOR = 0.40   # ✅ calibrated to your Excel

# Extra metal: runners, overflow, burning loss
GROSS_WEIGHT_FACTOR = 1.10          # ✅ typical 8–12%

# Effective press-facing projected area (not full envelope)
PROJECTED_AREA_UTILIZATION = 0.55   # ✅ open / ribbed parts

# Surface area influence (finishing, trimming — secondary effect)
SURFACE_AREA_UTILIZATION = 0.70     # ✅ fillets & cosmetics ignored

# ============================================================
# GEOMETRY → COSTING NORMALIZATION
# ============================================================
def derive_costing_geometry(
    cad_volume_mm3: float,
    cad_surface_area_mm2: float,
    dx: float,
    dy: float,
    dz: float,
    alloy: str,
) -> Dict[str, float]:
    """
    Convert CAD geometry to HPDC-usable geometry.
    """

    # ------------------------------
    # 1. CAD SOLID WEIGHT (REFERENCE)
    # ------------------------------
    density = ALLOY_DENSITY.get(alloy, 2.70)
    cad_weight_kg = (cad_volume_mm3 / 1e6) * density

    # ------------------------------
    # 2. NET HPDC WEIGHT (KEY FIX ✅)
    # ------------------------------
    # Supplier reality: CAD solid volume is NOT fully filled
    net_hpdc_weight_kg = cad_weight_kg * CASTING_UTILIZATION_FACTOR

    # ------------------------------
    # 3. GROSS HPDC WEIGHT
    # ------------------------------
    gross_hpdc_weight_kg = net_hpdc_weight_kg * GROSS_WEIGHT_FACTOR

    # ------------------------------
    # 4. EFFECTIVE PROJECTED AREA
    # ------------------------------
    # Assume die opens along Z → face = DX × DY
    cad_die_face_area_mm2 = dx * dy
    effective_projected_area_mm2 = cad_die_face_area_mm2 * PROJECTED_AREA_UTILIZATION

    # ------------------------------
    # 5. EFFECTIVE SURFACE AREA
    # ------------------------------
    effective_surface_area_mm2 = cad_surface_area_mm2 * SURFACE_AREA_UTILIZATION

    return {
        # ---- CAD TRUTH (FOR TRANSPARENCY) ----
        "cad_weight_kg": round(cad_weight_kg, 2),
        "cad_surface_area_mm2": round(cad_surface_area_mm2, 0),
        "cad_projected_area_mm2": round(cad_die_face_area_mm2, 0),

        # ---- HPDC-REAL VALUES (USED FOR COST) ----
        "net_weight_kg": round(net_hpdc_weight_kg, 2),
        "gross_weight_kg": round(gross_hpdc_weight_kg, 2),
        "effective_projected_area_mm2": round(effective_projected_area_mm2, 0),
        "effective_surface_area_mm2": round(effective_surface_area_mm2, 0),
    }


# ============================================================
# FINAL COST CALCULATION
# ============================================================
def calculate_hpdc_cost(
    cad_traits: Dict,
    alloy: str,
    material_price_per_kg: float,
    press_rate_per_mm2: float,
    conversion_rate_per_kg: float,
) -> Dict[str, float]:
    """
    Final HPDC part cost using calibrated manufacturing reality.
    """

    geom = derive_costing_geometry(
        cad_volume_mm3=cad_traits["volume_mm3"],
        cad_surface_area_mm2=cad_traits["surface_area_mm2"],
        dx=cad_traits["DX"],
        dy=cad_traits["DY"],
        dz=cad_traits["DZ"],
        alloy=alloy,
    )

    # ------------------------------
    # COST BREAKDOWN
    # ------------------------------
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
