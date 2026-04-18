from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import time
import logging
from typing import Optional, List
from pydantic import BaseModel

if __package__:
    from .logic.cad_analyzer import analyze_cad
    from .logic.ai_integrations import ai_hub
    from .logic.cost_engine import calculate_hpdc_cost
    from .logic.market_fetcher import market_fetcher
    from .logic.prediction_engine import infer_manufacturing_inputs
else:
    from logic.cad_analyzer import analyze_cad
    from logic.ai_integrations import ai_hub
    from logic.cost_engine import calculate_hpdc_cost
    from logic.market_fetcher import market_fetcher
    from logic.prediction_engine import infer_manufacturing_inputs

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="HPDC Cost & Geometry Engine API", version="2.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Pydantic Models
class GeometryTraits(BaseModel):
    volume: float
    surface_area: float
    dimensions: dict
    projected_area: float
    topology: dict
    validation: dict
    preview_mesh: str

class CostBreakdown(BaseModel):
    material_cost: float
    machine_cost: float
    amortization: float
    total_unit_cost: float
    market_price: float
    fluctuation_range: dict
    machine_details: dict
    tooling_estimate: float
    weight_g: float

class AgentReport(BaseModel):
    file: str
    technical_matrix: GeometryTraits
    cost_estimation: dict
    market_snapshot: dict
    engine: str

@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "version": "2.0.0_FASTAPI",
        "timestamp": time.time()
    }

@app.post("/api/agent/process")
async def agent_process(
    file: UploadFile = File(...),
    metal: Optional[str] = Form(None),
    annual_volume: Optional[int] = Form(None),
    location_multiplier: Optional[float] = Form(None),
    location_name: str = Form("India (Pune Node)"),
    sliders: Optional[int] = Form(None),
    port_cost: Optional[float] = Form(None)
):
    """
    Unified Agentic Endpoint: One-Click Analysis & Estimation.
    """
    try:
        filename = f"agent_{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            
        # 1. Analyze CAD
        analysis_result = analyze_cad(file_path)
        if "error" in analysis_result:
            raise HTTPException(status_code=500, detail=analysis_result["error"])
            
        traits = analysis_result["traits"]
        assumptions = infer_manufacturing_inputs(
            traits=traits,
            detected_metal=analysis_result.get("detected_metal"),
            requested_metal=metal,
            requested_volume=annual_volume,
            requested_sliders=sliders,
            requested_port_cost=port_cost,
            location_name=location_name,
        )
        selected_location = market_fetcher.get_location_record(location_name)
        active_metal = assumptions["alloy"]
        active_volume = assumptions["annual_volume"]
        active_sliders = assumptions["sliders"]
        active_port_cost = assumptions["port_cost"]
        active_location_multiplier = location_multiplier
        if active_location_multiplier is None:
            active_location_multiplier = next(
                (
                    location.get("multiplier", 1.0)
                    for location in market_fetcher.get_location_indices()
                    if location.get("name") == location_name
                ),
                1.0,
            )
        
        # 2. Fetch Live Market Price
        live_prices = market_fetcher.get_live_prices()
        selected_metal = live_prices.get(active_metal) or live_prices["Aluminum_A380"]
        live_price = selected_metal.get('current_price', 2.8)
        is_live_metal_price = bool(selected_metal.get("is_live"))
        location_price = market_fetcher.get_location_adjusted_price(
            live_price, location_name, is_live=is_live_metal_price
        )
        location_price_table = market_fetcher.get_location_price_table(
            live_price, is_live=is_live_metal_price
        )
        exchange_rate = market_fetcher.get_exchange_rate()
        
        # 3. Calculate HPDC Cost
        cost_report = calculate_hpdc_cost(
            traits, active_metal, active_volume, active_sliders, active_location_multiplier,
            live_price_per_kg=location_price["location_adjusted_usd_per_kg"], port_cost=active_port_cost
        )
        
        # Add metadata for location and currency
        cost_report["exchange_rate"] = exchange_rate
        cost_report["unit_cost_inr"] = round(cost_report["total_unit_cost"] * exchange_rate, 2)
        cost_report["material_price_basis"] = (
            "LIVE_MARKET" if is_live_metal_price else "REFERENCE_NOT_LIVE"
        )
        
        agent_report = {
            "file": file.filename,
            "manufacturing_assumptions": assumptions,
            "technical_matrix": traits,
            "cost_estimation": cost_report,
            "market_snapshot": {
                "metal": active_metal,
                "spot_price_usd": live_price,
                "live_spot_price_usd": live_price if is_live_metal_price else None,
                "reference_price_usd": None if is_live_metal_price else live_price,
                "location_adjusted_price_usd": location_price["location_adjusted_usd_per_kg"],
                "live_location_adjusted_price_usd": location_price["location_adjusted_usd_per_kg"] if is_live_metal_price else None,
                "reference_location_adjusted_price_usd": None if is_live_metal_price else location_price["location_adjusted_usd_per_kg"],
                "regional_premium_percent": location_price["regional_premium_percent"],
                "estimated_freight_usd_per_kg": location_price["estimated_freight_usd_per_kg"],
                "price_model": location_price["method"],
                "is_live_metal_price": is_live_metal_price,
                "spot_price_inr": round(live_price * exchange_rate, 2),
                "location_adjusted_price_inr": round(location_price["location_adjusted_usd_per_kg"] * exchange_rate, 2),
                "price_source": selected_metal.get("source"),
                "price_status": selected_metal.get("status"),
                "price_as_of": selected_metal.get("as_of"),
                "pricing_note": market_fetcher.cache.get("pricing_note"),
                "exchange_rate": round(exchange_rate, 4),
                "exchange_source": market_fetcher.cache.get("fx_source"),
                "exchange_as_of": market_fetcher.cache.get("fx_as_of"),
                "location": location_name,
                "location_geodata": {
                    "city": selected_location.get("city"),
                    "country": selected_location.get("country"),
                    "lat": selected_location.get("lat"),
                    "lon": selected_location.get("lon"),
                    "currency": selected_location.get("currency"),
                },
                "location_price_table": location_price_table,
                "timestamp": time.ctime(),
            },
            "engine": analysis_result.get("engine")
        }
        agent_report["ai_insight"] = ai_hub.generate_quote_insight(agent_report)
        agent_report["ai_providers"] = ai_hub.provider_status()

        return {
            "status": "success",
            "agent_report": agent_report
        }
    except Exception as e:
        logger.error(f"Error in agent_process: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/market-data")
async def get_market_data():
    live_prices = market_fetcher.get_live_prices()
    locations = market_fetcher.get_location_indices()
    exchange_rate = market_fetcher.get_exchange_rate()
    return {
        "metals": list(live_prices.keys()),
        "plant_locations": locations,
        "current_base_rates": live_prices,
        "location_price_tables": {
            metal: market_fetcher.get_location_price_table(
                data.get("current_price", 0), is_live=bool(data.get("is_live"))
            )
            for metal, data in live_prices.items()
        },
        "exchange_rate": exchange_rate,
        "pricing_status": market_fetcher.cache.get("pricing_status"),
        "pricing_note": market_fetcher.cache.get("pricing_note"),
        "provider_error": market_fetcher.cache.get("provider_error"),
        "exchange_source": market_fetcher.cache.get("fx_source"),
        "exchange_as_of": market_fetcher.cache.get("fx_as_of"),
        "last_updated": market_fetcher.cache["last_updated"]
    }

@app.get("/api/ai/status")
async def ai_status():
    return {
        "providers": ai_hub.provider_status(),
        "notes": [
            "Set GROQ_API_KEY for Groq AI quote reasoning.",
            "Set FIRECRAWL_API_KEY for Firecrawl web market search.",
            "Set TINYFISH_API_KEY for TinyFish search cross-checking.",
        ],
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
