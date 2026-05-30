"""HTTP client for the Veritas FastAPI backend (Railway).

Every request uses a full URL, e.g.:
  https://veritas-ai-production-f85b.up.railway.app/health
  https://veritas-ai-production-f85b.up.railway.app/v1/audits/run
"""

from typing import Any, Dict, List, Optional

import httpx
import streamlit as st

RAILWAY_API = "https://veritas-ai-production-f85b.up.railway.app"
AUDIT_TIMEOUT = 600.0


def secret(name: str, default: str = "") -> str:
    try:
        val = st.secrets.get(name, default)
    except Exception:
        val = default
    return str(val).strip() if val is not None else default


def api_base() -> str:
    raw = secret("VERITAS_API_URL", RAILWAY_API).strip().rstrip("/")
    if not raw:
        raw = RAILWAY_API
    if not raw.startswith(("http://", "https://")):
        raw = f"https://{raw}"
    return raw.rstrip("/")


def api_url(path: str, base: Optional[str] = None) -> str:
    """Build full endpoint URL: https://...railway.app/health"""
    segment = path if path.startswith("/") else f"/{path}"
    return f"{(base or api_base()).rstrip('/')}{segment}"


def api_key() -> str:
    return secret("VERITAS_API_KEY")


class VeritasAPI:
    """Calls Railway using full HTTPS URLs for every endpoint."""

    HEALTH = "/health"
    HEALTH_CONFIG = "/v1/health/config"
    SUPPLIERS = "/v1/suppliers"
    SCENARIOS = "/v1/scenarios"
    AUDITS_RUN = "/v1/audits/run"
    AUDITS_SYNTHESIZE = "/v1/audits/synthesize"
    AUDITS = "/v1/audits"

    def __init__(self, base_url: Optional[str] = None, key: Optional[str] = None) -> None:
        self.base_url = (base_url or api_base()).rstrip("/")
        self._key = key if key is not None else api_key()

    def url(self, path: str) -> str:
        return api_url(path, self.base_url)

    def _auth_headers(self) -> Dict[str, str]:
        return {"X-API-Key": self._key} if self._key else {}

    def _get(self, path: str, *, auth: bool = True, timeout: float = 30.0, **params) -> httpx.Response:
        full = self.url(path)
        headers = self._auth_headers() if auth else {}
        with httpx.Client(timeout=timeout) as client:
            return client.get(full, headers=headers, params=params or None)

    def _post(self, path: str, body: dict, *, timeout: float = AUDIT_TIMEOUT) -> httpx.Response:
        full = self.url(path)
        with httpx.Client(timeout=timeout) as client:
            return client.post(full, json=body, headers=self._auth_headers())

    def health(self) -> Dict[str, Any]:
        resp = self._get(self.HEALTH, auth=False, timeout=15.0)
        resp.raise_for_status()
        return resp.json()

    def health_config(self) -> List[Dict[str, Any]]:
        resp = self._get(self.HEALTH_CONFIG)
        resp.raise_for_status()
        return resp.json()

    def list_suppliers(self) -> List[Dict[str, Any]]:
        resp = self._get(self.SUPPLIERS)
        resp.raise_for_status()
        return resp.json()

    def get_supplier(self, supplier_id: str) -> Dict[str, Any]:
        resp = self._get(f"{self.SUPPLIERS}/{supplier_id}")
        resp.raise_for_status()
        return resp.json()

    def list_scenarios(self) -> List[Dict[str, Any]]:
        resp = self._get(self.SCENARIOS)
        resp.raise_for_status()
        return resp.json()

    def run_audit(
        self,
        supplier_id: str,
        scenario_id: str,
        simulate_error: Optional[str] = None,
        *,
        step: str = "full",
        save: bool = True,
    ) -> Dict[str, Any]:
        resp = self._post(
            self.AUDITS_RUN,
            {
                "supplier_id": supplier_id,
                "scenario_id": scenario_id,
                "simulate_error": simulate_error,
                "step": step,
                "save": save,
            },
        )
        resp.raise_for_status()
        return resp.json()

    def synthesize(self, state: Dict[str, Any], *, save: bool = True) -> Dict[str, Any]:
        resp = self._post(self.AUDITS_SYNTHESIZE, {"state": state, "save": save})
        resp.raise_for_status()
        return resp.json()

    def list_audits(self, limit: int = 50, supplier_id: Optional[str] = None) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"limit": limit}
        if supplier_id:
            params["supplier_id"] = supplier_id
        resp = self._get(self.AUDITS, **params)
        resp.raise_for_status()
        return resp.json()

    def get_audit(self, audit_id: int) -> Dict[str, Any]:
        resp = self._get(f"{self.AUDITS}/{audit_id}")
        resp.raise_for_status()
        return resp.json()

    def get_audit_pdf(self, audit_id: int) -> bytes:
        resp = self._get(f"{self.AUDITS}/{audit_id}/pdf", timeout=60.0)
        resp.raise_for_status()
        return resp.content

    def supplier_score_history(self, supplier_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        resp = self._get(f"{self.SUPPLIERS}/{supplier_id}/score-history", limit=limit)
        resp.raise_for_status()
        return resp.json()


def get_api() -> VeritasAPI:
    return VeritasAPI()
