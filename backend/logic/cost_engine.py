import math

# Market Rates (Refined for Industry Standards)
METAL_PROPERTIES = {
    "Aluminum_A380": {"density": 0.0027, "price_per_kg": 2.85, "injection_pressure": 80, "volatility": 0.06},
    "Zinc_ZD3": {"density": 0.0066, "price_per_kg": 3.42, "injection_pressure": 30, "volatility": 0.05},
    "Magnesium_AZ91D": {"density": 0.0018, "price_per_kg": 4.65, "injection_pressure": 60, "volatility": 0.08}
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
    
    # 1. Material Cost (Refined Foundry Model)
    weight = volume * props['density'] # grams
    weight_kg = weight / 1000
    
    SHOT_WEIGHT_MULTIPLIER = 1.50 # Incl. runners/overflows
    MELTING_LOSS_FACTOR = 1.05 # 5% oxidation/loss
    SCRAP_RECOVERY_VALUE = 0.40 # 40% of virgin price recovered
    
    shot_weight_kg = weight_kg * SHOT_WEIGHT_MULTIPLIER
    material_input_cost = shot_weight_kg * market_price * MELTING_LOSS_FACTOR
    scrap_credit = (shot_weight_kg - weight_kg) * market_price * SCRAP_RECOVERY_VALUE
    material_cost = material_input_cost - scrap_credit
    
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
    
    # 4. Tooling Cost & Amortization (Diamorization)
    base_tooling = 18000 + (max(0, machine_tonnage - 250) * 25)
    tooling_cost_total = base_tooling + (slider_count * 6500)
    amortization_cost = tooling_cost_total / production_qty
    
    # 5. Total Part Cost
    # Including HDPC Port Cost provided by user
    total_unit_cost = material_cost + machine_cost_per_part + amortization_cost + port_cost
    
    # 6. Fluctuation Range driven by metal volatility and process variation.
    range_pct = max(0.04, props.get("volatility", 0.05))
    fluctuation_range = {
        "min": round(total_unit_cost * (1 - range_pct), 2),
        "max": round(total_unit_cost * (1 + range_pct), 2),
        "percent": round(range_pct * 100, 1)
    }
    
    return {
        "material_cost": round(material_cost, 2),
        "machine_cost": round(machine_cost_per_part, 2),
        "amortization": round(amortization_cost, 2),
        "port_cost": round(port_cost, 2),
        "total_unit_cost": round(total_unit_cost, 2),
        "per_part_cost": round(total_unit_cost, 2),
        "annual_volume": production_qty,
        "alloy": metal,
        "market_price": round(market_price, 2),
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
