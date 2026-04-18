import json
import logging
import os
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
TINYFISH_API_KEY = os.getenv("TINYFISH_API_KEY")

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
FIRECRAWL_SEARCH_URL = "https://api.firecrawl.dev/v2/search"
TINYFISH_SEARCH_URL = "https://api.search.tinyfish.ai"


class AIIntegrationHub:
    def provider_status(self) -> Dict[str, Dict[str, Any]]:
        return {
            "groq": {
                "configured": bool(GROQ_API_KEY),
                "model": GROQ_MODEL,
                "role": "LLM quote reasoning and customer-ready explanation",
            },
            "firecrawl": {
                "configured": bool(FIRECRAWL_API_KEY),
                "role": "Web search for market context",
            },
            "tinyfish": {
                "configured": bool(TINYFISH_API_KEY),
                "role": "Second web-search provider for market cross-checking",
            },
        }

    def get_market_context(self, metal: str, location_name: str) -> List[Dict[str, str]]:
        query = f"{metal.replace('_', ' ')} alloy price USD per kg today HPDC die casting {location_name}"
        sources: List[Dict[str, str]] = []
        sources.extend(self._firecrawl_search(query))
        sources.extend(self._tinyfish_search(query))

        seen = set()
        unique_sources = []
        for source in sources:
            url = source.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            unique_sources.append(source)
        return unique_sources[:6]

    def generate_quote_insight(self, report: Dict[str, Any]) -> Dict[str, Any]:
        cost = report.get("cost_estimation", {})
        traits = report.get("technical_matrix", {})
        market = report.get("market_snapshot", {})
        metal = market.get("metal", "Selected alloy")
        location = market.get("location", "Selected plant")
        sources = self.get_market_context(metal, location)

        fallback = self._fallback_insight(report, sources)
        if not GROQ_API_KEY:
            fallback["status"] = "fallback"
            fallback["note"] = "Set GROQ_API_KEY to enable Groq AI quote reasoning."
            return fallback

        payload = {
            "model": GROQ_MODEL,
            "temperature": 0.2,
            "max_tokens": 550,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an HPDC costing engineer. Return only valid JSON with keys: "
                        "summary, key_drivers, risk_notes, recommendation. Keep numbers grounded "
                        "in the provided quote. Do not invent live prices."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "part_file": report.get("file"),
                            "geometry": {
                                "volume_mm3": traits.get("volume"),
                                "surface_area_mm2": traits.get("surface_area"),
                                "projected_area_mm2": traits.get("projected_area"),
                                "dimensions_mm": traits.get("dimensions"),
                            },
                            "cost": {
                                "per_part_usd": cost.get("per_part_cost") or cost.get("total_unit_cost"),
                                "per_part_inr": cost.get("unit_cost_inr"),
                                "material": cost.get("material_cost"),
                                "machine": cost.get("machine_cost"),
                                "amortization": cost.get("amortization"),
                                "port_finishing": cost.get("port_cost"),
                                "fluctuation_range": cost.get("fluctuation_range"),
                                "machine_details": cost.get("machine_details"),
                            },
                            "market": market,
                            "web_context": sources,
                        },
                        ensure_ascii=True,
                    ),
                },
            ],
        }

        try:
            response = requests.post(
                GROQ_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=12,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                parsed = {
                    "summary": content.strip(),
                    "key_drivers": fallback["key_drivers"],
                    "risk_notes": fallback["risk_notes"],
                    "recommendation": fallback["recommendation"],
                }
            return {
                "status": "ai_generated",
                "provider": "groq",
                "model": GROQ_MODEL,
                "summary": parsed.get("summary", fallback["summary"]),
                "key_drivers": parsed.get("key_drivers", fallback["key_drivers"]),
                "risk_notes": parsed.get("risk_notes", fallback["risk_notes"]),
                "recommendation": parsed.get("recommendation", fallback["recommendation"]),
                "sources": sources,
            }
        except Exception as exc:
            logger.warning(f"Groq insight failed: {exc}")
            fallback["status"] = "fallback"
            fallback["note"] = f"Groq AI could not generate an insight: {exc}"
            return fallback

    def _firecrawl_search(self, query: str) -> List[Dict[str, str]]:
        if not FIRECRAWL_API_KEY:
            return []

        try:
            response = requests.post(
                FIRECRAWL_SEARCH_URL,
                headers={
                    "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"query": query, "limit": 3, "sources": ["web"], "timeout": 8000},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json().get("data", {})
            return [
                {
                    "provider": "firecrawl",
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("description", "") or item.get("markdown", "")[:240],
                }
                for item in data.get("web", [])[:3]
            ]
        except Exception as exc:
            logger.warning(f"Firecrawl search failed: {exc}")
            return []

    def _tinyfish_search(self, query: str) -> List[Dict[str, str]]:
        if not TINYFISH_API_KEY:
            return []

        try:
            response = requests.get(
                TINYFISH_SEARCH_URL,
                headers={"X-API-Key": TINYFISH_API_KEY},
                params={"query": query, "location": "US", "language": "en"},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            return [
                {
                    "provider": "tinyfish",
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("snippet", ""),
                }
                for item in data.get("results", [])[:3]
            ]
        except Exception as exc:
            logger.warning(f"TinyFish search failed: {exc}")
            return []

    def _fallback_insight(self, report: Dict[str, Any], sources: List[Dict[str, str]]) -> Dict[str, Any]:
        cost = report.get("cost_estimation", {})
        traits = report.get("technical_matrix", {})
        per_part = cost.get("per_part_cost") or cost.get("total_unit_cost") or 0
        machine = cost.get("machine_details", {})

        return {
            "status": "deterministic",
            "provider": "local_rules",
            "summary": f"Estimated HPDC cost is ${per_part:.2f} per part based on CAD geometry, alloy input, plant factor, tooling amortization, and port/finishing cost.",
            "key_drivers": [
                f"Projected area is {traits.get('projected_area', 0):.2f} mm2, selecting a {machine.get('selected_machine', 0)}T press.",
                f"Die amortization contributes ${cost.get('amortization', 0):.2f} per part at {cost.get('annual_volume', 0)} pieces.",
                f"Material cost uses ${cost.get('market_price', 0):.2f}/kg for {cost.get('alloy', 'selected alloy')}.",
            ],
            "risk_notes": [
                "Live supplier premiums, treatment charges, and scrap contracts can move final purchase price.",
                "Gate, runner, trimming, and finishing assumptions should be validated with the selected die-caster.",
            ],
            "recommendation": "Validate the parting line, slider count, runner ratio, and annual demand before freezing the commercial quote.",
            "sources": sources,
        }


ai_hub = AIIntegrationHub()
