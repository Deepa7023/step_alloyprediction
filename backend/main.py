from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import time
import logging
import json
from typing import Optional
from pydantic import BaseModel

# ==============================
# IMPORTS
# ==============================
if __package__:
    from .logic.cad_analyzer import analyze_cad
    from .logic.prediction_engine import infer_manufacturing_inputs
    from .logic.ai_integrations import ai_hub
    from .logic.market_fetcher import market_fetcher, CURRENCY_SYMBOLS, CURRENCY_LABELS
    from .logic.db import save_estimate, get_history, delete_estimate, get_market_history
else:
    from logic.cad_analyzer import analyze_cad
    from logic.prediction_engine import infer_manufacturing_inputs
    from logic.ai_integrations import ai_hub
    from logic.market_fetcher import market_fetcher, CURRENCY_SYMBOLS, CURRENCY_LABELS
    from logic.db import save_estimate, get_history, delete_estimate, get_market_history

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================
# APP SETUP
# ==============================
app = FastAPI(title="HPDC Cost & Alloy Intelligence API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ==============================
# MODELS
# ==============================
class ChatMessage(BaseModel):
    message: str
    context: Optional[dict] = None


# ==============================
# HEALTH
# ==============================
@app.get("/api/health")
async def health():
    return {"status": "healthy", "version": "3.0.0", "timestamp": time.time()}


# =========================================================
# ✅ MAIN ENDPOINT — THIS IS WHERE EVERYTHING WAS FIXED
# =========================================================
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
        # -------------------------------
        # 1. Save uploaded file
        # -------------------------------
        filename = f"agent_{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        with open(file_path, "wb") as buf:
            buf.write(await file.read())

        # -------------------------------
        # 2. CAD ANALYSIS (PURE GEOMETRY)
        # -------------------------------
        analysis_result = analyze_cad(file_path)
        if "error" in analysis_result:
            raise HTTPException(status_code=500, detail=analysis_result["error"])

        traits = analysis_result["traits"]

        # -------------------------------
        # 3. HPDC MANUFACTURING + COST LOGIC
        #    ✅ THIS CALL ALREADY USES cost_engine.py
        # -------------------------------
        assumptions = infer_manufacturing_inputs(
            traits=traits,
            detected_metal=analysis_result.get("detected_metal"),
            requested_metal=metal,
            requested_volume=annual_volume,
            requested_sliders=sliders,
            requested_port_cost=port_cost,
            location_name=location_name,
        )

        # ✅ ✅ ✅ THIS IS THE CRITICAL FIX
        # ✅ DO NOT RECOMPUTE COST ANYWHERE ELSE
        cost_report = assumptions["costing"]

        # -------------------------------
        # 4. FX / MARKET DATA
        # -------------------------------
        fx_rates = market_fetcher.get_exchange_rates()
        exchange_rate = fx_rates.get("INR", 83.5)

        cost_report["exchange_rate"] = exchange_rate
        cost_report["unit_cost_inr"] = round(cost_report["total_cost"] * exchange_rate, 2)
        cost_report["prices_by_currency"] = {
            c: round(cost_report["total_cost"] * fx_rates.get(c, 1.0), 4)
            for c in fx_rates
        }

        # -------------------------------
        # 5. FINAL RESPONSE
        # -------------------------------
        agent_report = {
            "file": file.filename,
            "manufacturing_assumptions": assumptions,
            "technical_matrix": traits,  # CAD truth (reference only)
            "cost_estimation": cost_report,  # ✅ HPDC‑adjusted cost
            "engine": analysis_result.get("engine"),
        }

        agent_report["ai_insight"] = ai_hub.generate_quote_insight(agent_report)
        agent_report["ai_providers"] = ai_hub.provider_status()

        estimate_id = str(uuid.uuid4())
        save_estimate(estimate_id, file.filename, agent_report, file_path)
        agent_report["id"] = estimate_id

        return {"status": "success", "agent_report": agent_report}

    except Exception as e:
        logger.error(f"Error in agent_process: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==============================
# OTHER ENDPOINTS (UNCHANGED)
# ==============================
@app.get("/api/history")
async def get_history_api():
    return {"history": get_history()}


@app.delete("/api/history/{estimate_id}")
async def delete_history_api(estimate_id: str):
    delete_estimate(estimate_id)
    return {"status": "success"}


@app.get("/api/market-history")
async def get_market_history_api(limit: int = 100):
    return {"history": get_market_history(limit)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
``
