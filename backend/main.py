from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import time
import logging
import json
from typing import Optional
from pydantic import BaseModel

if __package__:
    from .logic.cad_analyzer import analyze_cad
    from .logic.ai_integrations import ai_hub
    from .logic.cost_engine import calculate_hpdc_cost
    from .logic.market_fetcher import market_fetcher, CURRENCY_SYMBOLS, CURRENCY_LABELS
    from .logic.prediction_engine import infer_manufacturing_inputs
    from .logic.db import save_estimate, get_history, delete_estimate, get_market_history
else:
    from logic.cad_analyzer import analyze_cad
    from logic.ai_integrations import ai_hub
    from logic.cost_engine import calculate_hpdc_cost
    from logic.market_fetcher import market_fetcher, CURRENCY_SYMBOLS, CURRENCY_LABELS
    from logic.prediction_engine import infer_manufacturing_inputs
    from logic.db import save_estimate, get_history, delete_estimate, get_market_history

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="HPDC Cost & Alloy Intelligence API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


class ChatMessage(BaseModel):
    message: str
    context: Optional[dict] = None


def _chat_context_summary(context: Optional[dict]) -> str:
    if not context:
        return ""

    safe_context = dict(context)
    technical = safe_context.get("technical_matrix")
    if isinstance(technical, dict):
        technical = dict(technical)
        technical.pop("preview_mesh", None)
        safe_context["technical_matrix"] = technical

    try:
        text = json.dumps(safe_context, indent=2, default=str)
    except Exception:
        text = str(safe_context)

    return text[:7000]


@app.get("/api/health")
async def health():
    return {"status": "healthy", "version": "3.0.0", "timestamp": time.time()}


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
        filename = f"agent_{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        with open(file_path, "wb") as buf:
            buf.write(await file.read())

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
        active_location_multiplier = location_multiplier or next(
            (loc.get("multiplier", 1.0) for loc in market_fetcher.get_location_indices() if loc.get("name") == location_name),
            1.0,
        )

        live_prices = market_fetcher.get_live_prices()
        selected_metal = live_prices.get(active_metal) or live_prices["Aluminum_A380"]
        live_price = selected_metal.get("current_price", 2.8)
        is_live = bool(selected_metal.get("is_live"))

        location_price = market_fetcher.get_location_adjusted_price(live_price, location_name, is_live=is_live)
        location_price_table = market_fetcher.get_location_price_table(live_price, is_live=is_live)
        fx_rates = market_fetcher.get_exchange_rates()
        exchange_rate = fx_rates.get("INR", 83.5)

        cost_report = calculate_hpdc_cost(
            traits, active_metal, active_volume, active_sliders, active_location_multiplier,
            live_price_per_kg=location_price["location_adjusted_usd_per_kg"],
            port_cost=active_port_cost,
        )
        cost_report["exchange_rate"] = exchange_rate
        cost_report["unit_cost_inr"] = round(cost_report["total_unit_cost"] * exchange_rate, 2)
        cost_report["prices_by_currency"] = {
            c: round(cost_report["total_unit_cost"] * fx_rates.get(c, 1.0), 4) for c in fx_rates
        }
        cost_report["material_price_basis"] = "LIVE_MARKET" if is_live else "REFERENCE_NOT_LIVE"

        agent_report = {
            "file": file.filename,
            "manufacturing_assumptions": assumptions,
            "technical_matrix": traits,
            "cost_estimation": cost_report,
            "market_snapshot": {
                "metal": active_metal,
                "spot_price_usd": live_price,
                "live_spot_price_usd": live_price if is_live else None,
                "reference_price_usd": None if is_live else live_price,
                "location_adjusted_price_usd": location_price["location_adjusted_usd_per_kg"],
                "live_location_adjusted_price_usd": location_price["location_adjusted_usd_per_kg"] if is_live else None,
                "reference_location_adjusted_price_usd": None if is_live else location_price["location_adjusted_usd_per_kg"],
                "regional_premium_percent": location_price["regional_premium_percent"],
                "estimated_freight_usd_per_kg": location_price["estimated_freight_usd_per_kg"],
                "price_model": location_price["method"],
                "is_live_metal_price": is_live,
                "spot_price_inr": round(live_price * exchange_rate, 2),
                "location_adjusted_price_inr": round(location_price["location_adjusted_usd_per_kg"] * exchange_rate, 2),
                "price_source": selected_metal.get("source"),
                "price_status": selected_metal.get("status"),
                "price_as_of": selected_metal.get("as_of"),
                "pricing_note": market_fetcher.cache.get("pricing_note"),
                "exchange_rate": round(exchange_rate, 4),
                "fx_rates": fx_rates,
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


@app.post("/api/chat")
async def chat(body: ChatMessage):
    """Live chatbot powered by Groq — short, to-the-point answers about HPDC and alloy pricing."""
    import os
    import requests as req

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    if not GROQ_API_KEY:
        return {"reply": "AI chat not configured. Add GROQ_API_KEY to enable the assistant.", "provider": "none"}

    context_str = _chat_context_summary(body.context)
    context_block = (
        "\n\nUPLOADED_PART_CONTEXT_JSON:\n"
        f"{context_str}\n\n"
        "Use this context when the user asks about their uploaded file, quote, geometry, material, cost, "
        "location, assumptions, risks, or recommendations. If a requested detail is missing, say it is not available. "
        "Do not invent hidden file contents."
        if context_str else
        "\n\nNo uploaded CAD/report context is attached yet. You can still answer general questions clearly."
    )

    system = (
        "You are AlloyBot, an expert assistant for HPDC (High-Pressure Die Casting) cost estimation, "
        "alloy properties, metal prices, and manufacturing. "
        "Give short, precise, expert answers — 2-4 sentences max unless a list is needed. "
        "Always be factual and grounded. You have live market awareness."
        + context_str
    )

    try:
        system = (
            "You are AlloyBot, an efficient all-purpose assistant for engineering, CAD, HPDC cost estimation, "
            "alloys, metal prices, manufacturing, and general user questions. "
            "Answer directly and to the point. Prefer 2-5 concise sentences or a short bullet list. "
            "When uploaded-part context is present, use it as the highest-priority source for questions about the user's file or quote. "
            "For unrelated general questions, answer normally."
            + context_block
        )

        resp = req.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": GROQ_MODEL,
                "temperature": 0.3,
                "max_tokens": 250,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": body.message},
                ],
            },
            timeout=10,
        )
        resp.raise_for_status()
        reply = resp.json()["choices"][0]["message"]["content"].strip()
        return {"reply": reply, "provider": "groq", "model": GROQ_MODEL}
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return {"reply": "I'm having trouble connecting right now. Please try again shortly.", "provider": "error"}


@app.get("/api/market-data")
async def get_market_data():
    live_prices = market_fetcher.get_live_prices()
    locations = market_fetcher.get_location_indices()
    fx_rates = market_fetcher.get_exchange_rates()
    exchange_rate = fx_rates.get("INR", 83.5)
    return {
        "metals": list(live_prices.keys()),
        "plant_locations": locations,
        "current_base_rates": live_prices,
        "location_price_tables": {
            metal: market_fetcher.get_location_price_table(data.get("current_price", 0), is_live=bool(data.get("is_live")))
            for metal, data in live_prices.items()
        },
        "exchange_rate": exchange_rate,
        "fx_rates": fx_rates,
        "currency_symbols": CURRENCY_SYMBOLS,
        "currency_labels": CURRENCY_LABELS,
        "pricing_status": market_fetcher.cache.get("pricing_status"),
        "pricing_note": market_fetcher.cache.get("pricing_note"),
        "provider_error": market_fetcher.cache.get("provider_error"),
        "exchange_source": market_fetcher.cache.get("fx_source"),
        "exchange_as_of": market_fetcher.cache.get("fx_as_of"),
        "last_updated": market_fetcher.cache["last_updated"],
    }


@app.get("/api/market-data/fx-rates")
async def get_fx_rates():
    rates = market_fetcher.get_exchange_rates()
    return {
        "rates": rates,
        "symbols": CURRENCY_SYMBOLS,
        "labels": CURRENCY_LABELS,
        "source": market_fetcher.cache.get("fx_source", "REFERENCE_FX"),
        "as_of": market_fetcher.cache.get("fx_as_of"),
    }


@app.get("/api/ai/status")
async def get_ai_status():
    return {"providers": ai_hub.provider_status()}


@app.get("/api/history")
async def get_history_api():
    try:
        return {"history": get_history()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/history/{estimate_id}")
async def delete_history_api(estimate_id: str):
    try:
        delete_estimate(estimate_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market-history")
async def get_market_history_api(limit: int = 100):
    try:
        return {"history": get_market_history(limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
