from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import time
import logging
import json
from typing import Optional
from pydantic import BaseModel

# ---------------- IMPORT LOGIC ----------------

if __package__:
    from .logic.cad_analyzer import analyze_cad
    from .logic.ai_integrations import ai_hub
    from .logic.cost_engine import calculate_hpdc_cost
    from .logic.market_fetcher import (
        market_fetcher,
        CURRENCY_SYMBOLS,
        CURRENCY_LABELS
    )
    from .logic.prediction_engine import infer_manufacturing_inputs
    from .logic.db import save_estimate, get_history, delete_estimate, get_market_history
    from .logic.fixed_step_registry import get_fixed_ui_output
else:
    from logic.cad_analyzer import analyze_cad
    from logic.ai_integrations import ai_hub
    from logic.cost_engine import calculate_hpdc_cost
    from logic.market_fetcher import (
        market_fetcher,
        CURRENCY_SYMBOLS,
        CURRENCY_LABELS
    )
    from logic.prediction_engine import infer_manufacturing_inputs
    from logic.db import save_estimate, get_history, delete_estimate, get_market_history
    from logic.fixed_step_registry import get_fixed_ui_output

# ---------------- APP SETUP ----------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="HPDC Cost & Alloy Intelligence API", version="3.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- MODELS ----------------

class ChatMessage(BaseModel):
    message: str
    context: Optional[dict] = None

# ---------------- HEALTH ----------------

@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "version": "3.0.1",
        "timestamp": time.time()
    }

# ---------------- MAIN CAD PROCESS ----------------

@app.post("/api/agent/process")
async def agent_process(
    file: UploadFile = File(...),
    metal: Optional[str] = Form(None),
    annual_volume: Optional[int] = Form(None),
    location_multiplier: Optional[float] = Form(None),
    location_name: str = Form("India (Pune Node)"),
    sliders: Optional[int] = Form(None),
    port_cost: Optional[float] = Form(None),
):
    try:
        # 1️⃣ Save file
        filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        with open(file_path, "wb") as buf:
            buf.write(await file.read())

        # 2️⃣ ✅ FIXED EXCEL REGISTRY CHECK (FIRST!)
        try:
            fixed_result = get_fixed_ui_output(file_path)

            logger.info("✅ Fixed CAD registry hit — returning Excel price")

            return {
                "status": "success",
                "pricing_source": "FIXED_EXCEL_REFERENCE",
                "result": fixed_result
            }

        except ValueError:
            # Not a registered CAD → continue with normal logic
            pass

        # 3️⃣ Normal agent/market pipeline
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

        active_metal = assumptions["alloy"]
        active_volume = assumptions["annual_volume"]
        active_sliders = assumptions["sliders"]
        active_port_cost = assumptions["port_cost"]

        selected_location = market_fetcher.get_location_record(location_name)

        live_prices = market_fetcher.get_live_prices()
        selected_metal = live_prices.get(active_metal) or live_prices["Aluminum_A380"]
        live_price = selected_metal.get("current_price", 2.8)
        is_live = bool(selected_metal.get("is_live"))

        location_price = market_fetcher.get_location_adjusted_price(
            live_price, location_name, is_live=is_live
        )

        fx_rates = market_fetcher.get_exchange_rates()
        exchange_rate = fx_rates.get("INR", 83.5)

        cost_report = calculate_hpdc_cost(
            traits,
            active_metal,
            active_volume,
            active_sliders,
            location_multiplier or 1.0,
            live_price_per_kg=location_price["location_adjusted_usd_per_kg"],
            port_cost=active_port_cost,
        )

        cost_report["exchange_rate"] = exchange_rate
        cost_report["unit_cost_inr"] = round(cost_report["total_unit_cost"] * exchange_rate, 2)

        response = {
            "status": "success",
            "pricing_source": "DYNAMIC_AGENT_ENGINE",
            "technical_matrix": traits,
            "manufacturing_assumptions": assumptions,
            "cost_estimation": cost_report
        }

        return response

    except Exception as e:
        logger.error(f"Error in agent_process: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ---------------- CHAT ----------------

@app.post("/api/chat")
async def chat(body: ChatMessage):
    return {"reply": "Chat unchanged", "provider": "static"}

# ---------------- HISTORY ----------------

@app.get("/api/history")
async def get_history_api():
    return {"history": get_history()}

@app.delete("/api/history/{estimate_id}")
async def delete_history_api(estimate_id: str):
    delete_estimate(estimate_id)
    return {"status": "success"}

# ---------------- RUN ----------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
