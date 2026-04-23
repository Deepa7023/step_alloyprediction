METAL_PROPERTIES = {
    "Aluminum_A380":    {"density": 0.00270, "price_per_kg": 2.85, "injection_pressure": 80,  "volatility": 0.06},
    "Aluminum_ADC12":   {"density": 0.00272, "price_per_kg": 2.78, "injection_pressure": 78,  "volatility": 0.06},
    "Aluminum_A356":    {"density": 0.00268, "price_per_kg": 3.05, "injection_pressure": 72,  "volatility": 0.07},
    "Aluminum_6061":    {"density": 0.00270, "price_per_kg": 3.25, "injection_pressure": 70,  "volatility": 0.07},
    "Zinc_ZD3":         {"density": 0.00660, "price_per_kg": 3.42, "injection_pressure": 30,  "volatility": 0.05},
    "Zinc_Zamak5":      {"density": 0.00670, "price_per_kg": 3.55, "injection_pressure": 32,  "volatility": 0.05},
    "Magnesium_AZ91D":  {"density": 0.00180, "price_per_kg": 4.65, "injection_pressure": 60,  "volatility": 0.08},
    "Magnesium_AM60B":  {"density": 0.00179, "price_per_kg": 4.90, "injection_pressure": 58,  "volatility": 0.08},
    "Copper_Brass":     {"density": 0.00850, "price_per_kg": 8.70, "injection_pressure": 95,  "volatility": 0.09},
    "Steel_Stainless":  {"density": 0.00780, "price_per_kg": 2.15, "injection_pressure": 110, "volatility": 0.06},
}

# Alloy-specific Indian market prices (INR/kg)
# Based on LME spot + India import duty + local dealer premium
_ALLOY_PRICE_INR = {
    "Aluminum_A380":   215,
    "Aluminum_ADC12":  210,
    "Aluminum_A356":   228,
    "Aluminum_6061":   250,
    "Zinc_ZD3":        272,
    "Zinc_Zamak5":     288,
    "Magnesium_AZ91D": 390,
    "Magnesium_AM60B": 412,
    "Copper_Brass":    685,
    "Steel_Stainless": 162,
}

# HPDC machine hourly rates in INR (depreciation + power + maintenance, no labour)
# Source: AIFA / ACMA India benchmarks
_MACHINE_RATES_INR = [
    {"limit": 250,  "rate_inr":  3_500},
    {"limit": 500,  "rate_inr":  5_800},
    {"limit": 850,  "rate_inr":  9_200},
    {"limit": 1250, "rate_inr": 14_500},
    {"limit": 2000, "rate_inr": 24_000},
    {"limit": 4000, "rate_inr": 42_000},
]

# Die life (shots before major refurbishment) — varies by alloy thermal load
def _die_life(metal: str) -> int:
    if "Zinc" in metal:       return 500_000
    if "Magnesium" in metal:  return  80_000
    if "Copper" in metal:     return  30_000
    if "Steel" in metal:      return  20_000
    if "ADC12" in metal:      return 120_000
    return 100_000  # Aluminum A380 / A356 / 6061

QUOTE_CONSTANTS = {
    "runner_overflow_percent":      8.0,
    "scrap_percent":                3.0,
    "melting_process_loss_percent": 6.0,
    "rnd_percent":                  4.0,
    "sa_percent":                   6.1,
    "ebit_percent":                10.0,
    "consumable_inr":               8.0,
    "melting_cost_inr_per_kg":     14.0,
    "shot_blast_inr_per_kg":        7.0,
    "cleaning_washing_inr":         5.0,
    "labour_rate_inr_per_hour":  1_800,   # operator + material handler + QC support
    "fettling_time_minutes":        5.0,
    "freight_rate_inr_per_kg":      0.0,
    "credit_cost_inr":             75.0,
}

TOOLING_ROWS_58_60 = [
    {"row": 58, "label": "HPDC Die cost",    "quantity": 1, "unit": "set"},
    {"row": 59, "label": "Trimming Die cost","quantity": 1, "unit": "set"},
    {"row": 60, "label": "Fixture Cost",     "quantity": 2, "unit": "set"},
]


def _row(row, section, label, value=0.0, unit="INR", note="", code=""):
    return {
        "row": row, "section": section, "label": label,
        "code": code, "value": round(float(value or 0), 2),
        "unit": unit, "note": note,
    }


def _hpdc_die_cost_inr(projected_area_mm2: float, machine_tonnage: int, slider_count: int) -> float:
    """
    Die cost driven by cavity projected area and machine tonnage.
    Area scaling: cost ∝ area^0.65 (larger die needs more steel + machining hours
    but not linearly — larger blocks share setup cost).
    Reference: 50 cm² die ≈ ₹10 lakh (250 T single-cavity, no sliders).
    """
    area_cm2 = max(projected_area_mm2 / 100.0, 5.0)
    base = 1_000_000 * (area_cm2 / 50.0) ** 0.65
    # Heavier machines need thicker, harder die steel → premium
    tonnage_premium = max(0, machine_tonnage - 500) * 250
    # Each slider adds side core + ejector mechanism + EDM machining
    slider_add = slider_count * 200_000
    return max(base + tonnage_premium + slider_add, 800_000)


def _tooling_costs(projected_area: float, machine_tonnage: int, slider_count: int, metal: str) -> dict:
    hpdc_die        = _hpdc_die_cost_inr(projected_area, machine_tonnage, slider_count)
    trimming_die    = hpdc_die * 0.18
    fixture         = hpdc_die * 0.08 * 2     # 2 sets
    machining_tool  = hpdc_die * 0.10
    gauges          = hpdc_die * 0.05 * 2     # 2 sets
    compression     = hpdc_die * 0.025
    ct_scan         = hpdc_die * 0.015 if projected_area > 25_000 else 0.0
    total           = hpdc_die + trimming_die + fixture + machining_tool + gauges + compression + ct_scan
    area_cm2        = max(projected_area / 100.0, 5.0)
    return {
        "hpdc_die":         round(hpdc_die, 2),
        "trimming_die":     round(trimming_die, 2),
        "fixture":          round(fixture, 2),
        "machining_tooling":round(machining_tool, 2),
        "gauges":           round(gauges, 2),
        "compression_test": round(compression, 2),
        "ct_scan":          round(ct_scan, 2),
        "total":            round(total, 2),
        "die_life_shots":   _die_life(metal),
        "complexity_factor":round(area_cm2 / 50.0, 4),
    }


def calculate_hpdc_cost(
    traits, metal, annual_volume, sliders,
    location_multiplier=1.0, port_cost=0.0
):
    INR_RATE = 83.5

    if metal not in METAL_PROPERTIES:
        metal = "Aluminum_A380"

    props         = METAL_PROPERTIES[metal]
    production_qty = max(1, int(annual_volume or 1))
    slider_count   = max(0, int(sliders or 0))
    port_cost      = max(0.0, float(port_cost or 0.0))
    volume         = traits.get("volume", 0)
    projected_area = traits.get("projected_area", 0)
    dimensions     = traits.get("dimensions") or {}
    max_dim        = max([float(v or 0) for v in dimensions.values()] or [0])

    if max_dim > 5000 or projected_area > 5_000_000 or volume > 1_000_000_000:
        raise ValueError(
            "GEOMETRY_SCALE_ERROR: CAD dimensions outside realistic part limits. "
            "Export file in mm or upload a clean STL/STEP."
        )

    # ── 1. Weight ────────────────────────────────────────────────────────────
    weight_override = traits.get("casting_weight_g_override")
    weight_g  = float(weight_override) if weight_override else volume * props["density"]
    weight_kg = weight_g / 1000.0

    yield_factor      = 1.0 / (1.0 - (QUOTE_CONSTANTS["runner_overflow_percent"] + QUOTE_CONSTANTS["scrap_percent"]) / 100.0)
    gross_melt_kg     = weight_kg * yield_factor
    costing_weight_kg = gross_melt_kg * (1.0 + QUOTE_CONSTANTS["melting_process_loss_percent"] / 100.0)

    # ── 2. Material cost ─────────────────────────────────────────────────────
    alloy_price_inr   = _ALLOY_PRICE_INR.get(metal, 215)
    material_cost_inr = costing_weight_kg * alloy_price_inr

    # ── 3. Machine selection (clamping force) ────────────────────────────────
    force_kn       = projected_area * props.get("injection_pressure", 80) / 1000.0
    force_tonne    = force_kn / 9.81
    req_tonnage    = force_tonne * 1.40

    machine_rate_inr = _MACHINE_RATES_INR[-1]["rate_inr"]
    machine_tonnage  = _MACHINE_RATES_INR[-1]["limit"]
    for m in _MACHINE_RATES_INR:
        if req_tonnage <= m["limit"]:
            machine_rate_inr = m["rate_inr"]
            machine_tonnage  = m["limit"]
            break

    # ── 4. Cycle time ────────────────────────────────────────────────────────
    # Solidification time ∝ weight^0.45 (empirical fit to HPDC production data)
    cooling_s  = 0.42 * max(weight_g, 1.0) ** 0.45
    cycle_s    = 18.0 + cooling_s + slider_count * 4.0
    shots_hr   = 3600.0 / cycle_s

    # ── 5. Machine conversion cost ───────────────────────────────────────────
    # Machine rate (INR/hr) + operator+support labour (INR/hr), location adjusted
    hourly_inr     = machine_rate_inr * location_multiplier + QUOTE_CONSTANTS["labour_rate_inr_per_hour"]
    machine_cost_inr = hourly_inr / shots_hr

    # ── 6. Other conversion costs ────────────────────────────────────────────
    consumable_inr   = QUOTE_CONSTANTS["consumable_inr"]
    melting_cost_inr = costing_weight_kg * QUOTE_CONSTANTS["melting_cost_inr_per_kg"]
    fettling_inr     = (QUOTE_CONSTANTS["fettling_time_minutes"] / 60.0) * QUOTE_CONSTANTS["labour_rate_inr_per_hour"]
    shot_blast_inr   = costing_weight_kg * QUOTE_CONSTANTS["shot_blast_inr_per_kg"]
    cleaning_inr     = QUOTE_CONSTANTS["cleaning_washing_inr"]

    # ── 7. Tooling & amortization ────────────────────────────────────────────
    tc               = _tooling_costs(projected_area, machine_tonnage, slider_count, metal)
    die_life         = tc["die_life_shots"]
    die_amort_inr    = tc["total"] / die_life           # per-shot amortization

    freight_inr  = costing_weight_kg * QUOTE_CONSTANTS["freight_rate_inr_per_kg"]
    port_cost_inr = port_cost * INR_RATE
    credit_inr   = QUOTE_CONSTANTS["credit_cost_inr"]

    # ── 8. Totals & margins ──────────────────────────────────────────────────
    raw_total_inr  = material_cost_inr
    conv_total_inr = machine_cost_inr + consumable_inr + melting_cost_inr + fettling_inr + shot_blast_inr + cleaning_inr
    others_inr     = credit_inr

    subtotal_inr   = raw_total_inr + conv_total_inr + others_inr + die_amort_inr + freight_inr + port_cost_inr

    rnd_inr   = subtotal_inr * QUOTE_CONSTANTS["rnd_percent"]  / 100.0
    sa_inr    = subtotal_inr * QUOTE_CONSTANTS["sa_percent"]   / 100.0
    ebit_inr  = subtotal_inr * QUOTE_CONSTANTS["ebit_percent"] / 100.0

    total_inr = subtotal_inr + rnd_inr + sa_inr + ebit_inr

    # ── 9. Quote sheet rows ──────────────────────────────────────────────────
    quote_sheet_rows = [
        _row(4,  "Part",             "PART NAME",                      0,                  "",       "Uploaded CAD file"),
        _row(5,  "Part",             "PDC M/C Tonnage",                machine_tonnage,    "T"),
        _row(6,  "Part",             "Cavity",                         1,                  "nos"),
        _row(8,  "Raw material",     "Volume",                         volume,             "mm3"),
        _row(8,  "Raw material",     "Projected area",                 projected_area,     "mm2",    code="P.A."),
        _row(9,  "Raw material",     "EX. Rate",                       INR_RATE,           "INR/USD"),
        _row(10, "Raw material",     "Casting Weight",                 weight_kg,          "kg"),
        _row(11, "Raw material",     "Gross Weight incl. Runner+Scrap",gross_melt_kg,      "kg",     f"{QUOTE_CONSTANTS['runner_overflow_percent']+QUOTE_CONSTANTS['scrap_percent']}%"),
        _row(11, "Raw material",     "Costing Weight incl. Melt Loss", costing_weight_kg,  "kg",     f"{QUOTE_CONSTANTS['melting_process_loss_percent']}%"),
        _row(12, "Raw material",     "Alloy Price/kg",                 alloy_price_inr,    "INR/kg"),
        _row(13, "Raw material",     "Cost of Raw Materials",          raw_total_inr,      "INR"),
        _row(14, "Raw material",     "Alloy Cost",                     raw_total_inr,      "INR"),
        _row(15, "Raw material",     "BOP",                            0,                  "INR"),
        _row(16, "Raw material",     "Job Work",                       0,                  "INR"),
        _row(17, "Raw material",     "Total",                          raw_total_inr,      "INR",    code="A"),
        _row(19, "Conversion",       "PDC Machine",                    machine_cost_inr,   "INR"),
        _row(20, "Conversion",       "Consumable",                     consumable_inr,     "INR"),
        _row(21, "Conversion",       "Melting Cost",                   melting_cost_inr,   "INR"),
        _row(22, "Conversion",       "Trimming",                       0,                  "INR"),
        _row(23, "Conversion",       "Fettling",                       fettling_inr,       "INR",    f"{QUOTE_CONSTANTS['fettling_time_minutes']} min / 60 x labour"),
        _row(24, "Conversion",       "Shot Blast",                     shot_blast_inr,     "INR"),
        _row(25, "Conversion",       "Xray",                           0,                  "INR"),
        _row(26, "Conversion",       "VMC",                            0,                  "INR"),
        _row(27, "Conversion",       "Cleaning/Washing",               cleaning_inr,       "INR"),
        _row(28, "Conversion",       "Tool Maint.",                    0,                  "INR"),
        _row(29, "Conversion",       "Sp Hand QA",                     0,                  "INR"),
        _row(30, "Conversion",       "Compression Test",               0,                  "INR"),
        _row(31, "Conversion",       "Total",                          conv_total_inr,     "INR",    code="B"),
        _row(33, "Others",           "ICC",                            0,                  "INR"),
        _row(34, "Others",           "Credit Costs",                   credit_inr,         "INR",    "12%"),
        _row(35, "Others",           "Insurance",                      0,                  "INR",    "0.50%"),
        _row(36, "Others",           "ACD Backup",                     0,                  "INR"),
        _row(37, "Others",           "Licence Cost",                   0,                  "INR"),
        _row(38, "Others",           "Rejection",                      0,                  "INR",    "5%"),
        _row(39, "Others",           "YOY Reduction",                  0,                  "INR"),
        _row(40, "Others",           "Total",                          others_inr,         "INR",    code="C"),
        _row(41, "Packing/Margins",  "Packing",                        0,                  "INR",    code="D"),
        _row(42, "Packing/Margins",  "Over Heads (R&D+S&A)",           rnd_inr + sa_inr,  "INR",    f"{QUOTE_CONSTANTS['rnd_percent']+QUOTE_CONSTANTS['sa_percent']}%", code="E"),
        _row(43, "Packing/Margins",  "Profit (EBIT)",                  ebit_inr,           "INR",    f"{QUOTE_CONSTANTS['ebit_percent']}%", code="F"),
        _row(44, "Packing/Margins",  "Freight (DAP VC Noida)",         freight_inr,        "INR",    code="G"),
        _row(46, "Summary",          "Cost of Raw Material",           raw_total_inr,      "INR",    code="A"),
        _row(47, "Summary",          "Conversion Cost",                conv_total_inr,     "INR",    code="B"),
        _row(48, "Summary",          "Others",                         others_inr,         "INR",    code="C"),
        _row(49, "Summary",          "Packing",                        0,                  "INR",    code="D"),
        _row(50, "Summary",          "Overheads",                      rnd_inr + sa_inr,  "INR",    code="E"),
        _row(51, "Summary",          "Profit",                         ebit_inr,           "INR",    code="F"),
        _row(52, "Summary",          "Freight",                        freight_inr,        "INR",    code="G"),
        _row(55, "Summary",          "Tool Amortization / part",       die_amort_inr,      "INR"),
        _row(56, "Summary",          "Final Cost incl. Tooling",       total_inr,          "INR"),
        _row(58, "Tooling",          "HPDC Die cost",                  tc["hpdc_die"],     "INR",    "1 set"),
        _row(59, "Tooling",          "Trimming Die cost",              tc["trimming_die"], "INR",    "1 set"),
        _row(60, "Tooling",          "Fixture Cost",                   tc["fixture"],      "INR",    "2 set"),
        _row(61, "Tooling",          "Machining Tooling",              tc["machining_tooling"], "INR","1 set"),
        _row(62, "Tooling",          "Gauges Cost",                    tc["gauges"],       "INR",    "2 set"),
        _row(63, "Tooling",          "Compression Test",               tc["compression_test"], "INR","1 set"),
        _row(64, "Tooling",          "CT Scan (One Time)",             tc["ct_scan"],      "INR",    "As applicable"),
        _row(65, "Tooling",          "TOTAL Tooling Cost",             tc["total"],        "INR",    f"die life {die_life:,} shots"),
    ]

    range_pct = max(0.04, props.get("volatility", 0.05))
    total_usd = total_inr / INR_RATE

    return {
        "material_cost":       round(material_cost_inr / INR_RATE, 2),
        "machine_cost":        round(machine_cost_inr   / INR_RATE, 2),
        "amortization":        round(die_amort_inr      / INR_RATE, 2),
        "port_cost":           round(port_cost, 2),
        "total_unit_cost":     round(total_usd, 2),
        "per_part_cost":       round(total_usd, 2),
        "annual_volume":       production_qty,
        "alloy":               metal,
        "market_price":        round(props["price_per_kg"], 2),
        "alloy_price_inr":     alloy_price_inr,
        "spreadsheet_constants": {**QUOTE_CONSTANTS, "alloy_price_inr_per_kg": alloy_price_inr, "die_life_shots": die_life},
        "tooling_rows_58_60":  TOOLING_ROWS_58_60,
        "quote_sheet_rows":    quote_sheet_rows,
        "tooling_estimate_inr":round(tc["total"], 2),
        "tooling_costs":       tc,
        "costing_weight_kg":   round(costing_weight_kg, 4),
        "gross_melt_kg":       round(gross_melt_kg, 4),
        "yield_factor":        round(yield_factor, 4),
        "inr_breakdown": {
            "Raw material":              round(raw_total_inr, 2),
            "Machine energy / PDC":      round(machine_cost_inr, 2),
            "Consumable":                round(consumable_inr, 2),
            "Melting cost":              round(melting_cost_inr, 2),
            "Fettling":                  round(fettling_inr, 2),
            "Shot blast":                round(shot_blast_inr, 2),
            "Cleaning / washing":        round(cleaning_inr, 2),
            "Die amortization":          round(die_amort_inr, 2),
            "Freight":                   round(freight_inr, 2),
            "Port / handling":           round(port_cost_inr, 2),
            "R&D":                       round(rnd_inr, 2),
            "S&A":                       round(sa_inr, 2),
            "EBIT":                      round(ebit_inr, 2),
            "Total":                     round(total_inr, 2),
        },
        "fluctuation_range": {
            "min":     round(total_usd * (1 - range_pct), 2),
            "max":     round(total_usd * (1 + range_pct), 2),
            "percent": round(range_pct * 100, 1),
        },
        "machine_details": {
            "required_tonnage": round(req_tonnage, 1),
            "selected_machine": machine_tonnage,
            "machine_rate_inr": machine_rate_inr,
            "cycle_time_s":     round(cycle_s, 1),
            "shots_per_hour":   round(shots_hr, 1),
        },
        "tooling_estimate": round(tc["total"] / INR_RATE, 0),
        "weight_g":         round(weight_g, 1),
    }
