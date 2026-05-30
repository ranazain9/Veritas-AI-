"""Audit scenario presets for repeatable demos and analyst briefings."""

from typing import Dict, Any

SCENARIOS: Dict[str, Dict[str, Any]] = {
    "NOMINAL": {
        "label": "A: Nominal Operations (Routine Audit)",
        "description": "Standard triangulation with no injected crisis signals.",
        "analyst_brief": (
            "Assume routine operations unless live evidence shows otherwise. "
            "Approve when all three tracks are nominal."
        ),
    },
    "STRIKE_COVERUP": {
        "label": "B: Wildcat Strike & Cover-Up",
        "description": "Expect operational shutdown, cargo/logistics drop, and coordinated positive PR.",
        "analyst_brief": (
            "High-priority: look for wildcat strike or plant shutdown (operational), "
            "sharp outbound cargo or production reduction (logistics), and a burst of "
            "identical positive safety/ESG articles (narrative cover-up). "
            "If all three align, escalate to coordinated deception."
        ),
    },
    "PR_SURGE": {
        "label": "C: PR Surge Only (Narrative Watch)",
        "description": "Focus on suspicious positive media without assuming physical disruption.",
        "analyst_brief": (
            "Prioritize narrative analysis: coordinated PR campaigns, newly registered "
            "news sites, or identical press releases. Physical ops may still look nominal."
        ),
    },
}

DEFAULT_SCENARIO = "NOMINAL"


def get_scenario(scenario_id: str) -> Dict[str, Any]:
    return SCENARIOS.get(scenario_id, SCENARIOS[DEFAULT_SCENARIO])


def scenario_prompt_block(scenario_id: str) -> str:
    s = get_scenario(scenario_id)
    return f"Scenario: {s['label']}\nAnalyst briefing: {s['analyst_brief']}"
