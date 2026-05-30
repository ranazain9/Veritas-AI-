"""Request/response models for the REST API."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "veritas-ai-api"
    version: str = "1.0.0"


class ConfigHealthItem(BaseModel):
    key: str
    label: str
    status: str
    detail: str


class SupplierOut(BaseModel):
    id: str
    name: str
    zone: str
    country: str
    lat: float
    lon: float
    default_lang: str
    base_risk: str


class ScenarioOut(BaseModel):
    id: str
    label: str
    description: str


class AuditRunRequest(BaseModel):
    supplier_id: str = Field(..., description="Supplier key, e.g. SUPPLIER-SINO-COBALT")
    scenario_id: str = Field(default="NOMINAL", description="NOMINAL | STRIKE_COVERUP | PR_SURGE")
    simulate_error: Optional[str] = Field(
        default=None,
        description="proxy_timeout | bot_block | payload_corruption",
    )
    step: Literal["full", "agents_only"] = Field(
        default="full",
        description="full = agents + synthesis; agents_only = human-in-the-loop step 1",
    )
    save: bool = Field(default=True, description="Persist result to SQLite audit history")


class SynthesizeRequest(BaseModel):
    """Agent state returned from step=agents_only, after human review."""
    state: Dict[str, Any]
    save: bool = True


class AuditSummary(BaseModel):
    id: int
    created_at: str
    supplier_id: str
    supplier_name: str
    scenario_id: Optional[str]
    truth_score: Optional[int]
    verdict: Optional[str]
    deception_pct: Optional[int]


class AuditRunResponse(BaseModel):
    audit_id: Optional[int] = None
    supplier_id: str
    supplier_name: str
    scenario_id: str
    step: str
    state: Dict[str, Any]


class ScorePoint(BaseModel):
    created_at: str
    truth_score: Optional[int]
    verdict: Optional[str]
    scenario_id: Optional[str]
