from typing import Any, Dict, Optional

from backend.logic.cost_engine import calculate_hpdc_cost

ALLOY_LABELS = {
    "Aluminum_A380": "Aluminum A380",
    "Aluminum_ADC12": "Aluminum ADC12",
    "Aluminum_A356": "Aluminum A356",
    "Aluminum_6061": "Aluminum 6061",
    "Zinc_ZD3": "Zinc ZD3 / Zamak 3",
    "Zinc_Zamak5": "Zinc Zamak 5",
    "Magnesium_AZ91D": "Magnesium AZ91D",
    "Magnesium_AM60B": "Magnesium AM60B",
    "Copper_Brass": "Copper / Brass casting alloy",
    "Steel_Stainless": "Steel / Stainless reference",
}


def infer_manufacturing_inputs(
    traits: Dict[str, Any],
    detected_metal: Optional[str],
    requested_metal: Optional[str],
    requested_volume: Optional[int],
    requested_sliders: Optional[int],
    requested_port_cost: Optional[float],
    location_name: str,
) -> Dict[str, Any]:

    # ---------------------------------------------------------
    # ✅ CAD GEOMETRY (SOURCE OF TRUTH)
    # ---------------------------------------------------------
    volume_mm3 = float(traits.get("volume") or 0)
    surface_mm2 = float(traits.get("surface_area") or 0)

    dx = float(traits.get("DX") or 0)
    dy = float(traits.get("DY") or 0)
    dz = float(traits.get("DZ") or 0)

    topology = traits.get("topology", {}) or {}
    faces = int(topology.get("faces") or 0)

    volume_cm3 = volume_mm3 / 1000.0 if volume_mm3 else 0

    # ---------------------------------------------------------
    # ✅ ALLOY
    # ---------------------------------------------------------
    alloy = requested_metal or detected_metal or "Aluminum_ADC12"

    # ---------------------------------------------------------
    # ✅ ANNUAL VOLUME
    # ---------------------------------------------------------
    if requested_volume:
        annual_volume = max(1, int(requested_volume))
    elif dx * dy < 2_500 and volume_cm3 < 20:
        annual_volume = 50_000
    elif dx * dy < 20_000 and volume_cm3 < 250:
        annual_volume = 20_000
    else:
        annual_volume = 5_000

    # ---------------------------------------------------------
    # ✅ SLIDERS
    # ---------------------------------------------------------
    if requested_sliders is not None:
        sliders = max(0, int(requested_sliders))
    else:
        slider_score = 0
        aspect_ratio = max(dx, dy, dz) / max(min(dx, dy, dz), 1)
        if aspect_ratio > 4:
            slider_score += 1
        if faces > 300:
            slider_score += 1
        if dx * dy > 35_000:
            slider_score += 1
        sliders = min(3, slider_score)

    # ---------------------------------------------------------
    # ✅ HPDC COST ENGINE (THIS IS THE FIX)
    # ---------------------------------------------------------
    cost = calculate_hpdc_cost(
        cad_traits={
            "volume_mm3": volume_mm3,
            "surface_area_mm2": surface_mm2,
            "DX": dx,
            "DY": dy,
            "DZ": dz,
        },
        alloy=alloy,
        material_price_per_kg=212.30,
        press_rate_per_mm2=0.25,
        conversion_rate_per_kg=45.0,
    )

    # ---------------------------------------------------------
    # ✅ RETURN ONLY HPDC VALUES (NO CAD LEAKAGE)
    # ---------------------------------------------------------
    return {
        "mode": "HPDC_COSTING",

        "alloy": alloy,
        "annual_volume": annual_volume,
        "sliders": sliders,
        "location": location_name,

        # ✅ WHAT UI MUST SHOW
        "weight": {
            "net_kg": cost["net_weight_kg"],
            "gross_kg": cost["gross_weight_kg"],
        },

        "areas": {
            "projected_mm2": cost["effective_projected_area_mm2"],
            "surface_mm2": cost["effective_surface_area_mm2"],
        },

        "costing": {
            "material_cost": cost["material_cost"],
            "press_cost": cost["press_cost"],
            "conversion_cost": cost["conversion_cost"],
            "total_cost": cost["total_cost"],
        },

        # Optional transparency (can hide later)
        "debug": {
            "cad_volume_cm3": round(volume_cm3, 2),
            "cad_surface_mm2": round(surface_mm2, 0),
        },
    }
