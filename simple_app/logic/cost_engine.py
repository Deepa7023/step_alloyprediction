import math

# Market Rates (Refined for Industry Standards)
METAL_PROPERTIES = {
    "Aluminum_A380": {"density": 0.0027, "price_per_kg": 2.85, "injection_pressure": 80, "volatility": 0.06},
    "Aluminum_ADC12": {"density": 0.00272, "price_per_kg": 2.78, "injection_pressure": 78, "volatility": 0.06},
    "Aluminum_A356": {"density": 0.00268, "price_per_kg": 3.05, "injection_pressure": 72, "volatility": 0.07},
    "Aluminum_6061": {"density": 0.00270, "price_per_kg": 3.25, "injection_pressure": 70, "volatility": 0.07},
    "Zinc_ZD3": {"density": 0.0066, "price_per_kg": 3.42, "injection_pressure": 30, "volatility": 0.05},
    "Zinc_Zamak5": {"density": 0.0067, "price_per_kg": 3.55, "injection_pressure": 32, "volatility": 0.05},
    "Magnesium_AZ91D": {"density": 0.0018, "price_per_kg": 4.65, "injection_pressure": 60, "volatility": 0.08},
    "Magnesium_AM60B": {"density": 0.00179, "price_per_kg": 4.90, "injection_pressure": 58, "volatility": 0.08},
    "Copper_Brass": {"density": 0.0085, "price_per_kg": 8.70, "injection_pressure": 95, "volatility": 0.09},
    "Steel_Stainless": {"density": 0.0078, "price_per_kg": 2.15, "injection_pressure": 110, "volatility": 0.06},
}

# Machine Tonnage Mapping (Tonne : Hourly Rate $)
MACHINE_RATES = [
    {"limit": 250, "rate": 55},
    {"limit": 500, "rate": 85},
    {"limit": 850, "rate": 125},
    {"limit": 1250, "rate": 180},
    {"limit": 2000, "rate": 320},
    {"limit": 4000, "rate": 600}
]

QUOTE_CONSTANTS = {
    "runner_overflow_percent": 8.0,
    "scrap_percent": 3.0,
    "melting_process_loss_percent": 6.0,
    "metal_price_inr_per_kg": 212.80,
    "rnd_percent": 4.0,
    "sa_percent": 6.1,
    "ebit_percent": 10.0,
    "die_cost_inr": 1200000.0,
    "die_life_shots": 150000.0,
    "base_projected_area_mm2": 37400.0,
    "base_machine_tonnage": 500.0,
    "consumable_inr": 5.0,
    "melting_cost_inr_per_kg": 12.0,
    "shot_blast_inr_per_kg": 6.0,
    "cleaning_washing_inr": 4.0,
    "labour_rate_inr_per_hour": 60.0,
    "fettling_time_minutes": 5.0,
    "freight_rate_inr_per_kg": 0.0,
}

TOOLING_ROWS_58_60 = [
    {"row": 58, "label": "HPDC Die cost", "quantity": 1, "unit": "set"},
    {"row": 59, "label": "Trimming Die cost", "quantity": 1, "unit": "set"},
    {"row": 60, "label": "Fixture Cost", "quantity": 2, "unit": "set"},
]


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


def _tooling_costs(projected_area, machine_tonnage, slider_count, weight_kg):
    area_factor = math.sqrt(max(projected_area, 1.0) / QUOTE_CONSTANTS["base_projected_area_mm2"])
    tonnage_factor = math.sqrt(max(machine_tonnage, 1.0) / QUOTE_CONSTANTS["base_machine_tonnage"])
    slider_factor = 1 + (0.12 * max(0, slider_count))
    weight_factor = 1 + math.log10(max(weight_kg * 1000, 1.0)) * 0.035
    complexity_factor = area_factor * tonnage_factor * slider_factor * weight_factor

    hpdc_die = max(0.0, QUOTE_CONSTANTS["die_cost_inr"] * complexity_factor)
    trimming_die = hpdc_die * 0.18
    fixture = hpdc_die * 0.08
    machining_tooling = hpdc_die * 0.10
    gauges = hpdc_die * 0.05
    compression_test = hpdc_die * 0.025
    ct_scan = hpdc_die * 0.015 if projected_area > 25000 else 0.0
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
        "complexity_factor": round(complexity_factor, 4),
    }


def calculate_hpdc_cost(traits, metal, annual_volume, sliders, location_multiplier=1.0, live_price_per_kg=None, port_cost=0.0):
    """
    Calculates HPDC cost based on part traits and user parameters.
    """
    if metal not in METAL_PROPERTIES:
        metal = "Aluminum_A380"
        
    props = METAL_PROPERTIES[metal]
    production_qty = max(1, int(annual_volume or 1))
    slider_count = max(0, int(sliders or 0))
    port_cost = max(0.0, float(port_cost or 0.0))
    volume = traits.get('volume', 0)
    projected_area = traits.get('projected_area', 0)
    dimensions = traits.get("dimensions") or {}
    max_dimension = max([float(v or 0) for v in dimensions.values()] or [0])
    if max_dimension > 5000 or projected_area > 5_000_000 or volume > 1_000_000_000:
        raise ValueError(
            "GEOMETRY_SCALE_ERROR: CAD dimensions are outside realistic part limits after unit normalization. "
            "Please export the file in millimeters or upload a clean STL/STEP."
        )
    
    market_price = live_price_per_kg if live_price_per_kg is not None else props['price_per_kg']
    
    # 1. Material Cost (Render-light spreadsheet model)
    weight = volume * props['density'] # grams
    weight_kg = weight / 1000

    yield_factor = 1 / (
        1 - (
            QUOTE_CONSTANTS["runner_overflow_percent"] +
            QUOTE_CONSTANTS["scrap_percent"]
        ) / 100
    )
    gross_melt_kg = weight_kg * yield_factor
    costing_weight_kg = gross_melt_kg * (1 + QUOTE_CONSTANTS["melting_process_loss_percent"] / 100)
    material_cost_inr = costing_weight_kg * QUOTE_CONSTANTS["metal_price_inr_per_kg"]
    
    # 2. Machine Tonnage (Clamping Force)
    force_kn = projected_area * props.get('injection_pressure', 80) / 1000
    force_tonne = force_kn / 9.81
    required_tonnage = force_tonne * 1.40 
    
    machine_rate = MACHINE_RATES[0]['rate']
    machine_tonnage = MACHINE_RATES[0]['limit']
    for m in MACHINE_RATES:
        if required_tonnage <= m['limit']:
            machine_rate = m['rate']
            machine_tonnage = m['limit']
            break
    
    if required_tonnage > MACHINE_RATES[-1]['limit']:
        machine_rate = MACHINE_RATES[-1]['rate']
        machine_tonnage = MACHINE_RATES[-1]['limit']
            
    # 3. Cycle Time & Labor
    cooling_time = math.sqrt(weight_kg * 1000) * 0.85
    cycle_time = 25 + cooling_time + (slider_count * 5)
    shots_per_hour = 3600 / cycle_time
    
    conversion_hourly_rate = (machine_rate * location_multiplier) + 55.0 
    machine_cost_per_part = conversion_hourly_rate / shots_per_hour
    machine_cost_inr = machine_cost_per_part * 83.5
    
    # 4. Conversion and die amortization from the supplied costing sheet.
    consumable_inr = QUOTE_CONSTANTS["consumable_inr"]
    melting_cost_inr = costing_weight_kg * QUOTE_CONSTANTS["melting_cost_inr_per_kg"]
    fettling_inr = (
        QUOTE_CONSTANTS["fettling_time_minutes"] / 60
    ) * QUOTE_CONSTANTS["labour_rate_inr_per_hour"]
    shot_blast_inr = costing_weight_kg * QUOTE_CONSTANTS["shot_blast_inr_per_kg"]
    cleaning_inr = QUOTE_CONSTANTS["cleaning_washing_inr"]
    tooling_costs = _tooling_costs(projected_area, machine_tonnage, slider_count, weight_kg)
    die_amortization_inr = tooling_costs["total"] / QUOTE_CONSTANTS["die_life_shots"]
    freight_inr = costing_weight_kg * QUOTE_CONSTANTS["freight_rate_inr_per_kg"]
    port_cost_inr = port_cost * 83.5

    raw_material_total_inr = material_cost_inr
    conversion_total_inr = (
        machine_cost_inr + consumable_inr + melting_cost_inr +
        fettling_inr + shot_blast_inr + cleaning_inr
    )
    subtotal_before_margins_inr = (
        raw_material_total_inr + conversion_total_inr +
        die_amortization_inr + freight_inr + port_cost_inr
    )
    rnd_inr = subtotal_before_margins_inr * QUOTE_CONSTANTS["rnd_percent"] / 100
    sa_inr = subtotal_before_margins_inr * QUOTE_CONSTANTS["sa_percent"] / 100
    ebit_inr = subtotal_before_margins_inr * QUOTE_CONSTANTS["ebit_percent"] / 100
    total_unit_cost_inr = subtotal_before_margins_inr + rnd_inr + sa_inr + ebit_inr
    final_cost_before_tool_amort_inr = total_unit_cost_inr - die_amortization_inr
    total_unit_cost = total_unit_cost_inr / 83.5
    tooling_cost_total = tooling_costs["total"] / 83.5
    amortization_cost = die_amortization_inr / 83.5
    material_cost = material_cost_inr / 83.5
    quote_sheet_rows = [
        _row(4, "Part", "PART NAME", 0, "", "Uploaded CAD file"),
        _row(5, "Part", "PDC M/C Tonnage", machine_tonnage, "T"),
        _row(6, "Part", "Cavity", 1, "nos"),
        _row(8, "Raw material", "Volume", volume, "mm3"),
        _row(8, "Raw material", "Projected area", projected_area, "mm2", code="P.A."),
        _row(9, "Raw material", "EX. Rate", 83.5, "INR/USD"),
        _row(10, "Raw material", "Casting Weight", weight_kg, "kg"),
        _row(11, "Raw material", "Gross Weight including Burning Loss", costing_weight_kg, "kg", f"{QUOTE_CONSTANTS['melting_process_loss_percent']}%"),
        _row(12, "Raw material", "Alloy Price/kg", QUOTE_CONSTANTS["metal_price_inr_per_kg"], "INR/kg"),
        _row(13, "Raw material", "Cost of Raw Materials", raw_material_total_inr, "INR"),
        _row(14, "Raw material", "Alloy Cost", raw_material_total_inr, "INR"),
        _row(15, "Raw material", "BOP", 0, "INR"),
        _row(16, "Raw material", "Job Work", 0, "INR"),
        _row(17, "Raw material", "Total", raw_material_total_inr, "INR", code="A"),
        _row(19, "Conversion", "PDC", machine_cost_inr, "INR"),
        _row(20, "Conversion", "Consumable", consumable_inr, "INR"),
        _row(21, "Conversion", "Melting Cost", melting_cost_inr, "INR"),
        _row(22, "Conversion", "Trimming", 0, "INR"),
        _row(23, "Conversion", "Fettling", fettling_inr, "INR", f"{QUOTE_CONSTANTS['fettling_time_minutes']} min / 60 x labour rate"),
        _row(24, "Conversion", "Shot Blast (Hanger Type)", shot_blast_inr, "INR"),
        _row(25, "Conversion", "Xray", 0, "INR"),
        _row(26, "Conversion", "VMC", 0, "INR"),
        _row(27, "Conversion", "Cleaning/Washing", cleaning_inr, "INR"),
        _row(28, "Conversion", "Tool Maint.", 0, "INR"),
        _row(29, "Conversion", "Sp Hand Qa (Inspection)", 0, "INR"),
        _row(30, "Conversion", "Compression Test", 0, "INR"),
        _row(31, "Conversion", "Total", conversion_total_inr, "INR", code="B"),
        _row(33, "Others", "ICC", 0, "INR"),
        _row(34, "Others", "Credit Costs", 75, "INR", "12%"),
        _row(35, "Others", "Insurance", 0, "INR", "0.50%"),
        _row(36, "Others", "ACD Backup", 0, "INR"),
        _row(37, "Others", "Licence Cost", 0, "INR"),
        _row(38, "Others", "Rejection", 0, "INR", "5%"),
        _row(39, "Others", "YOY Reduction", 0, "INR"),
        _row(40, "Others", "Total", 75, "INR", code="C"),
        _row(41, "Packing / Margins", "Packing", 0, "INR", code="D"),
        _row(42, "Packing / Margins", "Over Heads", 0, "INR", "12%", code="E"),
        _row(43, "Packing / Margins", "Profit", ebit_inr, "INR", "8%", code="F"),
        _row(44, "Packing / Margins", "Freight Cost (DAP VC Noida)", freight_inr, "INR", code="G"),
        _row(46, "Summary", "Cost of Raw Material", raw_material_total_inr, "INR", code="A"),
        _row(47, "Summary", "Conversion Cost", conversion_total_inr, "INR", code="B"),
        _row(48, "Summary", "Others", 75, "INR", code="C"),
        _row(49, "Summary", "Packing", 0, "INR", code="D"),
        _row(50, "Summary", "Overheads", rnd_inr + sa_inr, "INR", code="E"),
        _row(51, "Summary", "Profit", ebit_inr, "INR", code="F"),
        _row(52, "Summary", "Freight Cost (DAP VC Noida)", freight_inr, "INR", code="G"),
        _row(55, "Summary", "Repeat Tool Amortization Cost", die_amortization_inr, "INR"),
        _row(56, "Summary", "Final Cost including tool amort. Cost", total_unit_cost_inr, "INR"),
        _row(58, "Tooling", "HPDC Die cost", tooling_costs["hpdc_die"], "INR", "1 set"),
        _row(59, "Tooling", "Trimming Die cost", tooling_costs["trimming_die"], "INR", "1 set"),
        _row(60, "Tooling", "Fixture Cost", tooling_costs["fixture"], "INR", "2 set"),
        _row(61, "Tooling", "Machining Tooling cost", tooling_costs["machining_tooling"], "INR", "1 set"),
        _row(62, "Tooling", "Gauges Cost", tooling_costs["gauges"], "INR", "2 set"),
        _row(63, "Tooling", "Compression Test", tooling_costs["compression_test"], "INR", "1 set"),
        _row(64, "Tooling", "CT Scan Cost (One Time)", tooling_costs["ct_scan"], "INR", "As applicable"),
        _row(65, "Tooling", "TOTAL Tooling Cost INR", tooling_costs["total"], "INR", f"factor {tooling_costs['complexity_factor']}"),
    ]
    
    # 6. Fluctuation Range driven by metal volatility and process variation.
    range_pct = max(0.04, props.get("volatility", 0.05))
    fluctuation_range = {
        "min": round(total_unit_cost * (1 - range_pct), 2),
        "max": round(total_unit_cost * (1 + range_pct), 2),
        "percent": round(range_pct * 100, 1)
    }
    
    return {
        "material_cost": round(material_cost, 2),
        "machine_cost": round(machine_cost_inr / 83.5, 2),
        "amortization": round(amortization_cost, 2),
        "port_cost": round(port_cost, 2),
        "total_unit_cost": round(total_unit_cost, 2),
        "per_part_cost": round(total_unit_cost, 2),
        "annual_volume": production_qty,
        "alloy": metal,
        "market_price": round(market_price, 2),
        "spreadsheet_constants": QUOTE_CONSTANTS,
        "tooling_rows_58_60": TOOLING_ROWS_58_60,
        "quote_sheet_rows": quote_sheet_rows,
        "tooling_estimate_inr": round(tooling_costs["total"], 2),
        "tooling_costs": tooling_costs,
        "costing_weight_kg": round(costing_weight_kg, 4),
        "gross_melt_kg": round(gross_melt_kg, 4),
        "yield_factor": round(yield_factor, 4),
        "inr_breakdown": {
            "Raw material": round(raw_material_total_inr, 2),
            "Machine energy / PDC": round(machine_cost_inr, 2),
            "Consumable": round(consumable_inr, 2),
            "Melting cost": round(melting_cost_inr, 2),
            "Fettling": round(fettling_inr, 2),
            "Shot blast": round(shot_blast_inr, 2),
            "Cleaning / washing": round(cleaning_inr, 2),
            "Die amortization": round(die_amortization_inr, 2),
            "Freight": round(freight_inr, 2),
            "Port / handling": round(port_cost_inr, 2),
            "R&D": round(rnd_inr, 2),
            "S&A": round(sa_inr, 2),
            "EBIT": round(ebit_inr, 2),
            "Final before tool amortization": round(final_cost_before_tool_amort_inr, 2),
        },
        "fluctuation_range": fluctuation_range,
        "machine_details": {
            "required_tonnage": round(required_tonnage, 1),
            "selected_machine": machine_tonnage,
            "cycle_time_s": round(cycle_time, 1),
            "shots_per_hour": round(shots_per_hour, 1)
        },
        "tooling_estimate": round(tooling_cost_total, 0),
        "weight_g": round(weight, 1)
    }
