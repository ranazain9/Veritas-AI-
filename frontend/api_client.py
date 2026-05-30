"""HTTP client for the Veritas FastAPI backend (Railway)."""

from typing import Any, Dict, List, Optional

import httpx
import streamlit as st

DEFAULT_API_URL = "https://veritas-ai-production-f85b.up.railway.app"
AUDIT_TIMEOUT = 600.0


def secret(name: str, default: str = "") -> str:
    try:
        val = st.secrets.get(name, default)
    except Exception:
        val = default
    return str(val).strip() if val is not None else default


def api_base() -> str:
    return secret("VERITAS_API_URL", DEFAULT_API_URL).rstrip("/")


def api_key() -> str:
    return secret("VERITAS_API_KEY")


class VeritasAPI:
    """Thin wrapper over /health and /v1/* routes."""

    def __init__(self, base_url: Optional[str] = None, key: Optional[str] = None) -> None:
        self.base_url = (base_url or api_base()).rstrip("/")
        self._key = key if key is not None else api_key()

    def _auth_headers(self) -> Dict[str, str]:
        return {"X-API-Key": self._key} if self._key else {}

    def _get(self, path: str, *, auth: bool = True, timeout: float = 30.0, **params) -> httpx.Response:
        headers = self._auth_headers() if auth else {}
        with httpx.Client(timeout=timeout) as client:
            return client.get(f"{self.base_url}{path}", headers=headers, params=params or None)

    def _post(self, path: str, body: dict, *, timeout: float = AUDIT_TIMEOUT) -> httpx.Response:
        with httpx.Client(timeout=timeout) as client:
            return client.post(
                f"{self.base_url}{path}",
                json=body,
                headers=self._auth_headers(),
            )

    # ── system ──────────────────────────────────────────────────────────
    def health(self) -> Dict[str, Any]:
        resp = self._get("/health", auth=False, timeout=15.0)
        resp.raise_for_status()
        return resp.json()

    def health_config(self) -> List[Dict[str, Any]]:
        resp = self._get("/v1/health/config")
        resp.raise_for_status()
        return resp.json()

    # ── catalog ─────────────────────────────────────────────────────────
    def list_suppliers(self) -> List[Dict[str, Any]]:
        resp = self._get("/v1/suppliers")
        resp.raise_for_status()
        return resp.json()

    def get_supplier(self, supplier_id: str) -> Dict[str, Any]:
        resp = self._get(f"/v1/suppliers/{supplier_id}")
        resp.raise_for_status()
        return resp.json()

    def list_scenarios(self) -> List[Dict[str, Any]]:
        resp = self._get("/v1/scenarios")
        resp.raise_for_status()
        return resp.json()

    # ── audits ──────────────────────────────────────────────────────────
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
            "/v1/audits/run",
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
        resp = self._post("/v1/audits/synthesize", {"state": state, "save": save})
        resp.raise_for_status()
        return resp.json()

    def list_audits(self, limit: int = 50, supplier_id: Optional[str] = None) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"limit": limit}
        if supplier_id:
            params["supplier_id"] = supplier_id
        resp = self._get("/v1/audits", **params)
        resp.raise_for_status()
        return resp.json()

    def get_audit(self, audit_id: int) -> Dict[str, Any]:
        resp = self._get(f"/v1/audits/{audit_id}")
        resp.raise_for_status()
        return resp.json()

    def get_audit_pdf(self, audit_id: int) -> bytes:
        resp = self._get(f"/v1/audits/{audit_id}/pdf", timeout=60.0)
        resp.raise_for_status()
        return resp.content

    def supplier_score_history(self, supplier_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        resp = self._get(f"/v1/suppliers/{supplier_id}/score-history", limit=limit)
        resp.raise_for_status()
        return resp.json()


def get_api() -> VeritasAPI:
    return VeritasAPI()
