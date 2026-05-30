"""Shared audit state — no LangGraph or agent dependencies (safe to import anywhere)."""

from typing import Any, Dict, Optional, TypedDict


class AgentState(TypedDict):
    supplier_id: str
    target_industrial_zone: str
    native_language_code: str
    scenario_id: str
    simulate_error: Optional[str]
    op_log: Optional[Dict[str, Any]]
    financial_log: Optional[Dict[str, Any]]
    narrative_log: Optional[Dict[str, Any]]
    corporate_truth_score: Optional[int]
    status_verdict: Optional[str]
    llm_reasoning: Optional[str]
    deception_confidence_pct: Optional[int]
    synthesis_insights: Optional[Dict[str, Optional[str]]]
    bright_data_infrastructure_audit_trail: Optional[Dict[str, Any]]


def build_initial_state(
    supplier_id: str,
    zone: str,
    lang: str,
    scenario_id: str,
    simulate_error: Optional[str],
) -> AgentState:
    return {
        "supplier_id": supplier_id,
        "target_industrial_zone": zone,
        "native_language_code": lang,
        "scenario_id": scenario_id,
        "simulate_error": simulate_error,
        "op_log": None,
        "financial_log": None,
        "narrative_log": None,
        "corporate_truth_score": None,
        "status_verdict": None,
        "llm_reasoning": None,
        "deception_confidence_pct": None,
        "synthesis_insights": None,
        "bright_data_infrastructure_audit_trail": None,
    }
