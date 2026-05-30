"""FastAPI dependencies (auth, shared helpers)."""

import os
from typing import Optional

from fastapi import Header, HTTPException, status

from backend.scenarios import SCENARIOS, DEFAULT_SCENARIO
from backend.suppliers import SUPPLIERS, get_supplier
from backend.state import build_initial_state, AgentState


def verify_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> None:
    required = os.getenv("VERITAS_API_KEY", "").strip()
    if not required:
        return
    if x_api_key != required:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key",
        )


def resolve_supplier(supplier_id: str) -> dict:
    try:
        return get_supplier(supplier_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def resolve_scenario(scenario_id: str) -> str:
    if scenario_id not in SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scenario_id. Use one of: {', '.join(SCENARIOS)}",
        )
    return scenario_id


def make_initial_state(
    supplier_id: str,
    scenario_id: str,
    simulate_error: Optional[str],
) -> AgentState:
    sup = resolve_supplier(supplier_id)
    scenario_id = resolve_scenario(scenario_id or DEFAULT_SCENARIO)
    return build_initial_state(
        supplier_id,
        sup["zone"],
        sup["default_lang"],
        scenario_id,
        simulate_error,
    )
