"""LangGraph + agent orchestration (heavy imports isolated from state.py)."""

import asyncio
import json
import re
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from backend.aimlapi_llm import ChatAimlapi
from backend.agents import (
    run_narrative_defense_agent,
    run_operational_flow_agent,
    run_resource_valuation_agent,
    set_audit_context,
)
from backend.scenarios import scenario_prompt_block
from backend.state import AgentState

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=True)

_client = None


def _get_client() -> ChatAimlapi:
    global _client
    if _client is None:
        _client = ChatAimlapi(max_tokens=600, timeout=120)
    return _client


SYNTHESIS_SYSTEM_PROMPT = """You are Veritas AI's Counter-Deception Synthesis Engine.

You receive intelligence reports from three specialist agents:
  - Agent 1 (Operational Ground Truth): Crawls local worker forums and community boards.
  - Agent 2 (Resource & Cargo Flow): Analyses outbound shipping manifests and logistics tonnage.
  - Agent 3 (Narrative Defense): Scans search engines for coordinated PR campaigns / cover-ups.

Triangulate these three reports and produce a compliance verdict.

Return ONLY a valid JSON object with EXACTLY these four keys, no extra text:
{
  "corporate_truth_score": <integer 0-100>,
  "status_verdict": "<APPROVED | WARNING_MINOR_OPERATIONAL_ANOMALY | WARNING_MINOR_LOGISTICS_REDUCTION | WARNING_SUSPECTED_UNREPORTED_CRISIS | NOMINAL_PR_SURGE_DETECTED | ESCALATE_IMMEDIATE_COMPLIANCE_FRAUD>",
  "llm_reasoning": "<2-3 sentence explanation citing evidence>",
  "deception_confidence_pct": <integer 0-100>
}

Scoring: all normal=95-100 APPROVED, minor anomaly=80-90 WARNING, strike+cargo drop=55-70 WARNING_SUSPECTED, PR surge only=85-92 NOMINAL_PR_SURGE, strike+cargo+PR=5-20 ESCALATE_FRAUD."""


def _extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {}


def _audit_trail(op_log: dict, financial_log: dict, narrative_log: dict, routing: str) -> dict:
    avg_latency = round(
        (
            op_log.get("duration_seconds", 0)
            + financial_log.get("duration_seconds", 0)
            + narrative_log.get("duration_seconds", 0)
        )
        / 3.0,
        3,
    )
    return {
        "mcp_server_routing": routing,
        "proxies_utilized": {
            "agent_1_proxy": op_log.get("proxy_utilized", "N/A"),
            "agent_2_proxy": financial_log.get("proxy_utilized", "N/A"),
            "agent_3_proxy": narrative_log.get("proxy_utilized", "N/A"),
        },
        "average_network_latency_seconds": avg_latency,
    }


def _format_agent_block(name: str, log: dict) -> str:
    return (
        f"{name}\n"
        f"Status/Metrics: {log.get('status') or log.get('metrics')}\n"
        f"Confidence: {log.get('confidence', 'N/A')}%\n"
        f"Source: {log.get('target_url', 'N/A')}\n"
        f"Evidence: {log.get('evidence_snippet', log.get('data', 'N/A'))}\n"
        f"Summary: {log.get('data', 'N/A')}"
    )


async def run_agent_1(state: AgentState) -> Dict[str, Any]:
    res = await run_operational_flow_agent(
        state["target_industrial_zone"],
        state.get("simulate_error"),
    )
    return {"op_log": res}


async def run_agent_2(state: AgentState) -> Dict[str, Any]:
    res = await run_resource_valuation_agent(
        state["target_industrial_zone"],
        state.get("simulate_error"),
    )
    return {"financial_log": res}


async def run_agent_3(state: AgentState) -> Dict[str, Any]:
    res = await run_narrative_defense_agent(
        state["supplier_id"],
        state.get("simulate_error"),
    )
    return {"narrative_log": res}


async def run_llm_synthesis(state: AgentState) -> Dict[str, Any]:
    op_log = state.get("op_log") or {}
    financial_log = state.get("financial_log") or {}
    narrative_log = state.get("narrative_log") or {}
    scenario_id = state.get("scenario_id", "NOMINAL")

    if not op_log.get("data") and not financial_log.get("data"):
        return {
            "corporate_truth_score": 50,
            "status_verdict": "WARNING_SUSPECTED_UNREPORTED_CRISIS",
            "llm_reasoning": "One or more agents failed to retrieve data. Partial evidence prevents a full verdict.",
            "deception_confidence_pct": 50,
            "synthesis_insights": {
                "track_1_operational_ground_truth": op_log.get("data", "[Agent 1 unavailable]"),
                "track_2_financial_resource_flow": financial_log.get("data", "[Agent 2 unavailable]"),
                "track_3_narrative_deception_analysis": narrative_log.get("data", "[Agent 3 unavailable]"),
            },
            "bright_data_infrastructure_audit_trail": _audit_trail(
                op_log, financial_log, narrative_log, "PARTIAL"
            ),
        }

    user_message = f"""
{scenario_prompt_block(scenario_id)}

=== AGENT 1: OPERATIONAL GROUND TRUTH ===
{_format_agent_block("Operational", op_log)}

=== AGENT 2: RESOURCE & CARGO FLOW ===
{_format_agent_block("Logistics", financial_log)}

=== AGENT 3: NARRATIVE DEFENSE ===
Flags: {narrative_log.get("flags", [])}
{_format_agent_block("Narrative", narrative_log)}

Supplier: {state["supplier_id"]} | Zone: {state["target_industrial_zone"]} | Lang: {state.get("native_language_code", "en")}

Produce your JSON verdict now. Return ONLY the JSON object, nothing else.
"""

    response = await _get_client().ainvoke(
        [SystemMessage(content=SYNTHESIS_SYSTEM_PROMPT), HumanMessage(content=user_message)]
    )
    verdict = _extract_json(response.content if hasattr(response, "content") else str(response))

    return {
        "corporate_truth_score": int(verdict.get("corporate_truth_score", 50)),
        "status_verdict": verdict.get("status_verdict", "APPROVED"),
        "llm_reasoning": verdict.get("llm_reasoning", ""),
        "deception_confidence_pct": int(verdict.get("deception_confidence_pct", 0)),
        "synthesis_insights": {
            "track_1_operational_ground_truth": op_log.get("data"),
            "track_2_financial_resource_flow": financial_log.get("data"),
            "track_3_narrative_deception_analysis": narrative_log.get("data"),
        },
        "bright_data_infrastructure_audit_trail": _audit_trail(
            op_log, financial_log, narrative_log, "ACTIVE"
        ),
    }


async def run_all_agents(state: AgentState) -> AgentState:
    set_audit_context(
        state.get("scenario_id", "NOMINAL"),
        state.get("native_language_code", "en"),
    )
    r1, r2, r3 = await asyncio.gather(
        run_agent_1(state),
        run_agent_2(state),
        run_agent_3(state),
    )
    merged: AgentState = dict(state)  # type: ignore[assignment]
    merged.update(r1)
    merged.update(r2)
    merged.update(r3)
    return merged


async def run_synthesis_only(state: AgentState) -> AgentState:
    patch = await run_llm_synthesis(state)
    return {**state, **patch}


async def run_full_audit(state: AgentState) -> AgentState:
    return await run_synthesis_only(await run_all_agents(state))


def _build_full_graph():
    g = StateGraph(AgentState)
    g.add_node("agent_1", run_agent_1)
    g.add_node("agent_2", run_agent_2)
    g.add_node("agent_3", run_agent_3)
    g.add_node("synthesis", run_llm_synthesis)
    g.add_edge(START, "agent_1")
    g.add_edge(START, "agent_2")
    g.add_edge(START, "agent_3")
    g.add_edge("agent_1", "synthesis")
    g.add_edge("agent_2", "synthesis")
    g.add_edge("agent_3", "synthesis")
    g.add_edge("synthesis", END)
    return g.compile()


app_graph = None
try:
    app_graph = _build_full_graph()
except Exception:
    app_graph = None
