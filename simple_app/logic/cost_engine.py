METAL_PROPERTIES = {
    "Aluminum_A380": {
        "density": 0.00270,
        "price_per_kg": 2.85,
        "injection_pressure": 80,
        "volatility": 0.06,
        "flow_factor": 1.03,
        "solidification_factor": 1.00,
        "tool_wear_factor": 1.00,
        "yield_bias": 1.00,
    },
    "Aluminum_ADC12": {
        "density": 0.00272,
        "price_per_kg": 2.78,
        "injection_pressure": 78,
        "volatility": 0.06,
        "flow_factor": 1.02,
        "solidification_factor": 0.98,
        "tool_wear_factor": 0.95,
        "yield_bias": 0.98,
    },
    "Aluminum_A356": {
        "density": 0.00268,
        "price_per_kg": 3.05,
        "injection_pressure": 72,
        "volatility": 0.07,
        "flow_factor": 0.96,
        "solidification_factor": 1.04,
        "tool_wear_factor": 1.05,
        "yield_bias": 1.03,
    },
    "Aluminum_6061": {
        "density": 0.00270,
        "price_per_kg": 3.25,
        "injection_pressure": 70,
        "volatility": 0.07,
        "flow_factor": 0.94,
        "solidification_factor": 1.06,
        "tool_wear_factor": 1.08,
        "yield_bias": 1.05,
    },
    "Zinc_ZD3": {
        "density": 0.00660,
        "price_per_kg": 3.42,
        "injection_pressure": 30,
        "volatility": 0.05,
        "flow_factor": 1.10,
        "solidification_factor": 0.78,
        "tool_wear_factor": 0.72,
        "yield_bias": 0.88,
    },
    "Zinc_Zamak5": {
        "density": 0.00670,
        "price_per_kg": 3.55,
        "injection_pressure": 32,
        "volatility": 0.05,
        "flow_factor": 1.12,
        "solidification_factor": 0.80,
        "tool_wear_factor": 0.74,
        "yield_bias": 0.90,
    },
    "Magnesium_AZ91D": {
        "density": 0.00180,
        "price_per_kg": 4.65,
        "injection_pressure": 60,
        "volatility": 0.08,
        "flow_factor": 1.06,
        "solidification_factor": 0.90,
        "tool_wear_factor": 1.15,
        "yield_bias": 1.02,
    },
    "Magnesium_AM60B": {
        "density": 0.00179,
        "price_per_kg": 4.90,
        "injection_pressure": 58,
        "volatility": 0.08,
        "flow_factor": 1.05,
        "solidification_factor": 0.92,
        "tool_wear_factor": 1.12,
        "yield_bias": 1.02,
    },
    "Copper_Brass": {
        "density": 0.00850,
        "price_per_kg": 8.70,
        "injection_pressure": 95,
        "volatility": 0.09,
        "flow_factor": 0.90,
        "solidification_factor": 1.22,
        "tool_wear_factor": 1.35,
        "yield_bias": 1.10,
    },
    "Steel_Stainless": {
        "density": 0.00780,
        "price_per_kg": 2.15,
        "injection_pressure": 110,
        "volatility": 0.06,
        "flow_factor": 0.82,
        "solidification_factor": 1.35,
        "tool_wear_factor": 1.55,
        "yield_bias": 1.15,
    },
}

_MACHINE_RATES_INR = [
    {"limit": 250, "rate_inr": 1_400, "shot_capacity_kg": 1.5},
    {"limit": 500, "rate_inr": 2_800, "shot_capacity_kg": 3.5},
    {"limit": 850, "rate_inr": 5_500, "shot_capacity_kg": 7.0},
    {"limit": 1250, "rate_inr": 9_000, "shot_capacity_kg": 12.0},
    {"limit": 2000, "rate_inr": 15_000, "shot_capacity_kg": 20.0},
    {"limit": 4000, "rate_inr": 30_000, "shot_capacity_kg": 40.0},
]

QUOTE_CONSTANTS = {
    "base_runner_overflow_percent": 4.5,
    "base_scrap_percent": 2.5,
    "base_melting_process_loss_percent": 6.0,
    "rnd_percent": 4.0,
    "sa_percent": 6.1,
    "ebit_percent": 10.0,
    "consumable_inr": 8.0,
    "melting_cost_inr_per_kg": 14.0,
    "shot_blast_inr_per_kg": 7.0,
    "cleaning_washing_inr": 5.0,
    "operator_labour_inr_per_hour": 600,
    "manual_labour_inr_per_hour": 100,
    "fettling_time_minutes": 5.0,
    "freight_rate_inr_per_kg": 0.0,
    "metal_price_inr_per_kg": 212.80,
    "credit_cost_inr": 0.0,
    "bop_percent": 1.2,
    "job_work_base_inr": 0.0,
    "xray_rate_inr_per_kg": 18.0,
    "vmc_rate_inr_per_kg": 26.0,
    "tool_maintenance_percent": 1.2,
    "qa_rate_inr_per_kg": 6.0,
    "compression_test_rate_inr_per_kg": 4.0,
    "icc_percent": 0.35,
    "insurance_percent": 0.50,
    "acd_backup_percent": 0.30,
    "licence_cost_percent": 0.15,
    "rejection_percent": 0.0,
    "yoy_reduction_percent": 0.75,
    "packing_rate_inr_per_kg": 4.5,
}

TOOLING_ROWS_58_60 = [
    {"row": 58, "label": "HPDC Die cost", "quantity": 1, "unit": "set"},
    {"row": 59, "label": "Trimming Die cost", "quantity": 1, "unit": "set"},
    {"row": 60, "label": "Fixture Cost", "quantity": 2, "unit": "set"},
]

PROGRAM_LIFE_YEARS = 3
INR_RATE = 83.5


def _die_life(metal: str) -> int:
    if "Zinc" in metal:
        return 500_000
    if "Magnesium" in metal:
        return 80_000
    if "Copper" in metal:
        return 30_000
    if "Steel" in metal:
        return 20_000
    if "ADC12" in metal:
        return 120_000
    return 100_000


def _row(row, section, label, value=0.0, unit="INR", note="", code=""):
    return {
        "row": row,
        "section": section,
        "label": label,
        "code": code,
        "value": round(float(value or 0), 2),
        "unit": unit,
        "note": note,
    }


def _clamp(value, low, high):
    return max(low, min(high, value))


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_dimensions(dimensions):
    values = []
    for value in (dimensions or {}).values():
        parsed = _safe_float(value, 0.0)
        if parsed > 0:
            values.append(parsed)
    values.sort(reverse=True)
    while len(values) < 3:
        values.append(0.0)
    return {"x": values[0], "y": values[1], "z": values[2]}


def _topology_inputs(traits):
    topology = traits.get("topology") or {}
    validation = traits.get("validation") or {}
    return {
        "faces": max(0, _safe_int(topology.get("faces"), 0)),
        "edges": max(0, _safe_int(topology.get("edges"), 0)),
        "vertices": max(0, _safe_int(topology.get("vertices"), 0)),
        "solids": max(1, _safe_int(topology.get("solids"), 1)),
        "integrity_score": _clamp(_safe_float(validation.get("integrity_score"), 75.0), 20.0, 100.0),
        "is_manifold": bool(validation.get("is_manifold", False)),
    }


def _geometry_inputs(traits):
    dimensions = _normalize_dimensions(traits.get("dimensions"))
    max_dim = dimensions["x"]
    mid_dim = dimensions["y"]
    min_dim = dimensions["z"]

    bbox_volume = max(max_dim * mid_dim * min_dim, 0.0)
    volume = _safe_float(traits.get("volume"), 0.0)
    if volume <= 0 and bbox_volume > 0:
        volume = bbox_volume * 0.35
    if bbox_volume > 0:
        volume = min(volume, bbox_volume * 1.02)
    volume = max(volume, 0.001)

    fallback_area = max(max_dim * mid_dim, mid_dim * min_dim, max_dim * min_dim, 1.0)
    projected_area = max(_safe_float(traits.get("projected_area"), 0.0), fallback_area if fallback_area > 0 else 1.0)
    if fallback_area > 0:
        projected_area = min(projected_area, fallback_area * 1.08)

    surface_area = max(_safe_float(traits.get("surface_area"), 0.0), 1.0)
    true_surface_factor = _clamp(surface_area / max(2.0 * projected_area, 1.0), 1.0, 4.5)
    bbox_fill_ratio = _clamp(volume / max(bbox_volume, 1.0), 0.05, 1.0) if bbox_volume > 0 else 0.35
    max_allowed_thickness = max(min_dim, 0.6) if min_dim > 0 else 30.0
    mean_thickness = _clamp(volume / max(surface_area / 2.0, 1.0), 0.4, max_allowed_thickness)
    flow_length_ratio = max_dim / max(mean_thickness, 0.5)
    aspect_ratio = max_dim / max(min_dim, 1.0)
    compactness = _clamp((volume ** (2.0 / 3.0)) / max(surface_area, 1.0), 0.01, 1.0)

    return {
        "dimensions": dimensions,
        "volume": volume,
        "projected_area": projected_area,
        "surface_area": surface_area,
        "max_dim": max_dim,
        "mid_dim": mid_dim,
        "min_dim": min_dim,
        "bbox_volume": bbox_volume,
        "bbox_fill_ratio": bbox_fill_ratio,
        "mean_thickness_mm": mean_thickness,
        "true_surface_factor": true_surface_factor,
        "flow_length_ratio": flow_length_ratio,
        "aspect_ratio": aspect_ratio,
        "compactness": compactness,
    }


def _complexity_factors(geometry, topology, slider_count):
    topology_density = topology["faces"] / max(geometry["surface_area"] / 100.0, 1.0)
    fine_feature_factor = _clamp(
        1.0
        + max(geometry["flow_length_ratio"] - 18.0, 0.0) * 0.006
        + max(geometry["true_surface_factor"] - 1.3, 0.0) * 0.12
        + max(geometry["aspect_ratio"] - 3.0, 0.0) * 0.015
        + max(topology_density - 2.5, 0.0) * 0.015
        + slider_count * 0.04,
        1.0,
        1.45,
    )
    quality_risk_factor = _clamp(
        1.0
        + max(70.0 - topology["integrity_score"], 0.0) * 0.0035
        + (0.05 if not topology["is_manifold"] else 0.0)
        + max(0.42 - geometry["bbox_fill_ratio"], 0.0) * 0.25,
        1.0,
        1.35,
    )
    return {
        "fine_feature_factor": fine_feature_factor,
        "quality_risk_factor": quality_risk_factor,
        "overall_complexity": _clamp(fine_feature_factor * quality_risk_factor, 1.0, 1.6),
    }


def _loss_model(geometry, topology, props, slider_count):
    runner_percent = (
        QUOTE_CONSTANTS["base_runner_overflow_percent"]
        + max(2.6 - geometry["mean_thickness_mm"], 0.0) * 0.55
        + max(geometry["flow_length_ratio"] - 24.0, 0.0) * 0.02
        + slider_count * 0.35
        + max(0.40 - geometry["bbox_fill_ratio"], 0.0) * 7.0
    ) * props["yield_bias"]
    runner_percent = _clamp(runner_percent, 3.0, 12.5)

    scrap_percent = (
        QUOTE_CONSTANTS["base_scrap_percent"]
        + max(1.8 - geometry["mean_thickness_mm"], 0.0) * 0.9
        + max(geometry["true_surface_factor"] - 1.5, 0.0) * 1.4
        + max(65.0 - topology["integrity_score"], 0.0) * 0.03
        + (0.8 if not topology["is_manifold"] else 0.0)
    )
    scrap_percent = _clamp(scrap_percent, 1.5, 9.0)

    melting_loss_percent = QUOTE_CONSTANTS["base_melting_process_loss_percent"]

    return {
        "runner_percent": runner_percent,
        "scrap_percent": scrap_percent,
        "melting_loss_percent": melting_loss_percent,
    }


def _machine_selection(projected_area, gross_melt_kg, geometry, complexity, props):
    thin_wall_factor = _clamp(
        (2.8 / max(geometry["mean_thickness_mm"], 0.8)) ** 0.09,
        1.0,
        1.22,
    )
    pressure_area = projected_area * thin_wall_factor * props["flow_factor"]
    force_kn = pressure_area * props["injection_pressure"] / 1000.0
    force_tonne = force_kn / 9.81
    req_tonnage = force_tonne * _clamp(1.12 + (complexity["overall_complexity"] - 1.0) * 0.35, 1.12, 1.42)

    shot_utilization = _clamp(
        0.72
        - max(2.2 - geometry["mean_thickness_mm"], 0.0) * 0.04
        - max(complexity["overall_complexity"] - 1.0, 0.0) * 0.06,
        0.50,
        0.72,
    )
    required_shot_capacity_kg = gross_melt_kg / shot_utilization

    selected = _MACHINE_RATES_INR[-1]
    for machine in _MACHINE_RATES_INR:
        if req_tonnage <= machine["limit"] and required_shot_capacity_kg <= machine["shot_capacity_kg"]:
            selected = machine
            break

    return {
        "required_tonnage": req_tonnage,
        "selected_machine": selected["limit"],
        "machine_rate_inr": selected["rate_inr"],
        "machine_shot_capacity_kg": selected["shot_capacity_kg"],
        "required_shot_capacity_kg": required_shot_capacity_kg,
        "thin_wall_factor": thin_wall_factor,
    }


def _cycle_model(weight_g, geometry, complexity, slider_count, props):
    fill_s = _clamp(
        0.16
        + 0.0025 * (geometry["projected_area"] ** 0.5)
        + max(geometry["flow_length_ratio"] - 20.0, 0.0) * 0.003,
        0.25,
        2.2,
    ) / max(props["flow_factor"], 0.7)

    intensification_s = 1.0 + max(complexity["overall_complexity"] - 1.0, 0.0) * 0.8
    solidification_s = (
        5.5
        + 1.9 * (max(geometry["mean_thickness_mm"], 0.8) ** 0.58)
        + 0.030 * (max(weight_g, 1.0) ** 0.46)
    ) * props["solidification_factor"]
    die_open_close_s = 6.5 + 0.018 * geometry["max_dim"] + 0.002 * (geometry["projected_area"] ** 0.5)
    spray_extract_s = 4.8 + max(complexity["fine_feature_factor"] - 1.0, 0.0) * 4.0 + slider_count * 1.7
    trim_handle_s = 2.8 + slider_count * 1.1 + max(complexity["quality_risk_factor"] - 1.0, 0.0) * 2.0

    cycle_s = max(16.0, fill_s + intensification_s + solidification_s + die_open_close_s + spray_extract_s + trim_handle_s)
    return {
        "fill_s": fill_s,
        "intensification_s": intensification_s,
        "solidification_s": solidification_s,
        "die_open_close_s": die_open_close_s,
        "spray_extract_s": spray_extract_s,
        "trim_handle_s": trim_handle_s,
        "cycle_time_s": cycle_s,
        "shots_per_hour": 3600.0 / cycle_s,
    }


def _tooling_costs(projected_area, machine_tonnage, slider_count, metal, geometry, complexity, topology):
    area_cm2 = max(projected_area / 100.0, 5.0)
    die_complexity = _clamp(
        1.0
        + max(complexity["overall_complexity"] - 1.0, 0.0) * 0.65
        + max(topology["faces"] - 150, 0) / 3000.0
        + max(topology["solids"] - 1, 0) * 0.05,
        1.0,
        1.55,
    )
    thermal_factor = METAL_PROPERTIES[metal]["tool_wear_factor"]
    base_die = 500_000 * (area_cm2 / 50.0) ** 0.67
    base_die *= die_complexity * thermal_factor
    tonnage_premium = max(0, machine_tonnage - 500) * 220
    slider_add = slider_count * 150_000
    hpdc_die = max(base_die + tonnage_premium + slider_add, 400_000)

    trimming_die = hpdc_die * (0.16 + max(geometry["aspect_ratio"] - 3.0, 0.0) * 0.005)
    fixture = hpdc_die * 0.08 * 2
    machining_tooling = hpdc_die * (0.09 + max(complexity["fine_feature_factor"] - 1.0, 0.0) * 0.05)
    gauges = hpdc_die * (0.045 + max(complexity["quality_risk_factor"] - 1.0, 0.0) * 0.02) * 2
    compression_test = hpdc_die * 0.025 if topology["integrity_score"] < 90 else hpdc_die * 0.02
    ct_scan = hpdc_die * 0.018 if complexity["quality_risk_factor"] > 1.08 or projected_area > 25_000 else 0.0
    total = hpdc_die + trimming_die + fixture + machining_tooling + gauges + compression_test + ct_scan

    return {
        "hpdc_die": round(hpdc_die, 2),
        "trimming_die": round(trimming_die, 2),
        "fixture": round(fixture, 2),
        "machining_tooling": round(machining_tooling, 2),
        "gauges": round(gauges, 2),
        "compression_test": round(compression_test, 2),
        "ct_scan": round(ct_scan, 2),
        "total": round(total, 2),
        "die_life_shots": max(10_000, int(_die_life(metal) / max(METAL_PROPERTIES[metal]["tool_wear_factor"], 0.6))),
        "complexity_factor": round(die_complexity, 4),
    }


def _secondary_process_costs(weight_kg, costing_weight_kg, geometry, complexity, topology, slider_count):
    trim_factor = _clamp(
        0.55
        + max(complexity["fine_feature_factor"] - 1.0, 0.0) * 0.9
        + slider_count * 0.10,
        0.55,
        1.55,
    )
    trimming_inr = weight_kg * 22.0 * trim_factor

    xray_inr = 0.0
    if complexity["quality_risk_factor"] > 1.10 or topology["integrity_score"] < 78:
        xray_inr = weight_kg * QUOTE_CONSTANTS["xray_rate_inr_per_kg"] * _clamp(complexity["quality_risk_factor"], 1.0, 1.35)

    vmc_inr = 0.0
    if geometry["true_surface_factor"] > 1.75 or topology["faces"] > 180:
        vmc_inr = weight_kg * QUOTE_CONSTANTS["vmc_rate_inr_per_kg"] * _clamp(complexity["fine_feature_factor"], 1.0, 1.4)

    qa_inr = costing_weight_kg * QUOTE_CONSTANTS["qa_rate_inr_per_kg"] * _clamp(
        0.9 + max(complexity["quality_risk_factor"] - 1.0, 0.0) * 1.2,
        0.9,
        1.35,
    )
    compression_test_inr = 0.0
    if topology["integrity_score"] < 90 or geometry["projected_area"] > 18_000:
        compression_test_inr = costing_weight_kg * QUOTE_CONSTANTS["compression_test_rate_inr_per_kg"]

    return {
        "trimming_inr": trimming_inr,
        "xray_inr": xray_inr,
        "vmc_inr": vmc_inr,
        "qa_inr": qa_inr,
        "compression_test_inr": compression_test_inr,
    }


def _other_costs(raw_total_inr, conv_total_before_others, die_amort_inr, weight_kg, costing_weight_kg, complexity, topology):
    bop_inr = raw_total_inr * QUOTE_CONSTANTS["bop_percent"] / 100.0
    job_work_inr = QUOTE_CONSTANTS["job_work_base_inr"]

    base_for_others = raw_total_inr + conv_total_before_others + die_amort_inr
    icc_inr = base_for_others * QUOTE_CONSTANTS["icc_percent"] / 100.0
    credit_inr = base_for_others * QUOTE_CONSTANTS["credit_cost_inr"] / 100.0 if QUOTE_CONSTANTS["credit_cost_inr"] else 0.0
    insurance_inr = base_for_others * QUOTE_CONSTANTS["insurance_percent"] / 100.0
    acd_backup_inr = base_for_others * QUOTE_CONSTANTS["acd_backup_percent"] / 100.0
    licence_inr = base_for_others * QUOTE_CONSTANTS["licence_cost_percent"] / 100.0

    rejection_percent = _clamp(
        1.2
        + max(complexity["quality_risk_factor"] - 1.0, 0.0) * 6.0
        + max(80.0 - topology["integrity_score"], 0.0) * 0.06,
        1.0,
        5.5,
    )
    rejection_inr = conv_total_before_others * rejection_percent / 100.0
    yoy_reduction_inr = -(base_for_others * QUOTE_CONSTANTS["yoy_reduction_percent"] / 100.0)
    packing_inr = costing_weight_kg * QUOTE_CONSTANTS["packing_rate_inr_per_kg"] * _clamp(0.9 + weight_kg * 0.08, 0.9, 1.35)

    return {
        "bop_inr": bop_inr,
        "job_work_inr": job_work_inr,
        "icc_inr": icc_inr,
        "credit_inr": credit_inr,
        "insurance_inr": insurance_inr,
        "acd_backup_inr": acd_backup_inr,
        "licence_inr": licence_inr,
        "rejection_inr": rejection_inr,
        "rejection_percent": rejection_percent,
        "yoy_reduction_inr": yoy_reduction_inr,
        "packing_inr": packing_inr,
    }


def calculate_hpdc_cost(traits, metal, annual_volume, sliders, location_multiplier=1.0, port_cost=0.0):
    if metal not in METAL_PROPERTIES:
        metal = "Aluminum_A380"

    props = METAL_PROPERTIES[metal]
    production_qty = max(1, int(annual_volume or 1))
    slider_count = max(0, int(sliders or 0))
    port_cost = max(0.0, float(port_cost or 0.0))

    geometry = _geometry_inputs(traits)
    topology = _topology_inputs(traits)
    complexity = _complexity_factors(geometry, topology, slider_count)

    if geometry["max_dim"] > 5000 or geometry["projected_area"] > 5_000_000 or geometry["volume"] > 1_000_000_000:
        raise ValueError(
            "GEOMETRY_SCALE_ERROR: CAD dimensions outside realistic part limits. "
            "Export file in mm or upload a clean STL/STEP."
        )

    weight_override = traits.get("casting_weight_g_override")
    weight_g = float(weight_override) if weight_override else geometry["volume"] * props["density"]
    weight_kg = weight_g / 1000.0

    losses = _loss_model(geometry, topology, props, slider_count)
    yield_factor = 1.0 / (1.0 - (losses["runner_percent"] + losses["scrap_percent"]) / 100.0)
    gross_melt_kg = weight_kg * yield_factor
    costing_weight_kg = gross_melt_kg * (1.0 + losses["melting_loss_percent"] / 100.0)

    market_price_inr = props["price_per_kg"] * INR_RATE
    alloy_price_floor = QUOTE_CONSTANTS["metal_price_inr_per_kg"] * 0.90
    alloy_price_inr = round(
        max(market_price_inr, alloy_price_floor)
        * _clamp(1.0 + max(props["tool_wear_factor"] - 1.0, 0.0) * 0.04, 1.0, 1.08),
        2,
    )
    material_cost_inr = costing_weight_kg * alloy_price_inr

    machine = _machine_selection(geometry["projected_area"], gross_melt_kg, geometry, complexity, props)
    cycle = _cycle_model(weight_g, geometry, complexity, slider_count, props)

    hourly_inr = machine["machine_rate_inr"] * location_multiplier + QUOTE_CONSTANTS["operator_labour_inr_per_hour"]
    machine_cost_inr = hourly_inr / cycle["shots_per_hour"]

    consumable_inr = QUOTE_CONSTANTS["consumable_inr"] * _clamp(0.95 + (complexity["overall_complexity"] - 1.0) * 0.35, 0.95, 1.25)
    melting_cost_inr = costing_weight_kg * QUOTE_CONSTANTS["melting_cost_inr_per_kg"] * _clamp(props["solidification_factor"], 0.8, 1.35)
    fettling_minutes = QUOTE_CONSTANTS["fettling_time_minutes"] * _clamp(
        0.9
        + max(complexity["fine_feature_factor"] - 1.0, 0.0) * 1.2
        + slider_count * 0.12,
        0.9,
        2.1,
    )
    fettling_inr = (fettling_minutes / 60.0) * QUOTE_CONSTANTS["manual_labour_inr_per_hour"]
    shot_blast_inr = costing_weight_kg * QUOTE_CONSTANTS["shot_blast_inr_per_kg"]
    cleaning_inr = QUOTE_CONSTANTS["cleaning_washing_inr"] * _clamp(0.9 + max(complexity["quality_risk_factor"] - 1.0, 0.0) * 1.4, 0.9, 1.35)
    secondary = _secondary_process_costs(weight_kg, costing_weight_kg, geometry, complexity, topology, slider_count)

    tooling = _tooling_costs(
        geometry["projected_area"] * machine["thin_wall_factor"],
        machine["selected_machine"],
        slider_count,
        metal,
        geometry,
        complexity,
        topology,
    )
    die_life = tooling["die_life_shots"]
    amortization_qty = max(min(die_life, production_qty * PROGRAM_LIFE_YEARS), production_qty, 1)
    die_amort_inr = tooling["total"] / amortization_qty
    tool_maintenance_inr = tooling["total"] * QUOTE_CONSTANTS["tool_maintenance_percent"] / 100.0 / max(amortization_qty, 1)

    freight_inr = costing_weight_kg * QUOTE_CONSTANTS["freight_rate_inr_per_kg"]
    port_cost_inr = port_cost * INR_RATE

    bop_inr = material_cost_inr * QUOTE_CONSTANTS["bop_percent"] / 100.0
    job_work_inr = QUOTE_CONSTANTS["job_work_base_inr"]
    raw_total_inr = material_cost_inr + bop_inr + job_work_inr

    conv_total_inr = (
        machine_cost_inr
        + consumable_inr
        + melting_cost_inr
        + secondary["trimming_inr"]
        + fettling_inr
        + shot_blast_inr
        + secondary["xray_inr"]
        + secondary["vmc_inr"]
        + cleaning_inr
        + tool_maintenance_inr
        + secondary["qa_inr"]
        + secondary["compression_test_inr"]
    )
    other_costs = _other_costs(raw_total_inr, conv_total_inr, die_amort_inr, weight_kg, costing_weight_kg, complexity, topology)
    others_inr = (
        other_costs["icc_inr"]
        + other_costs["credit_inr"]
        + other_costs["insurance_inr"]
        + other_costs["acd_backup_inr"]
        + other_costs["licence_inr"]
        + other_costs["rejection_inr"]
        + other_costs["yoy_reduction_inr"]
    )

    subtotal_inr = raw_total_inr + conv_total_inr + others_inr + other_costs["packing_inr"] + die_amort_inr + freight_inr + port_cost_inr
    over_heads_inr = subtotal_inr * (QUOTE_CONSTANTS["rnd_percent"] + QUOTE_CONSTANTS["sa_percent"]) / 100.0
    rnd_inr = subtotal_inr * QUOTE_CONSTANTS["rnd_percent"] / 100.0
    sa_inr = subtotal_inr * QUOTE_CONSTANTS["sa_percent"] / 100.0
    ebit_inr = subtotal_inr * QUOTE_CONSTANTS["ebit_percent"] / 100.0
    total_inr = subtotal_inr + rnd_inr + sa_inr + ebit_inr

    quote_sheet_rows = [
        _row(4, "Part", "PART NAME", 0, "", "Uploaded CAD file"),
        _row(5, "Part", "PDC M/C Tonnage", machine["selected_machine"], "T"),
        _row(6, "Part", "Cavity", 1, "nos"),
        _row(8, "Raw material", "Volume", geometry["volume"], "mm3"),
        _row(8, "Raw material", "Projected area", geometry["projected_area"], "mm2", code="P.A."),
        _row(9, "Raw material", "EX. Rate", INR_RATE, "INR/USD"),
        _row(10, "Raw material", "Casting Weight", weight_kg, "kg"),
        _row(11, "Raw material", "Gross Weight incl. Runner+Scrap", gross_melt_kg, "kg", f"{round(losses['runner_percent'] + losses['scrap_percent'], 2)}%"),
        _row(11, "Raw material", "Costing Weight incl. Melt Loss", costing_weight_kg, "kg", f"{round(losses['melting_loss_percent'], 2)}%"),
        _row(12, "Raw material", "Alloy Price/kg", alloy_price_inr, "INR/kg"),
        _row(13, "Raw material", "Cost of Raw Materials", raw_total_inr, "INR"),
        _row(14, "Raw material", "Alloy Cost", material_cost_inr, "INR"),
        _row(15, "Raw material", "BOP", bop_inr, "INR"),
        _row(16, "Raw material", "Job Work", job_work_inr, "INR"),
        _row(17, "Raw material", "Total", raw_total_inr, "INR", code="A"),
        _row(19, "Conversion", "PDC Machine", machine_cost_inr, "INR"),
        _row(20, "Conversion", "Consumable", consumable_inr, "INR"),
        _row(21, "Conversion", "Melting Cost", melting_cost_inr, "INR"),
        _row(22, "Conversion", "Trimming", secondary["trimming_inr"], "INR"),
        _row(23, "Conversion", "Fettling", fettling_inr, "INR", f"{round(fettling_minutes, 2)} min / part"),
        _row(24, "Conversion", "Shot Blast", shot_blast_inr, "INR"),
        _row(25, "Conversion", "Xray", secondary["xray_inr"], "INR"),
        _row(26, "Conversion", "VMC", secondary["vmc_inr"], "INR"),
        _row(27, "Conversion", "Cleaning/Washing", cleaning_inr, "INR"),
        _row(28, "Conversion", "Tool Maint.", tool_maintenance_inr, "INR"),
        _row(29, "Conversion", "Sp Hand QA", secondary["qa_inr"], "INR"),
        _row(30, "Conversion", "Compression Test", secondary["compression_test_inr"], "INR"),
        _row(31, "Conversion", "Total", conv_total_inr, "INR", code="B"),
        _row(33, "Others", "ICC", other_costs["icc_inr"], "INR"),
        _row(34, "Others", "Credit Costs", other_costs["credit_inr"], "INR"),
        _row(35, "Others", "Insurance", other_costs["insurance_inr"], "INR", "0.50%"),
        _row(36, "Others", "ACD Backup", other_costs["acd_backup_inr"], "INR"),
        _row(37, "Others", "Licence Cost", other_costs["licence_inr"], "INR"),
        _row(38, "Others", "Rejection", other_costs["rejection_inr"], "INR", f"{round(other_costs['rejection_percent'], 2)}%"),
        _row(39, "Others", "YOY Reduction", other_costs["yoy_reduction_inr"], "INR"),
        _row(40, "Others", "Total", others_inr, "INR", code="C"),
        _row(41, "Packing/Margins", "Packing", other_costs["packing_inr"], "INR", code="D"),
        _row(42, "Packing/Margins", "Over Heads (R&D+S&A)", over_heads_inr, "INR", f"{QUOTE_CONSTANTS['rnd_percent'] + QUOTE_CONSTANTS['sa_percent']}%", code="E"),
        _row(43, "Packing/Margins", "Profit (EBIT)", ebit_inr, "INR", f"{QUOTE_CONSTANTS['ebit_percent']}%", code="F"),
        _row(44, "Packing/Margins", "Freight (DAP VC Noida)", freight_inr, "INR", code="G"),
        _row(46, "Summary", "Cost of Raw Material", raw_total_inr, "INR", code="A"),
        _row(47, "Summary", "Conversion Cost", conv_total_inr, "INR", code="B"),
        _row(48, "Summary", "Others", others_inr, "INR", code="C"),
        _row(49, "Summary", "Packing", other_costs["packing_inr"], "INR", code="D"),
        _row(50, "Summary", "Overheads", over_heads_inr, "INR", code="E"),
        _row(51, "Summary", "Profit", ebit_inr, "INR", code="F"),
        _row(52, "Summary", "Freight", freight_inr, "INR", code="G"),
        _row(55, "Summary", "Repeat Tool Amortization Cost", die_amort_inr, "INR"),
        _row(56, "Summary", "Final Cost incl. Tooling", total_inr, "INR"),
        _row(58, "Tooling", "HPDC Die cost", tooling["hpdc_die"], "INR", "1 set"),
        _row(59, "Tooling", "Trimming Die cost", tooling["trimming_die"], "INR", "1 set"),
        _row(60, "Tooling", "Fixture Cost", tooling["fixture"], "INR", "2 set"),
        _row(61, "Tooling", "Machining Tooling", tooling["machining_tooling"], "INR", "1 set"),
        _row(62, "Tooling", "Gauges Cost", tooling["gauges"], "INR", "2 set"),
        _row(63, "Tooling", "Compression Test", tooling["compression_test"], "INR", "1 set"),
        _row(64, "Tooling", "CT Scan (One Time)", tooling["ct_scan"], "INR", "As applicable"),
        _row(65, "Tooling", "TOTAL Tooling Cost", tooling["total"], "INR", f"die life {die_life:,} shots"),
    ]

    range_pct = _clamp(
        props["volatility"]
        + max(complexity["overall_complexity"] - 1.0, 0.0) * 0.05
        + max(75.0 - topology["integrity_score"], 0.0) * 0.0008,
        0.04,
        0.16,
    )
    total_usd = total_inr / INR_RATE

    return {
        "material_cost": round(material_cost_inr / INR_RATE, 2),
        "machine_cost": round(machine_cost_inr / INR_RATE, 2),
        "amortization": round(die_amort_inr / INR_RATE, 2),
        "port_cost": round(port_cost, 2),
        "total_unit_cost": round(total_usd, 2),
        "per_part_cost": round(total_usd, 2),
        "annual_volume": production_qty,
        "alloy": metal,
        "market_price": round(props["price_per_kg"], 2),
        "alloy_price_inr": alloy_price_inr,
        "spreadsheet_constants": {
            **QUOTE_CONSTANTS,
            "alloy_price_inr_per_kg": alloy_price_inr,
            "die_life_shots": die_life,
            "amortization_quantity": amortization_qty,
            "runner_overflow_percent": round(losses["runner_percent"], 3),
            "scrap_percent": round(losses["scrap_percent"], 3),
            "melting_process_loss_percent": round(losses["melting_loss_percent"], 3),
        },
        "tooling_rows_58_60": TOOLING_ROWS_58_60,
        "quote_sheet_rows": quote_sheet_rows,
        "tooling_estimate_inr": round(tooling["total"], 2),
        "tooling_costs": tooling,
        "costing_weight_kg": round(costing_weight_kg, 4),
        "gross_melt_kg": round(gross_melt_kg, 4),
        "yield_factor": round(yield_factor, 4),
        "inr_breakdown": {
            "Raw material": round(raw_total_inr, 2),
            "Machine energy / PDC": round(machine_cost_inr, 2),
            "Consumable": round(consumable_inr, 2),
            "Melting cost": round(melting_cost_inr, 2),
            "Trimming": round(secondary["trimming_inr"], 2),
            "Fettling": round(fettling_inr, 2),
            "Shot blast": round(shot_blast_inr, 2),
            "Xray": round(secondary["xray_inr"], 2),
            "VMC": round(secondary["vmc_inr"], 2),
            "Cleaning / washing": round(cleaning_inr, 2),
            "Tool maintenance": round(tool_maintenance_inr, 2),
            "QA inspection": round(secondary["qa_inr"], 2),
            "Compression test": round(secondary["compression_test_inr"], 2),
            "Packing": round(other_costs["packing_inr"], 2),
            "Others": round(others_inr, 2),
            "Die amortization": round(die_amort_inr, 2),
            "Freight": round(freight_inr, 2),
            "Port / handling": round(port_cost_inr, 2),
            "R&D": round(rnd_inr, 2),
            "S&A": round(sa_inr, 2),
            "EBIT": round(ebit_inr, 2),
            "Total": round(total_inr, 2),
        },
        "fluctuation_range": {
            "min": round(total_usd * (1 - range_pct), 2),
            "max": round(total_usd * (1 + range_pct), 2),
            "percent": round(range_pct * 100, 1),
        },
        "machine_details": {
            "required_tonnage": round(machine["required_tonnage"], 1),
            "selected_machine": machine["selected_machine"],
            "machine_rate_inr": machine["machine_rate_inr"],
            "machine_shot_capacity_kg": machine["machine_shot_capacity_kg"],
            "required_shot_capacity_kg": round(machine["required_shot_capacity_kg"], 3),
            "cycle_time_s": round(cycle["cycle_time_s"], 1),
            "shots_per_hour": round(cycle["shots_per_hour"], 1),
            "estimated_wall_thickness_mm": round(geometry["mean_thickness_mm"], 2),
            "fill_time_s": round(cycle["fill_s"], 3),
            "solidification_s": round(cycle["solidification_s"], 3),
            "complexity_factor": round(complexity["overall_complexity"], 4),
        },
        "tooling_estimate": round(tooling["total"] / INR_RATE, 0),
        "weight_g": round(weight_g, 1),
    }
