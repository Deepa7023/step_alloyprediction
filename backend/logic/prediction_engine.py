from typing import Any, Dict, Optional

# ✅ IMPORT THE COST ENGINE (THIS WAS MISSING BEFORE)
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
    # ✅ CAD TRAITS (PURE GEOMETRY – DO NOT MODIFY)
    # ---------------------------------------------------------
    volume_mm3 = float(traits.get("volume_mm3") or traits.get("volume") or 0)
    surface_mm2 = float(traits.get("surface_area_mm2") or traits.get("surface_area") or 0)

    dx = float(traits.get("DX") or 0)
    dy = float(traits.get("DY") or 0)
    dz = float(traits.get("DZ") or 0)

    topology = traits.get("topology", {}) or {}
    faces = int(topology.get("faces") or 0)

    volume_cm3 = volume_mm3 / 1000 if volume_mm3 else 0

    # ---------------------------------------------------------
    # ✅ ALLOY DECISION
    # ---------------------------------------------------------
    alloy = requested_metal or detected_metal or "Aluminum_A380"
    alloy_reason = (
        "Read from CAD metadata."
        if detected_metal
        else "Defaulted to Aluminum A380 because CAD metadata did not specify alloy."
    )
    if requested_metal:
        alloy_reason = "User override selected."

    # ---------------------------------------------------------
    # ✅ ANNUAL VOLUME LOGIC (UNCHANGED)
    # ---------------------------------------------------------
    if requested_volume:
        annual_volume = max(1, int(requested_volume))
        volume_reason = "User override selected."
    elif dx * dy < 2_500 and volume_cm3 < 20:
        annual_volume = 50_000
        volume_reason = "Small casting suggests high-volume production."
    elif dx * dy < 20_000 and volume_cm3 < 250:
        annual_volume = 20_000
        volume_reason = "Medium casting suggests standard production batch."
    else:
        annual_volume = 5_000
        volume_reason = "Large casting suggests lower production volume."

    # ---------------------------------------------------------
    # ✅ SLIDER ESTIMATION (UNCHANGED)
    # ---------------------------------------------------------
    if requested_sliders is not None:
        sliders = max(0, int(requested_sliders))
        slider_reason = "User override selected."
    else:
        slider_score = 0
        aspect_ratio = max(dx, dy, dz) / max(min(dx, dy, dz), 1)
        if aspect_ratio > 4:
            slider_score += 1
        if faces > 300:
            slider_score += 1
        if (dx * dy) > 35_000:
            slider_score += 1
        sliders = min(3, slider_score)
        slider_reason = "Estimated from geometry complexity."

    # ---------------------------------------------------------
    # ✅ PORT / FINISHING COST LOGIC (UNCHANGED)
    # ---------------------------------------------------------
    if requested_port_cost is not None:
        port_cost = max(0.0, float(requested_port_cost))
        port_reason = "User override selected."
    else:
        finishing_factor = 0.12
        if surface_mm2 > 200_000:
            finishing_factor += 0.20
        if faces > 500:
            finishing_factor += 0.15
        port_cost = round(finishing_factor + sliders * 0.12, 2)
        port_reason = "Estimated from surface finish and complexity."

    # ---------------------------------------------------------
    # ✅ THIS IS THE CRITICAL FIX: CALL COST ENGINE
    # ---------------------------------------------------------
    cost_result = calculate_hpdc_cost(
        cad_traits={
            "volume_mm3": volume_mm3,
            "surface_area_mm2": surface_mm2,
            "DX": dx,
            "DY": dy,
            "DZ": dz,
        },
        alloy=alloy,
        material_price_per_kg=212.30,   # example material rate (can be made dynamic)
        press_rate_per_mm2=0.25,         # example press rate
        conversion_rate_per_kg=45.0      # example conversion cost
    )

    # ---------------------------------------------------------
    # ✅ CONFIDENCE SCORE (UNCHANGED)
    # ---------------------------------------------------------
    confidence = 0.74
    if detected_metal:
        confidence += 0.08
    if faces > 0:
        confidence += 0.06
    if requested_metal or requested_volume or requested_sliders is not None:
        confidence += 0.04
    confidence = min(round(confidence, 2), 0.92)

    # ---------------------------------------------------------
    # ✅ FINAL RESPONSE (CAD + HPDC REALITY)
    # ---------------------------------------------------------
    return {
        "mode": "CAD_ASSISTED_INFERENCE",

        "audience_summary": (
            f"The system read the CAD geometry, applied HPDC manufacturing "
            f"adjustments (porosity, thin walls, trimmed runners), selected "
            f"{ALLOY_LABELS.get(alloy, alloy)}, assumed {annual_volume:,} parts/year "
            f"with {sliders} die slider(s)."
        ),

        "alloy": alloy,
        "annual_volume": annual_volume,
        "sliders": sliders,
        "port_cost": port_cost,
        "confidence": confidence,
        "location": location_name,

        # ✅ CAD GEOMETRY (REFERENCE)
        "cad_geometry": {
            "DX_mm": round(dx, 2),
            "DY_mm": round(dy, 2),
            "DZ_mm": round(dz, 2),
            "volume_cm3": round(volume_cm3, 2),
            "surface_area_mm2": round(surface_mm2, 0),
        },

        # ✅ HPDC COSTING GEOMETRY (USED FOR PRICE)
        "hpdc_geometry": {
            "net_weight_kg": cost_result["net_weight_kg"],
            "gross_weight_kg": cost_result["gross_weight_kg"],
            "effective_projected_area_mm2": cost_result["effective_projected_area_mm2"],
            "effective_surface_area_mm2": cost_result["effective_surface_area_mm2"],
        },

        # ✅ COST RESULT
        "costing": {
            "material_cost": cost_result["material_cost"],
            "press_cost": cost_result["press_cost"],
            "conversion_cost": cost_result["conversion_cost"],
            "total_cost": cost_result["total_cost"],
        },

        "decisions": [
            {"label": "Alloy", "value": ALLOY_LABELS.get(alloy, alloy), "reason": alloy_reason},
            {"label": "Pieces/year", "value": f"{annual_volume:,}", "reason": volume_reason},
            {"label": "Die sliders", "value": str(sliders), "reason": slider_reason},
            {"label": "Port / finishing", "value": f"${port_cost:.2f} per part", "reason": port_reason},
        ],
    }
