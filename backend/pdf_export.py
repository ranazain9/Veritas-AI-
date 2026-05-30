"""PDF audit dossier export."""

from fpdf import FPDF

from backend.scenarios import get_scenario


def _safe(text: str) -> str:
    return (
        str(text)
        .replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2022", "*")
        .replace("\u2026", "...")
        .encode("latin-1", errors="replace")
        .decode("latin-1")
    )


def build_pdf(supplier_key: str, supplier_name: str, final_state: dict) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(20, 20, 20)

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "VERITAS AI - COMPLIANCE INTEGRITY AUDIT DOSSIER", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "Autonomous Counter-Deception Intelligence Platform", ln=True, align="C")
    pdf.ln(6)

    pdf.set_draw_color(99, 102, 241)
    pdf.set_line_width(0.5)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(4)

    def section(title: str, body: str) -> None:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(99, 102, 241)
        pdf.cell(0, 8, _safe(title), ln=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(0, 5, _safe(body or "N/A"))
        pdf.ln(3)

    score = final_state.get("corporate_truth_score", "N/A")
    verdict = final_state.get("status_verdict", "N/A")
    deception = final_state.get("deception_confidence_pct", "N/A")
    section("Supplier", f"{supplier_name}  ({supplier_key})")
    section("Industrial Zone", final_state.get("target_industrial_zone", "N/A"))
    section("Corporate Truth Score", f"{score} / 100")
    section("Deception Confidence Score", f"{deception}%")
    section("Verdict", str(verdict))
    section("GPT-4o Reasoning", final_state.get("llm_reasoning", ""))
    insights = final_state.get("synthesis_insights") or {}
    section("Track 1 — Operational Ground Truth", insights.get("track_1_operational_ground_truth"))
    section("Track 2 — Resource & Cargo Flow", insights.get("track_2_financial_resource_flow"))
    section("Track 3 — Narrative Deception Analysis", insights.get("track_3_narrative_deception_analysis"))

    scenario = final_state.get("scenario_id", "NOMINAL")
    section("Audit Scenario", get_scenario(scenario).get("label", scenario))

    for label, key in [
        ("Track 1 Citation", "op_log"),
        ("Track 2 Citation", "financial_log"),
        ("Track 3 Citation", "narrative_log"),
    ]:
        log = final_state.get(key) or {}
        cite = (
            f"URL: {log.get('target_url', 'N/A')}\n"
            f"Collected: {log.get('scraped_at', 'N/A')}\n"
            f"Confidence: {log.get('confidence', 'N/A')}%\n"
            f"Evidence: {log.get('evidence_snippet', 'N/A')}"
        )
        section(label, cite)

    return bytes(pdf.output())
