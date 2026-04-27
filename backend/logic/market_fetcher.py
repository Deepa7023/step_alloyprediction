import time
import logging
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

FX_API_URL = "https://api.frankfurter.app/latest"

from .ai_integrations import ai_hub
from .db import save_market_snapshot

logger = logging.getLogger(__name__)

CURRENCY_SYMBOLS = {"USD": "$", "INR": "₹", "EUR": "€", "CNY": "¥", "GBP": "£"}
CURRENCY_LABELS = {"USD": "US Dollar", "INR": "Indian Rupee", "EUR": "Euro", "CNY": "Chinese Yuan", "GBP": "British Pound"}
DEFAULT_FX = {"USD": 1.0, "INR": 83.5, "EUR": 0.92, "CNY": 7.24, "GBP": 0.79}

ALLOY_CATALOG = {
    "Aluminum_A380": {"base_price": 2.85, "density": 0.0027, "pressure": 80, "label": "Aluminum A380", "family": "Aluminum", "premium": 0.35},
    "Aluminum_ADC12": {"base_price": 2.78, "density": 0.00272, "pressure": 78, "label": "Aluminum ADC12", "family": "Aluminum", "premium": 0.28},
    "Aluminum_A356": {"base_price": 3.05, "density": 0.00268, "pressure": 72, "label": "Aluminum A356", "family": "Aluminum", "premium": 0.55},
    "Aluminum_6061": {"base_price": 3.25, "density": 0.00270, "pressure": 70, "label": "Aluminum 6061", "family": "Aluminum", "premium": 0.75},
    "Zinc_ZD3": {"base_price": 3.42, "density": 0.0066, "pressure": 30, "label": "Zinc ZD3 / Zamak 3", "family": "Zinc", "premium": 0.42},
    "Zinc_Zamak5": {"base_price": 3.55, "density": 0.0067, "pressure": 32, "label": "Zinc Zamak 5", "family": "Zinc", "premium": 0.55},
    "Magnesium_AZ91D": {"base_price": 4.65, "density": 0.0018, "pressure": 60, "label": "Magnesium AZ91D", "family": "Magnesium", "premium": 0.65},
    "Magnesium_AM60B": {"base_price": 4.90, "density": 0.00179, "pressure": 58, "label": "Magnesium AM60B", "family": "Magnesium", "premium": 0.90},
    "Copper_Brass": {"base_price": 8.70, "density": 0.0085, "pressure": 95, "label": "Copper / Brass casting alloy", "family": "Copper", "premium": 0.90},
    "Steel_Stainless": {"base_price": 2.15, "density": 0.0078, "pressure": 110, "label": "Steel / Stainless reference", "family": "Steel", "premium": 0.70},
}

PRICE_SANITY_RANGES = {
    "Aluminum": (1.0, 7.0),
    "Zinc": (1.0, 8.0),
    "Magnesium": (1.5, 14.0),
    "Copper": (3.0, 20.0),
    "Steel": (0.5, 8.0),
}


class MarketFetcher:
    def __init__(self):
        self.cache = {
            "metals": {
                key: {**data, "current_price": data["base_price"], "source": "REFERENCE_ALLOY_PRICE", "is_live": False}
                for key, data in ALLOY_CATALOG.items()
            },
            "last_updated": 0,
            "fx_rates": dict(DEFAULT_FX),
            "last_rate_update": 0,
            "pricing_status": "REFERENCE",
            "pricing_note": "Live prices fetched via Agentic Web Search.",
        }
        self.ttl = 3600
        self.location_market_adjustments = {
            "India (Pune Node)": {"metal_premium": 0.045, "freight": 0.08, "currency": "INR", "city": "Pune", "country": "India", "lat": 18.5204, "lon": 73.8567},
            "India (Chennai Cluster)": {"metal_premium": 0.05, "freight": 0.09, "currency": "INR", "city": "Chennai", "country": "India", "lat": 13.0827, "lon": 80.2707},
            "China (Ningbo Hub)": {"metal_premium": 0.025, "freight": 0.06, "currency": "CNY", "city": "Ningbo", "country": "China", "lat": 29.8683, "lon": 121.5440},
            "USA (Chicago/Midwest)": {"metal_premium": 0.075, "freight": 0.16, "currency": "USD", "city": "Chicago", "country": "United States", "lat": 41.8781, "lon": -87.6298},
            "Germany (Stuttgart)": {"metal_premium": 0.09, "freight": 0.18, "currency": "EUR", "city": "Stuttgart", "country": "Germany", "lat": 48.7758, "lon": 9.1829},
            "Vietnam (Hanoi)": {"metal_premium": 0.04, "freight": 0.1, "currency": "USD", "city": "Hanoi", "country": "Vietnam", "lat": 21.0278, "lon": 105.8342},
            "Mexico (Monterrey)": {"metal_premium": 0.055, "freight": 0.12, "currency": "USD", "city": "Monterrey", "country": "Mexico", "lat": 25.6866, "lon": -100.3161},
        }

    def _utc_stamp(self):
        return datetime.now(timezone.utc).isoformat()

    def _valid_market_price(self, family, price):
        try:
            value = float(price)
        except (TypeError, ValueError):
            return False
        low, high = PRICE_SANITY_RANGES.get(family, (0.5, 25.0))
        return low <= value <= high

    def get_live_prices(self):
        now = time.time()
        if now - self.cache["last_updated"] > self.ttl or self.cache["last_updated"] == 0:
            logger.info("MARKET_NODE: Starting agentic market-data sync")
            sync_success = False
            self.cache["provider_error"] = None

            family_queries = {
                family: [key for key, data in self.cache["metals"].items() if data.get("family") == family]
                for family in ["Aluminum", "Zinc", "Magnesium", "Copper", "Steel"]
            }

            try:
                for metal_query, internal_keys in family_queries.items():
                    result = ai_hub.get_agentic_market_price(metal_query)
                    raw_price = result.get("price")
                    if result.get("success") and self._valid_market_price(metal_query, raw_price):
                        for internal_key in internal_keys:
                            alloy = self.cache["metals"][internal_key]
                            price = float(raw_price) + float(alloy.get("premium", 0))
                            self.cache["metals"][internal_key].update({
                                "current_price": round(price, 4),
                                "source": "AI_AGENTIC_WEB_SEARCH",
                                "as_of": result.get("date") or self._utc_stamp(),
                                "is_live": True,
                                "source_url": result.get("source"),
                            })
                            save_market_snapshot(internal_key, round(price, 4), self.cache["fx_rates"].get("INR", 83.5))
                        sync_success = True
                    else:
                        logger.warning(f"Agentic fetch failed or invalid for {metal_query}: price={raw_price} error={result.get('error')}")
                        for internal_key in internal_keys:
                            self.cache["metals"][internal_key]["is_live"] = False
            except Exception as e:
                logger.error(f"Global market sync failed: {e}")
                self.cache["provider_error"] = str(e)

            for internal_key, m_data in self.cache["metals"].items():
                if not m_data.get("is_live"):
                    m_data.update({"current_price": m_data["base_price"], "source": "REFERENCE_ALLOY_PRICE",
                                   "as_of": self._utc_stamp(), "is_live": False})
                if not self._valid_market_price(m_data.get("family", ""), m_data.get("current_price")):
                    m_data.update({"current_price": m_data["base_price"], "source": "REFERENCE_ALLOY_PRICE",
                                   "as_of": self._utc_stamp(), "is_live": False})
                m_data["current_price"] = round(float(m_data.get("current_price") or m_data.get("base_price", 2.85)), 4)
                m_data["status"] = "LIVE_MARKET" if m_data.get("is_live") else "REFERENCE_PRICE"
                save_market_snapshot(internal_key, m_data["current_price"], self.cache["fx_rates"].get("INR", 83.5))

            self.cache["pricing_status"] = "LIVE_AGENTIC" if sync_success else "REFERENCE"
            fx = self.get_exchange_rates()
            self.cache["pricing_note"] = (
                f"Live prices via Agentic Web Search. FX: ₹{fx.get('INR', 83.5):.2f} / €{fx.get('EUR', 0.92):.3f} / ¥{fx.get('CNY', 7.24):.2f} per USD."
                if sync_success
                else "Using reference alloy prices. Configure Firecrawl/Groq for live discovery."
            )
            self.cache["last_updated"] = now

        return self.cache["metals"]

    def get_exchange_rates(self) -> dict:
        now = time.time()
        if now - self.cache.get("last_rate_update", 0) > self.ttl:
            try:
                resp = requests.get(FX_API_URL, params={"from": "USD", "to": "INR,EUR,CNY,GBP"}, timeout=5)
                resp.raise_for_status()
                data = resp.json()
                rates = data.get("rates", {})
                self.cache["fx_rates"] = {
                    "USD": 1.0,
                    "INR": float(rates.get("INR", DEFAULT_FX["INR"])),
                    "EUR": float(rates.get("EUR", DEFAULT_FX["EUR"])),
                    "CNY": float(rates.get("CNY", DEFAULT_FX["CNY"])),
                    "GBP": float(rates.get("GBP", DEFAULT_FX["GBP"])),
                }
                self.cache["fx_source"] = "FRANKFURTER"
                self.cache["fx_as_of"] = data.get("date") or self._utc_stamp()
            except Exception as e:
                logger.error(f"FX sync failed: {e}")
                self.cache.setdefault("fx_rates", dict(DEFAULT_FX))
                self.cache["fx_source"] = "REFERENCE_FX"
                self.cache["fx_as_of"] = self._utc_stamp()
            self.cache["last_rate_update"] = now
        return self.cache["fx_rates"]

    def get_exchange_rate(self) -> float:
        return self.get_exchange_rates().get("INR", 83.5)

    def get_location_record(self, location_name):
        return self.location_market_adjustments.get(
            location_name,
            {"metal_premium": 0.06, "freight": 0.12, "currency": "USD", "city": location_name, "country": "Unknown", "lat": None, "lon": None},
        )

    def get_location_adjusted_price(self, base_price_usd_per_kg, location_name, is_live=False):
        adj = self.location_market_adjustments.get(
            location_name,
            {"metal_premium": 0.06, "freight": 0.12, "currency": "USD"},
        )
        landed = base_price_usd_per_kg * (1 + adj["metal_premium"]) + adj["freight"]
        fx = self.get_exchange_rates()
        return {
            "location_adjusted_usd_per_kg": round(landed, 4),
            "regional_premium_percent": round(adj["metal_premium"] * 100, 2),
            "estimated_freight_usd_per_kg": adj["freight"],
            "currency": adj["currency"],
            "is_live_price": bool(is_live),
            "prices_by_currency": {c: round(landed * fx.get(c, 1.0), 4) for c in fx},
            "method": (
                "live spot price plus location premium and freight"
                if is_live
                else "reference alloy price plus location premium and freight; live metal quote unavailable"
            ),
        }

    def get_location_price_table(self, base_price_usd_per_kg, is_live=False):
        fx = self.get_exchange_rates()
        table = []
        for name, loc in self.location_market_adjustments.items():
            price = self.get_location_adjusted_price(base_price_usd_per_kg, name, is_live=is_live)
            table.append({
                "name": name,
                "city": loc["city"],
                "country": loc["country"],
                "lat": loc["lat"],
                "lon": loc["lon"],
                "currency": loc["currency"],
                "location_adjusted_usd_per_kg": price["location_adjusted_usd_per_kg"],
                "regional_premium_percent": price["regional_premium_percent"],
                "estimated_freight_usd_per_kg": price["estimated_freight_usd_per_kg"],
                "is_live_price": price["is_live_price"],
                "prices_by_currency": {c: round(price["location_adjusted_usd_per_kg"] * fx.get(c, 1.0), 4) for c in fx},
                "method": price["method"],
            })
        return table

    def get_location_indices(self):
        return [
            {"name": "India (Pune Node)", "multiplier": 0.82, "market_status": "STABLE", **self.location_market_adjustments["India (Pune Node)"]},
            {"name": "India (Chennai Cluster)", "multiplier": 0.85, "market_status": "STABLE", **self.location_market_adjustments["India (Chennai Cluster)"]},
            {"name": "China (Ningbo Hub)", "multiplier": 0.92, "market_status": "STABLE", **self.location_market_adjustments["China (Ningbo Hub)"]},
            {"name": "USA (Chicago/Midwest)", "multiplier": 1.55, "market_status": "HIGH_COST", **self.location_market_adjustments["USA (Chicago/Midwest)"]},
            {"name": "Germany (Stuttgart)", "multiplier": 1.70, "market_status": "PREMIUM", **self.location_market_adjustments["Germany (Stuttgart)"]},
            {"name": "Vietnam (Hanoi)", "multiplier": 0.72, "market_status": "EMERGING", **self.location_market_adjustments["Vietnam (Hanoi)"]},
            {"name": "Mexico (Monterrey)", "multiplier": 1.05, "market_status": "STABLE", **self.location_market_adjustments["Mexico (Monterrey)"]},
        ]

    def search_location(self, query):
        query = query.lower()
        return [l for l in self.get_location_indices() if query in l["name"].lower() or query in l.get("city", "").lower()]


market_fetcher = MarketFetcher()
