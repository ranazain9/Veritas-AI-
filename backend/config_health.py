"""Environment and integration health checks for the dashboard."""

import os
from typing import Dict, List

REQUIRED_KEYS = [
    ("AIMLAPI_API_KEY", "AIML API (GPT-4o)"),
    ("BRIGHT_DATA_SBR_WS", "Bright Data Scraping Browser"),
    ("BRIGHT_DATA_SERP_TOKEN", "Bright Data SERP API"),
]

OPTIONAL_KEYS = [
    ("SLACK_WEBHOOK_URL", "Slack alerts"),
    ("AIMLAPI_API_BASE", "AIML API base URL"),
    ("BRIGHT_DATA_ZONE_SERP", "SERP zone name"),
]


def check_config() -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []
    for key, label in REQUIRED_KEYS:
        val = os.getenv(key, "").strip()
        if val:
            results.append({"key": key, "label": label, "status": "ok", "detail": "Configured"})
        else:
            results.append({"key": key, "label": label, "status": "error", "detail": "Missing or empty"})
    for key, label in OPTIONAL_KEYS:
        val = os.getenv(key, "").strip()
        if val:
            results.append({"key": key, "label": label, "status": "ok", "detail": "Configured"})
        else:
            results.append({"key": key, "label": label, "status": "warn", "detail": "Optional — not set"})
    return results


def all_required_ok() -> bool:
    return all(r["status"] == "ok" for r in check_config() if r["key"] in {k for k, _ in REQUIRED_KEYS})
