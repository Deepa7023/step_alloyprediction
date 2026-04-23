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
    die_amortization_inr = QUOTE_CONSTANTS["die_cost_inr"] / QUOTE_CONSTANTS["die_life_shots"]
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
    total_unit_cost = total_unit_cost_inr / 83.5
    tooling_cost_total = QUOTE_CONSTANTS["die_cost_inr"] / 83.5
    amortization_cost = die_amortization_inr / 83.5
    material_cost = material_cost_inr / 83.5
    
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
        "quote_basis": "Render-light spreadsheet costing",
        "spreadsheet_constants": QUOTE_CONSTANTS,
        "tooling_rows_58_60": TOOLING_ROWS_58_60,
        "tooling_estimate_inr": round(QUOTE_CONSTANTS["die_cost_inr"], 2),
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
