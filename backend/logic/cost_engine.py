import math

# Market Rates (Simplified simulation)
METAL_PROPERTIES = {
    "Aluminum_A380": {"density": 0.0027, "price_per_kg": 2.8, "injection_pressure": 80}, # 80 MPa
    "Zinc_ZD3": {"density": 0.0066, "price_per_kg": 3.4, "injection_pressure": 30},
    "Magnesium_AZ91D": {"density": 0.0018, "price_per_kg": 4.5, "injection_pressure": 60}
}

# Machine Tonnage Mapping (Tonne : Hourly Rate $)
MACHINE_RATES = [
    {"limit": 250, "rate": 45},
    {"limit": 500, "rate": 75},
    {"limit": 850, "rate": 110},
    {"limit": 1250, "rate": 160},
    {"limit": 2000, "rate": 280},
    {"limit": 4000, "rate": 550}
]

def calculate_hpdc_cost(traits, metal, annual_volume, sliders, location_multiplier=1.0, live_price_per_kg=None):
    """
    Calculates HPDC cost based on part traits and user parameters.
    """
    if metal not in METAL_PROPERTIES:
        metal = "A380 (Aluminum)"
        
    props = METAL_PROPERTIES[metal]
    volume = traits['volume']
    projected_area = traits['projected_area']
    
    # Use live price if provided, else fallback to static data
    market_price = live_price_per_kg if live_price_per_kg is not None else props['price_per_kg']
    
    # 1. Material Cost (Refined Foundry Model)
    volume = traits['volume']
    projected_area = traits['projected_area']
    weight = volume * props['density'] # grams
    weight_kg = weight / 1000
    
    # Runner/Gating system typically adds 30-50% to part weight in HPDC
    SHOT_WEIGHT_MULTIPLIER = 1.45 
    MELTING_LOSS_FACTOR = 1.04 # 4% oxidation/loss
    SCRAP_RECOVERY_VALUE = 0.45 # 45% of virgin price recovered from internal scrap
    
    shot_weight_kg = weight_kg * SHOT_WEIGHT_MULTIPLIER
    material_input_cost = shot_weight_kg * market_price * MELTING_LOSS_FACTOR
    scrap_credit = (shot_weight_kg - weight_kg) * market_price * SCRAP_RECOVERY_VALUE
    material_cost = material_input_cost - scrap_credit
    
    # 2. Machine Tonnage (Clamping Force)
    # Total Tonnage = (Projected Area * Injection Pressure) * SF / 10
    # Projected Area is in mm^2, Injection Pressure in MPa (N/mm^2)
    force_kn = projected_area * props.get('injection_pressure', 80) / 1000
    force_tonne = force_kn / 9.81 # Exact conversion to Metric Tonne Force
    required_tonnage = force_tonne * 1.35 # 35% Safety factor for dynamic intensification
    
    # Select Machine
    machine_rate = 45 # Default
    machine_tonnage = 250
    for m in MACHINE_RATES:
        if required_tonnage <= m['limit']:
            machine_rate = m['rate']
            machine_tonnage = m['limit']
            break
            
    # 3. Cycle Time & Labor (Refined)
    # Base: 20s + cooling time (dependent on part weight and wall thickness proxy)
    # 30s is more realistic for small parts, increasing with mass.
    cooling_time = math.sqrt(weight_kg * 1000) * 0.8 # Empirical cooling proxy
    cycle_time = 22 + cooling_time + (sliders * 4)
    shots_per_hour = 3600 / cycle_time
    
    # Labor and Energy ($15/hr energy + $30/hr labor/overhead)
    conversion_hourly_rate = (machine_rate * location_multiplier) + 45.0 
    machine_cost_per_part = conversion_hourly_rate / shots_per_hour
    
    # 4. Tooling Cost (Estimated)
    # Base Mold: $15,000 for 250T + scaling
    base_tooling = 15000 + (max(0, machine_tonnage - 250) * 22)
    tooling_cost_total = base_tooling + (sliders * 5500)
    amortization_cost = tooling_cost_total / annual_volume
    
    # 5. Total
    total_unit_cost = material_cost + machine_cost_per_part + amortization_cost
    
    return {
        "material_cost": round(material_cost, 2),
        "machine_cost": round(machine_cost_per_part, 2),
        "amortization": round(amortization_cost, 2),
        "total_unit_cost": round(total_unit_cost, 2),
        "market_price": round(market_price, 2),
        "machine_details": {
            "required_tonnage": round(required_tonnage, 1),
            "selected_machine": machine_tonnage,
            "cycle_time_s": round(cycle_time, 1),
            "shots_per_hour": round(shots_per_hour, 1)
        },
        "tooling_estimate": round(tooling_cost_total, 0),
        "weight_g": round(weight, 1)
    }
