"""API route handlers."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response

from backend.api.deps import make_initial_state, resolve_supplier, verify_api_key
from backend.api.schemas import (
    AuditRunRequest,
    AuditRunResponse,
    AuditSummary,
    ConfigHealthItem,
    HealthResponse,
    ScenarioOut,
    ScorePoint,
    SupplierOut,
    SynthesizeRequest,
)
from backend.audit_store import get_audit, list_audits, save_audit, supplier_score_history
from backend.config_health import check_config
from backend.orchestration import run_all_agents, run_full_audit, run_synthesis_only
from backend.pdf_export import build_pdf
from backend.scenarios import SCENARIOS
from backend.suppliers import SUPPLIERS

public_router = APIRouter(tags=["system"])
api_router = APIRouter(prefix="/v1", dependencies=[Depends(verify_api_key)])


@public_router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@api_router.get("/health/config", response_model=List[ConfigHealthItem])
async def health_config() -> List[ConfigHealthItem]:
    return [ConfigHealthItem(**row) for row in check_config()]


@api_router.get("/suppliers", response_model=List[SupplierOut], tags=["catalog"])
async def list_suppliers() -> List[SupplierOut]:
    return [
        SupplierOut(id=sid, **meta)
        for sid, meta in SUPPLIERS.items()
    ]


@api_router.get("/suppliers/{supplier_id}", response_model=SupplierOut, tags=["catalog"])
async def get_supplier_detail(supplier_id: str) -> SupplierOut:
    meta = resolve_supplier(supplier_id)
    return SupplierOut(id=supplier_id, **meta)


@api_router.get("/scenarios", response_model=List[ScenarioOut], tags=["catalog"])
async def list_scenarios() -> List[ScenarioOut]:
    return [
        ScenarioOut(id=sid, label=meta["label"], description=meta["description"])
        for sid, meta in SCENARIOS.items()
    ]


@api_router.post("/audits/run", response_model=AuditRunResponse, tags=["audits"])
async def run_audit(body: AuditRunRequest) -> AuditRunResponse:
    sup = resolve_supplier(body.supplier_id)
    state = make_initial_state(body.supplier_id, body.scenario_id, body.simulate_error)

    if body.step == "agents_only":
        final = await run_all_agents(state)
        step = "agents_only"
    else:
        final = await run_full_audit(state)
        step = "full"

    audit_id = None
    if body.save and step == "full":
        audit_id = save_audit(body.supplier_id, sup["name"], body.scenario_id, final)

    return AuditRunResponse(
        audit_id=audit_id,
        supplier_id=body.supplier_id,
        supplier_name=sup["name"],
        scenario_id=body.scenario_id,
        step=step,
        state=dict(final),
    )


@api_router.post("/audits/synthesize", response_model=AuditRunResponse, tags=["audits"])
async def synthesize_audit(body: SynthesizeRequest) -> AuditRunResponse:
    state = body.state
    supplier_id = state.get("supplier_id")
    if not supplier_id:
        raise HTTPException(status_code=400, detail="state.supplier_id is required")

    sup = resolve_supplier(supplier_id)
    scenario_id = state.get("scenario_id", "NOMINAL")
    final = await run_synthesis_only(state)  # type: ignore[arg-type]

    audit_id = None
    if body.save:
        audit_id = save_audit(supplier_id, sup["name"], scenario_id, final)

    return AuditRunResponse(
        audit_id=audit_id,
        supplier_id=supplier_id,
        supplier_name=sup["name"],
        scenario_id=scenario_id,
        step="synthesis",
        state=dict(final),
    )


@api_router.get("/audits", response_model=List[AuditSummary], tags=["audits"])
async def audits_history(
    limit: int = 50,
    supplier_id: Optional[str] = None,
) -> List[AuditSummary]:
    rows = list_audits(limit=min(limit, 200), supplier_id=supplier_id)
    return [
        AuditSummary(
            id=r["id"],
            created_at=r["created_at"],
            supplier_id=r["supplier_id"],
            supplier_name=r["supplier_name"],
            scenario_id=r.get("scenario_id"),
            truth_score=r.get("truth_score"),
            verdict=r.get("verdict"),
            deception_pct=r.get("deception_pct"),
        )
        for r in rows
    ]


@api_router.get("/audits/{audit_id}", tags=["audits"])
async def audit_detail(audit_id: int) -> dict:
    row = get_audit(audit_id)
    if not row:
        raise HTTPException(status_code=404, detail="Audit not found")
    return row


@api_router.get("/audits/{audit_id}/pdf", tags=["audits"])
async def audit_pdf(audit_id: int) -> Response:
    row = get_audit(audit_id)
    if not row:
        raise HTTPException(status_code=404, detail="Audit not found")
    state = row["final_state"]
    pdf_bytes = build_pdf(row["supplier_id"], row["supplier_name"], state)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="veritas_audit_{audit_id}.pdf"'},
    )


@api_router.get(
    "/suppliers/{supplier_id}/score-history",
    response_model=List[ScorePoint],
    tags=["audits"],
)
async def supplier_history(supplier_id: str, limit: int = 20) -> List[ScorePoint]:
    resolve_supplier(supplier_id)
    points = supplier_score_history(supplier_id, limit=min(limit, 100))
    return [ScorePoint(**p) for p in points]
