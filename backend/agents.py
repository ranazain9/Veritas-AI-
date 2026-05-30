"""
Veritas AI - Agents powered by Bright Data + AIML API (GPT-4o)
"""

import os
import re
import json
import time
import aiohttp
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from langchain_core.messages import SystemMessage, HumanMessage
from backend.aimlapi_llm import ChatAimlapi
from backend.scenarios import scenario_prompt_block, DEFAULT_SCENARIO
from backend.retry_utils import with_retry
from backend.error_handler import get_fallback_response, logger

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=True)

SBR_WS = os.getenv("BRIGHT_DATA_SBR_WS", "")
SERP_TOKEN = os.getenv("BRIGHT_DATA_SERP_TOKEN", "")
SERP_ZONE = os.getenv("BRIGHT_DATA_ZONE_SERP", "serp_api1")

llm = ChatAimlapi(max_tokens=512, timeout=120)

# Set by orchestration before each audit (avoids extra kwargs / Streamlit hot-reload issues)
_audit_ctx: Dict[str, str] = {
    "scenario_id": DEFAULT_SCENARIO,
    "native_language_code": "en",
}


def set_audit_context(scenario_id: str, native_language_code: str = "en") -> None:
    _audit_ctx["scenario_id"] = scenario_id or DEFAULT_SCENARIO
    _audit_ctx["native_language_code"] = native_language_code or "en"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clean(html: str, max_chars: int = 3500) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


async def _llm_json(system: str, user: str) -> dict:
    resp = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=user)])
    content = resp.content if hasattr(resp, "content") else str(resp)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {}


async def _scrape_with_browser(url: str, logs: list, timeout_ms: int = 60_000) -> str:
    if not SBR_WS:
        raise EnvironmentError("BRIGHT_DATA_SBR_WS not set in .env")

    async def _do_scrape() -> str:
        logs.append("[INFO] Connecting to Bright Data Scraping Browser...")
        async with async_playwright() as pw:
            browser = await pw.chromium.connect_over_cdp(SBR_WS)
            page = await browser.new_page()
            logs.append(f"[INFO] Navigating to: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            html = await page.content()
            await browser.close()
        snippet = _clean(html)
        logs.append(f"[SUCCESS] Scraped {len(html)} bytes -> {len(snippet)} chars extracted.")
        return snippet

    return await with_retry(_do_scrape, retries=2)


def _base_fields(
    agent_name: str,
    logs: list,
    target_url: str,
    proxy_utilized: str,
    proxy_pool: str,
    start_time: float,
    **extra,
) -> Dict[str, Any]:
    return {
        "agent_name": agent_name,
        "logs": logs,
        "target_url": target_url,
        "proxy_utilized": proxy_utilized,
        "proxy_pool": proxy_pool,
        "duration_seconds": round(time.time() - start_time, 3),
        "scraped_at": _utc_now(),
        "confidence": extra.pop("confidence", 0),
        "evidence_snippet": extra.pop("evidence_snippet", ""),
        **extra,
    }


async def run_operational_flow_agent(target_zone: str, simulate_error: str = None) -> Dict[str, Any]:
    scenario_id = _audit_ctx["scenario_id"]
    native_language_code = _audit_ctx["native_language_code"]
    start_time = time.time()
    agent_label = "Operational Flow Agent (Agent 1 - Scraping Browser)"

    try:
        if simulate_error == "proxy_timeout":
            raise TimeoutError("Bright Data Scraping Browser websocket timed out.")

        logs = ["[INFO] Agent 1 (Operational Flow) initializing..."]
        if simulate_error == "bot_block":
            logs += [
                "[WARNING] CAPTCHA detected.",
                "[INFO] Activating Bright Data auto-solver...",
                "[SUCCESS] CAPTCHA solved.",
            ]

        brief = scenario_prompt_block(scenario_id)
        url_decision = await _llm_json(
            system=(
                "You are an operational intelligence system. "
                "Return JSON with keys: url (public mining/industrial news URL), region (short label). "
                "Prefer reuters.com, mining.com, bbc.com. No paywalls. JSON only."
            ),
            user=f"{brief}\nIndustrial zone: {target_zone}\nPreferred language context: {native_language_code}",
        )
        url = url_decision.get("url", "https://www.mining.com/")
        region = url_decision.get("region", target_zone)
        logs.append(f"[INFO] LLM selected: {region} | {url}")

        snippet, status, confidence, evidence = f"No live data for {region}.", "nominal", 40, ""
        raw_snippet = ""
        try:
            raw_snippet = await _scrape_with_browser(url, logs)
            evidence = raw_snippet[:280]
            content = raw_snippet if len(raw_snippet) > 50 else f"No live content for {region}."
            assessment = await _llm_json(
                system=(
                    "Operational intelligence analyst. Return JSON: "
                    'status ("nominal"|"anomaly_detected"), summary (one sentence), '
                    "confidence (0-100 integer), evidence_snippet (short quote from content). "
                    "Flag anomalies for strikes, shutdowns, accidents, spills, protests. JSON only."
                ),
                user=f"{brief}\nRegion: {region}\n\nContent:\n{content}",
            )
            status = assessment.get("status", "nominal")
            snippet = assessment.get("summary", raw_snippet[:300])
            confidence = int(assessment.get("confidence", 70 if status == "nominal" else 85))
            evidence = assessment.get("evidence_snippet", evidence) or evidence
            logs.append(f"[INFO] LLM assessment: {status.upper()} ({confidence}%) - {snippet}")
        except Exception as exc:
            logs.append(f"[ERROR] Scraping Browser failed: {exc}")
            snippet, status, confidence = f"[AGENT 1 ERROR] {region}: {exc}", "error", 0
            logger.exception("Agent 1 scrape failed")

        return _base_fields(
            agent_label, logs, url, "Bright Data Scraping Browser (scraping_browser1)",
            "scraping_browser1", start_time,
            status=status, data=snippet, confidence=confidence, evidence_snippet=evidence,
        )
    except Exception as exc:
        logger.exception("Agent 1 fatal error")
        fb = get_fallback_response(agent_label)
        fb.update(_base_fields(
            agent_label, fb["logs"], "", "N/A", "", start_time,
            status="error", data=str(exc), confidence=0, evidence_snippet="",
        ))
        return fb


async def run_resource_valuation_agent(target_zone: str, simulate_error: str = None) -> Dict[str, Any]:
    scenario_id = _audit_ctx["scenario_id"]
    start_time = time.time()
    agent_label = "Resource & Valuation Agent (Agent 2 - Scraping Browser)"

    try:
        if simulate_error == "proxy_timeout":
            raise TimeoutError("Bright Data Scraping Browser websocket timed out.")
        if simulate_error == "payload_corruption":
            return _base_fields(
                agent_label, ["[ERROR] CRC checksum mismatch."], "", "N/A", "",
                start_time, status="error", data=None, metrics="corrupt", confidence=0,
                evidence_snippet="",
            )

        logs = ["[INFO] Agent 2 (Resource & Valuation) initializing..."]
        brief = scenario_prompt_block(scenario_id)
        url_decision = await _llm_json(
            system=(
                "Commodity intelligence system. Return JSON: url, commodity. "
                "Use indexmundi.com, markets.businessinsider.com, or kitco.com only. JSON only."
            ),
            user=f"{brief}\nIndustrial zone: {target_zone}",
        )
        url = url_decision.get("url", "https://www.kitco.com/")
        commodity = url_decision.get("commodity", "commodity")
        logs.append(f"[INFO] LLM selected: {commodity.upper()} | {url}")

        snippet, metrics, confidence, evidence = f"No live data for {commodity}.", "nominal_flow", 40, ""
        try:
            raw_snippet = await _scrape_with_browser(url, logs, timeout_ms=60_000)
            evidence = raw_snippet[:280]
            content = raw_snippet if len(raw_snippet) > 50 else f"No live content for {commodity}."
            assessment = await _llm_json(
                system=(
                    "Commodity flow analyst. Return JSON: "
                    'metrics ("nominal_flow"|"significant_reduction"), summary, '
                    "confidence (0-100), evidence_snippet. JSON only."
                ),
                user=f"{brief}\nCommodity: {commodity}\n\nContent:\n{content}",
            )
            metrics = assessment.get("metrics", "nominal_flow")
            snippet = assessment.get("summary", raw_snippet[:300])
            confidence = int(assessment.get("confidence", 65))
            evidence = assessment.get("evidence_snippet", evidence) or evidence
            logs.append(f"[INFO] LLM assessment: {metrics.upper()} ({confidence}%) - {snippet}")
        except Exception as exc:
            logs.append(f"[ERROR] Scraping Browser failed: {exc}")
            snippet, metrics, confidence = f"[AGENT 2 ERROR] {commodity}: {exc}", "error", 0
            logger.exception("Agent 2 scrape failed")

        return _base_fields(
            agent_label, logs, url, "Bright Data Scraping Browser (scraping_browser1)",
            "scraping_browser1", start_time,
            status="success" if metrics != "error" else "error",
            metrics=metrics, data=snippet, confidence=confidence, evidence_snippet=evidence,
        )
    except Exception as exc:
        logger.exception("Agent 2 fatal error")
        fb = get_fallback_response(agent_label)
        fb.update(_base_fields(
            agent_label, fb["logs"], "", "N/A", "", start_time,
            status="error", data=str(exc), metrics="error", confidence=0, evidence_snippet="",
        ))
        return fb


async def run_narrative_defense_agent(supplier_id: str, simulate_error: str = None) -> Dict[str, Any]:
    scenario_id = _audit_ctx["scenario_id"]
    start_time = time.time()
    agent_label = "Narrative Defense Agent (Agent 3 - SERP API)"

    try:
        if simulate_error == "proxy_timeout":
            raise TimeoutError("Bright Data SERP API proxy connection reset.")

        logs = [
            "[INFO] Agent 3 (Narrative Defense) initializing...",
            "[INFO] Triggering Bright Data SERP API (Google Search)...",
        ]
        brief = scenario_prompt_block(scenario_id)
        query_decision = await _llm_json(
            system=(
                "Counter-deception analyst. Return JSON with key query: "
                "Google search for ESG violations, labor abuses, or PR cover-ups. JSON only."
            ),
            user=f"{brief}\nSupplier ID: {supplier_id}",
        )
        query = query_decision.get("query", f"{supplier_id} ESG compliance violations")
        serp_url = f"https://www.google.com/search?q={query.replace(' ', '+')}&num=10"
        logs.append(f'[INFO] LLM query: "{query}"')

        snippet, flags, status, confidence, evidence = f"No narrative data for {supplier_id}.", [], "nominal", 40, ""
        try:
            if not SERP_TOKEN:
                raise EnvironmentError("BRIGHT_DATA_SERP_TOKEN not set in .env")

            async def _fetch_serp() -> str:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://api.brightdata.com/request",
                        headers={
                            "Authorization": f"Bearer {SERP_TOKEN}",
                            "Content-Type": "application/json",
                        },
                        json={"zone": SERP_ZONE, "url": serp_url, "format": "raw"},
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as resp:
                        raw = await resp.text()
                        logs.append(f"[SUCCESS] HTTP {resp.status} - SERP ({len(raw)} bytes).")
                        return raw

            raw = await with_retry(_fetch_serp, retries=2)
            cleaned = _clean(raw)
            evidence = cleaned[:280]
            content = cleaned if len(cleaned) > 50 else f"No results for {supplier_id}."
            assessment = await _llm_json(
                system=(
                    "Narrative manipulation specialist. Return JSON: "
                    'flags (list: "high_frequency_pr_campaign", "negative_coverage_detected"), '
                    "summary, confidence (0-100), evidence_snippet. JSON only."
                ),
                user=f"{brief}\nSupplier: {supplier_id}\nQuery: {query}\n\nSERP:\n{content}",
            )
            flags = assessment.get("flags", [])
            snippet = assessment.get("summary", cleaned[:300])
            confidence = int(assessment.get("confidence", 80 if flags else 55))
            evidence = assessment.get("evidence_snippet", evidence) or evidence
            status = "flagged" if flags else "nominal"
            logs.append(f"[INFO] Narrative assessment: flags={flags} ({confidence}%) - {snippet}")
        except Exception as exc:
            logs.append(f"[ERROR] SERP API failed: {exc}")
            snippet, status, confidence = f"[AGENT 3 ERROR] {supplier_id}: {exc}", "error", 0
            logger.exception("Agent 3 SERP failed")

        return _base_fields(
            agent_label, logs, serp_url, f"Bright Data SERP API ({SERP_ZONE})",
            SERP_ZONE, start_time,
            status=status, flags=flags, data=snippet, confidence=confidence,
            evidence_snippet=evidence,
        )
    except Exception as exc:
        logger.exception("Agent 3 fatal error")
        fb = get_fallback_response(agent_label)
        fb.update(_base_fields(
            agent_label, fb["logs"], "", "N/A", "", start_time,
            status="error", data=str(exc), flags=[], confidence=0, evidence_snippet="",
        ))
        return fb


simulate_scraping_browser = run_operational_flow_agent
simulate_web_scraper_api = run_resource_valuation_agent
simulate_serp_api = run_narrative_defense_agent
