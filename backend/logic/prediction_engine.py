from typing import Any, Dict, Optional


ALLOY_LABELS = {
    "Aluminum_A380": "Aluminum A380",
    "Zinc_ZD3": "Zinc ZD3 / Zamak",
    "Magnesium_AZ91D": "Magnesium AZ91D",
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
    dimensions = traits.get("dimensions", {}) or {}
    volume_mm3 = float(traits.get("volume") or 0)
    surface_mm2 = float(traits.get("surface_area") or 0)
    projected_mm2 = float(traits.get("projected_area") or 0)
    topology = traits.get("topology", {}) or {}
    faces = int(topology.get("faces") or 0)

    dims = [float(dimensions.get(axis) or 0) for axis in ("x", "y", "z")]
    max_dim = max(dims) if dims else 0
    min_dim = min([dim for dim in dims if dim > 0], default=0)
    aspect_ratio = round(max_dim / min_dim, 2) if min_dim else 1.0
    volume_cm3 = volume_mm3 / 1000

    alloy = requested_metal or detected_metal or "Aluminum_A380"
    alloy_reason = (
        "Read from CAD metadata."
        if detected_metal
        else "Defaulted to Aluminum A380 because CAD metadata did not specify alloy."
    )
    if requested_metal:
        alloy_reason = "User override selected."

    if requested_volume:
        annual_volume = max(1, int(requested_volume))
        volume_reason = "User override selected."
    elif projected_mm2 < 2_500 and volume_cm3 < 20:
        annual_volume = 50_000
        volume_reason = "Small projected area and low volume suggest high-volume production."
    elif projected_mm2 < 20_000 and volume_cm3 < 250:
        annual_volume = 20_000
        volume_reason = "Medium casting envelope suggests a standard annual production batch."
    else:
        annual_volume = 5_000
        volume_reason = "Large projected area or volume suggests lower annual demand and higher tooling amortization."

    if requested_sliders is not None:
        sliders = max(0, int(requested_sliders))
        slider_reason = "User override selected."
    else:
        slider_score = 0
        if aspect_ratio > 4:
            slider_score += 1
        if faces > 300:
            slider_score += 1
        if projected_mm2 > 35_000:
            slider_score += 1
        sliders = min(3, slider_score)
        slider_reason = "Estimated from aspect ratio, projected area, and topology complexity."

    if requested_port_cost is not None:
        port_cost = max(0.0, float(requested_port_cost))
        port_reason = "User override selected."
    else:
        finishing_factor = 0.12
        if surface_mm2 > 200_000:
            finishing_factor += 0.2
        if faces > 500:
            finishing_factor += 0.15
        port_cost = round(finishing_factor + sliders * 0.12, 2)
        port_reason = "Estimated from surface area, topology complexity, and slider count."

    confidence = 0.74
    if detected_metal:
        confidence += 0.08
    if faces > 0:
        confidence += 0.06
    if requested_metal or requested_volume or requested_sliders is not None:
        confidence += 0.04
    confidence = min(round(confidence, 2), 0.92)

    return {
        "mode": "CAD_ASSISTED_INFERENCE",
        "audience_summary": (
            f"The system read the CAD geometry, selected {ALLOY_LABELS.get(alloy, alloy)}, "
            f"assumed {annual_volume:,} pieces/year, and estimated {sliders} die slider(s)."
        ),
        "alloy": alloy,
        "annual_volume": annual_volume,
        "sliders": sliders,
        "port_cost": port_cost,
        "confidence": confidence,
        "location": location_name,
        "signals": {
            "volume_cm3": round(volume_cm3, 2),
            "projected_area_mm2": round(projected_mm2, 2),
            "surface_area_cm2": round(surface_mm2 / 100, 2),
            "max_dimension_mm": round(max_dim, 2),
            "aspect_ratio": aspect_ratio,
            "faces": faces,
        },
        "decisions": [
            {"label": "Alloy", "value": ALLOY_LABELS.get(alloy, alloy), "reason": alloy_reason},
            {"label": "Pieces/year", "value": f"{annual_volume:,}", "reason": volume_reason},
            {"label": "Die sliders", "value": str(sliders), "reason": slider_reason},
            {"label": "Port / finishing", "value": f"${port_cost:.2f} per part", "reason": port_reason},
        ],
        "open_data_sources": [
            "OpenStreetMap-style geodata for plant hub coordinates.",
            "Open exchange-rate feed for USD/INR conversion when available.",
            "Metalprice API when the account plan exposes live alloy symbols; otherwise clearly marked reference pricing.",
        ],
    }
