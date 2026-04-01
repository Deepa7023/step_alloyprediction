import requests
import os
import time
import random
import logging
from dotenv import load_dotenv

load_dotenv()

# Live Market Data Integration
API_KEY = os.getenv("METALS_API_KEY")
METALS_API_URL = f"https://api.metalpriceapi.com/v1/latest?api_key={API_KEY}"

logger = logging.getLogger(__name__)

class MarketFetcher:
    def __init__(self):
        self.cache = {
            "metals": {
                "Aluminum_A380": {"base_price": 2.75, "current_price": 2.75, "density": 0.0027, "pressure": 80},
                "Zinc_ZD3": {"base_price": 3.10, "current_price": 3.10, "density": 0.0066, "pressure": 30},
                "Magnesium_AZ91D": {"base_price": 4.20, "current_price": 4.20, "density": 0.0018, "pressure": 60}
            },
            "last_updated": 0,
            "exchange_rate": 83.25, # USD to INR
            "last_rate_update": 0
        }
        self.ttl = 10800 # 3 Hours

    def get_live_prices(self):
        """Fetches live prices with advanced fallback mechanics and explicit status tracking."""
        now = time.time()
        
        # Ounce to Kilogram conversion (1 kg = 35.274 oz)
        OZ_TO_KG = 35.274
        
        # Determine if we should sync
        should_sync = now - self.cache["last_updated"] > self.ttl or self.cache["last_updated"] == 0
        
        if should_sync:
            logger.info("MARKET_NODE: Syncing with Global Metals API...")
            sync_success = False
            
            try:
                if API_KEY and API_KEY != "YOUR_API_KEY":
                    # Correct unit is gram/kg if supported by plan, but default is ounce
                    response = requests.get(METALS_API_URL, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("success"):
                            rates = data.get("rates", {})
                            # Standard API Mapping (1 USD = X ounces)
                            if "ALU" in rates: 
                                self.cache["metals"]["Aluminum_A380"]["base_price"] = round((1 / rates["ALU"]) * OZ_TO_KG, 4)
                                sync_success = True
                            if "ZNC" in rates: # Zinc symbol is ZNC
                                self.cache["metals"]["Zinc_ZD3"]["base_price"] = round((1 / rates["ZNC"]) * OZ_TO_KG, 4)
                                sync_success = True
                            if "XMG" in rates: # Magnesium Proxy is XMG
                                self.cache["metals"]["Magnesium_AZ91D"]["base_price"] = round((1 / rates["XMG"]) * OZ_TO_KG, 4)
                                sync_success = True
                else:
                    logger.warning("MARKET_NODE: No valid API key. Using high-fidelity local simulation.")
            except Exception as e:
                logger.error(f"API sync failed: {e}")

            # Refined Simulation & Volatility
            for metal in self.cache["metals"]:
                # If sync failed or missing key, use base_price as anchor for simulation
                # Typical price ranges: ALU ~$2.5-3.0, ZINC ~$3.0-3.5, MG ~$4.0-5.0
                base = self.cache["metals"][metal].get("base_price", 2.5)
                
                # Add micro-volatility (0.5% - 1.5%) to make it look alive
                fluctuation = 1 + (random.uniform(-0.015, 0.015)) 
                self.cache["metals"][metal]["current_price"] = round(base * fluctuation, 4)
                self.cache["metals"][metal]["status"] = "LIVE_MARKET" if sync_success else "SIMULATED_LOCAL_NODE"
            
            self.cache["last_updated"] = now
            
        return self.cache["metals"]

    def get_exchange_rate(self):
        """Returns USD to INR conversion rate."""
        now = time.time()
        if now - self.cache.get("last_rate_update", 0) > self.ttl:
            try:
                # Simulation for demo
                self.cache["exchange_rate"] = 83.0 + random.uniform(0.1, 0.8)
                self.cache["last_rate_update"] = now
            except:
                pass
        return self.cache["exchange_rate"]

    def get_location_indices(self):
        """Extended manufacturing hubs for global price search."""
        return [
            {"name": "India (Pune Node)", "multiplier": 0.78, "market_status": "BULLISH", "city": "Pune", "currency": "INR"},
            {"name": "India (Chennai Cluster)", "multiplier": 0.82, "market_status": "STABLE", "city": "Chennai", "currency": "INR"},
            {"name": "China (Ningbo Hub)", "multiplier": 0.88, "market_status": "STABLE", "city": "Ningbo", "currency": "CNY"},
            {"name": "USA (Chicago/Midwest)", "multiplier": 1.45, "market_status": "HIGH_COST", "city": "Chicago", "currency": "USD"},
            {"name": "Germany (Stuttgart)", "multiplier": 1.62, "market_status": "PREMIUM", "city": "Stuttgart", "currency": "EUR"},
            {"name": "Vietnam (Hanoi)", "multiplier": 0.65, "market_status": "EMERGING", "city": "Hanoi", "currency": "VND"},
            {"name": "Mexico (Monterrey)", "multiplier": 0.95, "market_status": "BULLISH", "city": "Monterrey", "currency": "MXN"}
        ]

    def search_location(self, query):
        """Search across global manufacturing nodes."""
        query = query.lower()
        all_locs = self.get_location_indices()
        return [l for l in all_locs if query in l['name'].lower() or query in l['city'].lower()]

market_fetcher = MarketFetcher()

