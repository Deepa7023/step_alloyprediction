import os
import time
import logging
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("METALS_API_KEY")
METALS_API_URL = "https://api.metalpriceapi.com/v1/latest"
FX_API_URL = "https://api.frankfurter.app/latest"

logger = logging.getLogger(__name__)

class MarketFetcher:
    def __init__(self):
        # Deterministic reference values are used only when no live provider key is
        # configured. They are intentionally not randomized.
        self.cache = {
            "metals": {
                "Aluminum_A380": {
                    "base_price": 2.85,
                    "current_price": 2.85,
                    "density": 0.0027,
                    "pressure": 80,
                    "label": "Aluminum A380",
                    "source": "REFERENCE_ALLOY_PRICE",
                },
                "Zinc_ZD3": {
                    "base_price": 3.42,
                    "current_price": 3.42,
                    "density": 0.0066,
                    "pressure": 30,
                    "label": "Zinc ZD3 / Zamak",
                    "source": "REFERENCE_ALLOY_PRICE",
                },
                "Magnesium_AZ91D": {
                    "base_price": 4.65,
                    "current_price": 4.65,
                    "density": 0.0018,
                    "pressure": 60,
                    "label": "Magnesium AZ91D",
                    "source": "REFERENCE_ALLOY_PRICE",
                },
            },
            "last_updated": 0,
            "exchange_rate": 83.50,
            "last_rate_update": 0,
            "pricing_status": "REFERENCE",
            "pricing_note": "Configure METALS_API_KEY for live metal quotes.",
        }
        self.ttl = 3600
        self.location_market_adjustments = {
            "India (Pune Node)": {"metal_premium": 0.045, "freight": 0.08, "currency": "INR", "city": "Pune", "country": "India", "lat": 18.5204, "lon": 73.8567},
            "India (Chennai Cluster)": {"metal_premium": 0.05, "freight": 0.09, "currency": "INR", "city": "Chennai", "country": "India", "lat": 13.0827, "lon": 80.2707},
            "China (Ningbo Hub)": {"metal_premium": 0.025, "freight": 0.06, "currency": "CNY", "city": "Ningbo", "country": "China", "lat": 29.8683, "lon": 121.5440},
            "USA (Chicago/Midwest)": {"metal_premium": 0.075, "freight": 0.16, "currency": "USD", "city": "Chicago", "country": "United States", "lat": 41.8781, "lon": -87.6298},
            "Germany (Stuttgart)": {"metal_premium": 0.09, "freight": 0.18, "currency": "EUR", "city": "Stuttgart", "country": "Germany", "lat": 48.7758, "lon": 9.1829},
            "Vietnam (Hanoi)": {"metal_premium": 0.04, "freight": 0.1, "currency": "VND", "city": "Hanoi", "country": "Vietnam", "lat": 21.0278, "lon": 105.8342},
            "Mexico (Monterrey)": {"metal_premium": 0.055, "freight": 0.12, "currency": "MXN", "city": "Monterrey", "country": "Mexico", "lat": 25.6866, "lon": -100.3161},
        }

    def _utc_stamp(self):
        return datetime.now(timezone.utc).isoformat()

    def get_live_prices(self):
        """Fetch live prices or return deterministic reference prices."""
        now = time.time()
        should_sync = now - self.cache["last_updated"] > self.ttl or self.cache["last_updated"] == 0

        if should_sync:
            logger.info("MARKET_NODE: Syncing market prices")
            sync_success = False
            self.cache["provider_error"] = None

            try:
                if API_KEY and API_KEY != "YOUR_API_KEY" and len(API_KEY) > 5:
                    response = requests.get(
                        METALS_API_URL,
                        params={"api_key": API_KEY, "base": "USD", "currencies": "ALU,ZNC,XMG"},
                        timeout=3,
                    )
                    response.raise_for_status()
                    data = response.json()
                    rates = data.get("rates", {})
                    provider_error = data.get("error")
                    if provider_error:
                        self.cache["provider_error"] = provider_error.get("message", str(provider_error))
                    if data.get("success") and rates:
                        # metalpriceapi commonly returns metal units as troy ounces.
                        oz_to_kg = 35.27396195
                        mappings = {
                            "ALU": "Aluminum_A380",
                            "ZNC": "Zinc_ZD3",
                            "XMG": "Magnesium_AZ91D",
                        }
                        for symbol, metal in mappings.items():
                            rate = rates.get(symbol)
                            if rate:
                                usd_per_kg = (1 / float(rate)) * oz_to_kg
                                if metal == "Aluminum_A380":
                                    usd_per_kg += 0.35
                                self.cache["metals"][metal]["base_price"] = round(usd_per_kg, 4)
                                self.cache["metals"][metal]["current_price"] = round(usd_per_kg, 4)
                                self.cache["metals"][metal]["source"] = "METALPRICEAPI_LIVE"
                                self.cache["metals"][metal]["as_of"] = data.get("date") or self._utc_stamp()
                                self.cache["metals"][metal]["is_live"] = True
                                sync_success = True
            except Exception as e:
                logger.error(f"API sync failed: {e}")
                self.cache["provider_error"] = str(e)

            for metal, data in self.cache["metals"].items():
                if not sync_success or data.get("source") != "METALPRICEAPI_LIVE":
                    data["current_price"] = data["base_price"]
                    data["source"] = "REFERENCE_ALLOY_PRICE"
                    data["as_of"] = self._utc_stamp()
                    data["is_live"] = False
                base = self.cache["metals"][metal].get("base_price", 2.85)
                self.cache["metals"][metal]["current_price"] = round(base, 4)
                self.cache["metals"][metal]["status"] = "LIVE_MARKET" if sync_success else "REFERENCE_PRICE"

            self.cache["pricing_status"] = "LIVE" if sync_success else "REFERENCE"
            self.cache["pricing_note"] = (
                "Live metal provider returned today's quote."
                if sync_success
                else (
                    "Using reference alloy prices because Metalprice API did not return live alloy quotes"
                    + (f": {self.cache.get('provider_error')}" if self.cache.get("provider_error") else ".")
                )
            )
            self.cache["last_updated"] = now

        return self.cache["metals"]

    def get_location_record(self, location_name):
        return self.location_market_adjustments.get(
            location_name,
            {"metal_premium": 0.06, "freight": 0.12, "currency": "USD", "city": location_name, "country": "Unknown", "lat": None, "lon": None},
        )

    def get_location_adjusted_price(self, base_price_usd_per_kg, location_name, is_live=False):
        adjustment = self.location_market_adjustments.get(
            location_name,
            {"metal_premium": 0.06, "freight": 0.12, "currency": "USD", "city": location_name, "country": "Unknown", "lat": None, "lon": None},
        )
        landed_price = base_price_usd_per_kg * (1 + adjustment["metal_premium"]) + adjustment["freight"]
        return {
            "location_adjusted_usd_per_kg": round(landed_price, 4),
            "regional_premium_percent": round(adjustment["metal_premium"] * 100, 2),
            "estimated_freight_usd_per_kg": adjustment["freight"],
            "currency": adjustment["currency"],
            "is_live_price": bool(is_live),
            "method": (
                "live spot price plus location premium and freight model"
                if is_live
                else "reference alloy price plus location premium and freight model; live metal quote unavailable"
            ),
        }

    def get_location_price_table(self, base_price_usd_per_kg, is_live=False):
        table = []
        for name, location in self.location_market_adjustments.items():
            price = self.get_location_adjusted_price(base_price_usd_per_kg, name, is_live=is_live)
            table.append({
                "name": name,
                "city": location["city"],
                "country": location["country"],
                "lat": location["lat"],
                "lon": location["lon"],
                "currency": location["currency"],
                "location_adjusted_usd_per_kg": price["location_adjusted_usd_per_kg"],
                "regional_premium_percent": price["regional_premium_percent"],
                "estimated_freight_usd_per_kg": price["estimated_freight_usd_per_kg"],
                "is_live_price": price["is_live_price"],
                "method": price["method"],
            })
        return table

    def get_exchange_rate(self):
        """Return USD to INR conversion rate without synthetic random movement."""
        now = time.time()
        if now - self.cache.get("last_rate_update", 0) > self.ttl:
            try:
                response = requests.get(FX_API_URL, params={"from": "USD", "to": "INR"}, timeout=3)
                response.raise_for_status()
                data = response.json()
                self.cache["exchange_rate"] = float(data["rates"]["INR"])
                self.cache["fx_source"] = "FRANKFURTER"
                self.cache["fx_as_of"] = data.get("date") or self._utc_stamp()
            except Exception as e:
                logger.error(f"FX sync failed: {e}")
                self.cache["fx_source"] = "REFERENCE_FX"
                self.cache["fx_as_of"] = self._utc_stamp()
            self.cache["last_rate_update"] = now
        return self.cache["exchange_rate"]

    def get_location_indices(self):
        """Extended manufacturing hubs for global price search."""
        return [
            {"name": "India (Pune Node)", "multiplier": 0.82, "market_status": "STABLE", **self.location_market_adjustments["India (Pune Node)"]},
            {"name": "India (Chennai Cluster)", "multiplier": 0.85, "market_status": "STABLE", **self.location_market_adjustments["India (Chennai Cluster)"]},
            {"name": "China (Ningbo Hub)", "multiplier": 0.92, "market_status": "STABLE", **self.location_market_adjustments["China (Ningbo Hub)"]},
            {"name": "USA (Chicago/Midwest)", "multiplier": 1.55, "market_status": "HIGH_COST", **self.location_market_adjustments["USA (Chicago/Midwest)"]},
            {"name": "Germany (Stuttgart)", "multiplier": 1.70, "market_status": "PREMIUM", **self.location_market_adjustments["Germany (Stuttgart)"]},
            {"name": "Vietnam (Hanoi)", "multiplier": 0.72, "market_status": "EMERGING", **self.location_market_adjustments["Vietnam (Hanoi)"]},
            {"name": "Mexico (Monterrey)", "multiplier": 1.05, "market_status": "STABLE", **self.location_market_adjustments["Mexico (Monterrey)"]}
        ]

    def search_location(self, query):
        query = query.lower()
        all_locs = self.get_location_indices()
        return [l for l in all_locs if query in l['name'].lower() or query in l['city'].lower()]

market_fetcher = MarketFetcher()
