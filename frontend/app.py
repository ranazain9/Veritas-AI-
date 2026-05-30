"""Veritas AI Streamlit UI — Railway FastAPI client only (no local backend)."""

import asyncio
from typing import Any, Dict, Optional

import aiohttp
import httpx
import pandas as pd
import plotly.express as px
import streamlit as st

from api_client import VeritasAPI, api_base, api_key, get_api, secret


st.set_page_config(
    page_title="Veritas AI — Compliance Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Space+Grotesk:wght@400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }
    .stApp { background: linear-gradient(135deg, #030712 0%, #0b0f19 50%, #0f172a 100%); color: #f3f4f6; }
    .metric-card {
        background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px; padding: 20px; box-shadow: 0 8px 32px 0 rgba(0,0,0,0.37);
        backdrop-filter: blur(8px); transition: all 0.3s ease;
    }
    .metric-card:hover { border-color: rgba(99,102,241,0.4); transform: translateY(-2px); }
    .metric-value { font-family: 'Space Grotesk', sans-serif; font-size: 32px; font-weight: 700; margin-top: 5px; }
    .metric-label { font-size: 13px; color: #9ca3af; text-transform: uppercase; letter-spacing: 1px; }
    .terminal-container {
        font-family: 'Courier New', monospace; font-size: 11px; background-color: #020617;
        color: #38bdf8; border: 1px solid #1e293b; border-radius: 8px; padding: 12px;
        height: 250px; overflow-y: auto; box-shadow: inset 0 2px 8px rgba(0,0,0,0.8);
    }
    .terminal-line { margin-bottom: 4px; line-height: 1.4; }
    .log-info { color: #38bdf8; } .log-warning { color: #f59e0b; }
    .log-error { color: #ef4444; } .log-success { color: #10b981; }
    .main-title {
        font-family: 'Space Grotesk', sans-serif; font-size: 40px; font-weight: 800;
        background: linear-gradient(to right, #6366f1, #38bdf8, #ec4899);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 2px;
    }
    .subtitle { color: #9ca3af; font-size: 16px; margin-bottom: 25px; }
    .verdict-box { border-radius: 8px; padding: 15px; margin-top: 10px; font-weight: 600; text-align: center; letter-spacing: 1px; }
    .verdict-approved { background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.4); color: #34d399; }
    .verdict-warning  { background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.4); color: #fbbf24; }
    .verdict-danger   { background: rgba(239,68,68,0.1);  border: 1px solid rgba(239,68,68,0.4);  color: #f87171; }
    .score-circle-container { display: flex; justify-content: center; align-items: center; margin: 20px 0; }
    .score-circle {
        width: 140px; height: 140px; border-radius: 50%;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        transition: all 0.5s ease;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300, show_spinner=False)
def _load_catalogs(base: str, key: str) -> tuple[dict, dict]:
    api = VeritasAPI(base, key)
    suppliers = {
        row["id"]: {k: v for k, v in row.items() if k != "id"}
        for row in api.list_suppliers()
    }
    scenarios = {row["id"]: row for row in api.list_scenarios()}
    return suppliers, scenarios


def render_term(logs, title, proxy="Routing..."):
    out = f"<div style='font-weight:600;color:#9ca3af;margin-bottom:5px;'>📟 {title}</div>"
    out += f"<div style='font-size:10px;color:#10b981;margin-bottom:5px;'>🌐 {proxy}</div>"
    out += "<div class='terminal-container'>"
    for line in logs:
        cls = (
            "log-error" if "[ERROR]" in line
            else "log-warning" if "[WARNING]" in line
            else "log-success" if "[SUCCESS]" in line
            else "log-info"
        )
        out += f"<div class='terminal-line {cls}'>{line}</div>"
    out += "</div>"
    return out


async def send_slack_alert(supplier_name: str, score: int, verdict: str, webhook_url: str):
    if not webhook_url:
        return
    emoji = "🚨" if score < 50 else "✅"
    color = "#ef4444" if score < 50 else "#10b981"
    payload = {
        "attachments": [{
            "color": color,
            "text": f"{emoji} *Veritas AI Alert* — `{supplier_name}`\n*Truth Score:* {score}/100 | *Verdict:* `{verdict}`",
            "footer": "Veritas AI • Railway API",
        }]
    }
    async with aiohttp.ClientSession() as session:
        await session.post(webhook_url, json=payload)


def render_audit_results(final_state: dict, supplier_key: str, supplier: dict, audit_id: Optional[int]):
    op_log = final_state.get("op_log") or {}
    fin_log = final_state.get("financial_log") or {}
    nar_log = final_state.get("narrative_log") or {}

    st.markdown("---")
    st.markdown(
        "<h2 style='font-family:\"Space Grotesk\"; text-align:center; color:#6366f1;'>"
        "🕵️ Parallel Multi-Agent Analysis Log Console</h2>",
        unsafe_allow_html=True,
    )

    col_a1, col_a2, col_a3 = st.columns(3)
    with col_a1:
        st.markdown(render_term(op_log.get("logs", []), "Agent 1: Operational Flow", op_log.get("proxy_utilized", "BrowserAPI")), unsafe_allow_html=True)
    with col_a2:
        st.markdown(render_term(fin_log.get("logs", []), "Agent 2: Resource & Valuation", fin_log.get("proxy_utilized", "WebUnlocker")), unsafe_allow_html=True)
    with col_a3:
        st.markdown(render_term(nar_log.get("logs", []), "Agent 3: Narrative Defense", nar_log.get("proxy_utilized", "SERP API")), unsafe_allow_html=True)

    score = final_state.get("corporate_truth_score", 0)
    verdict = final_state.get("status_verdict", "N/A")

    st.markdown("<br>", unsafe_allow_html=True)
    col_l, col_r = st.columns([2, 3])

    with col_l:
        st.markdown("<h3 style='font-family:\"Space Grotesk\";text-align:center;font-size:18px;'>🛡️ Compliance Score</h3>", unsafe_allow_html=True)
        if score >= 80:
            bc, vc, glow = "#10b981", "verdict-approved", "rgba(16,185,129,0.4)"
        elif score >= 50:
            bc, vc, glow = "#f59e0b", "verdict-warning", "rgba(245,158,11,0.4)"
        else:
            bc, vc, glow = "#ef4444", "verdict-danger", "rgba(239,68,68,0.4)"

        st.markdown(f"""
        <div class='score-circle-container'>
          <div class='score-circle' style='border:4px solid {bc};box-shadow:0 0 25px {glow};'>
            <span style='font-size:11px;text-transform:uppercase;color:#9ca3af;font-weight:600;'>TRUTH SCORE</span>
            <span style='font-size:38px;font-weight:800;font-family:"Space Grotesk",sans-serif;color:{bc};'>{score}</span>
            <span style='font-size:10px;color:#9ca3af;'>OUT OF 100</span>
          </div>
        </div>
        <div class='verdict-box {vc}'>{verdict}</div>
        """, unsafe_allow_html=True)

        deception = final_state.get("deception_confidence_pct", 0)
        dbc = "#ef4444" if deception >= 75 else "#f59e0b" if deception >= 35 else "#10b981"
        st.markdown(f"""
        <div style='text-align:center;margin-top:15px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:12px;'>
          <span style='font-size:11px;text-transform:uppercase;color:#9ca3af;font-weight:600;'>DECEPTION PROBABILITY</span>
          <div style='font-size:26px;font-weight:800;color:{dbc};margin:3px 0;'>{deception}%</div>
        </div>
        """, unsafe_allow_html=True)

        if audit_id:
            try:
                pdf_bytes = get_api().get_audit_pdf(audit_id)
                st.download_button(
                    "📄 Export Audit Dossier (PDF)",
                    data=pdf_bytes,
                    file_name=f"veritas_audit_{audit_id}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as exc:
                st.warning(f"PDF unavailable: {exc}")

    with col_r:
        st.markdown("<h3 style='font-family:\"Space Grotesk\";font-size:18px;'>🔍 Triangulated Counter-Deception Synthesis</h3>", unsafe_allow_html=True)
        reasoning = final_state.get("llm_reasoning", "")
        if reasoning:
            st.markdown(f"""
            <div style='background:rgba(99,102,241,0.07);border:1px solid rgba(99,102,241,0.25);border-radius:8px;padding:14px;margin-bottom:14px;'>
              <div style='font-size:12px;text-transform:uppercase;color:#9ca3af;margin-bottom:6px;'>🧠 GPT-4o Reasoning</div>
              <div style='color:#e2e8f0;font-style:italic;'>{reasoning}</div>
            </div>
            """, unsafe_allow_html=True)

        insights = final_state.get("synthesis_insights", {})
        with st.expander("🔨 Track 1: Operational Ground Truth", expanded=True):
            st.markdown(f"*{insights.get('track_1_operational_ground_truth', 'N/A')}*")
        with st.expander("📈 Track 2: Resource & Logistics Flow", expanded=True):
            st.markdown(f"*{insights.get('track_2_financial_resource_flow', 'N/A')}*")
        with st.expander("📰 Track 3: Narrative Manipulation Analysis", expanded=True):
            st.markdown(f"*{insights.get('track_3_narrative_deception_analysis', 'N/A')}*")


# ── API bootstrap ─────────────────────────────────────────────────────────────
api = get_api()
base = api_base()
key = api_key()

try:
    health = api.health()
    api_ok, api_msg = True, health.get("service", "ok")
except Exception as exc:
    api_ok, api_msg = False, str(exc)

try:
    SUPPLIERS, SCENARIOS_RAW = _load_catalogs(base, key)
except Exception as exc:
    st.error(f"Cannot load catalog from Railway API: {exc}")
    st.info(f"Backend: `{base}` — check `/health` and `/v1/suppliers`")
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.markdown("<h2 style='font-family:\"Space Grotesk\";font-size: 22px; color: #6366f1;'>🌐 Railway API</h2>", unsafe_allow_html=True)
st.sidebar.code(base, language=None)
if api_ok:
    st.sidebar.success(f"✅ GET /health → {api_msg}")
else:
    st.sidebar.error(f"❌ GET /health failed: {api_msg}")

with st.sidebar.expander("GET /v1/health/config"):
    try:
        cfg = api.health_config()
        for row in cfg:
            icon = "✅" if row["status"] == "ok" else "⚠️" if row["status"] == "warn" else "❌"
            st.caption(f"{icon} **{row['label']}** — {row['detail']}")
    except Exception as exc:
        st.caption(f"Unavailable: {exc}")

st.sidebar.markdown("---")
scenario_id = st.sidebar.selectbox(
    "GET /v1/scenarios",
    list(SCENARIOS_RAW.keys()),
    format_func=lambda k: SCENARIOS_RAW[k]["label"],
)
if SCENARIOS_RAW[scenario_id].get("description"):
    st.sidebar.caption(SCENARIOS_RAW[scenario_id]["description"])

st.sidebar.markdown("---")
simulate_error = st.sidebar.selectbox(
    "Chaos injection (POST /v1/audits/run)",
    [None, "proxy_timeout", "bot_block", "payload_corruption"],
    format_func=lambda x: {
        None: "Nominal (no errors)",
        "proxy_timeout": "Proxy timeout",
        "bot_block": "Bot block",
        "payload_corruption": "Payload corruption",
    }.get(x),
)
hitl_mode = st.sidebar.checkbox("Human-in-the-loop (step=agents_only first)", value=False)

st.sidebar.markdown("---")
slack_webhook = st.sidebar.text_input(
    "Slack Webhook",
    value=secret("SLACK_WEBHOOK_URL"),
    type="password",
    help="Optional — Streamlit secret SLACK_WEBHOOK_URL",
)

# ── Header ────────────────────────────────────────────────────────────────────
col_logo, col_desc = st.columns([1, 15])
with col_logo:
    st.markdown("<h1 style='font-size: 60px; margin: 0;'>🛡️</h1>", unsafe_allow_html=True)
with col_desc:
    st.markdown("<div class='main-title'>VERITAS AI</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Streamlit UI → Railway FastAPI</div>", unsafe_allow_html=True)

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    st.markdown(f"<div class='metric-card'><div class='metric-label'>Suppliers</div><div class='metric-value'>{len(SUPPLIERS)}</div></div>", unsafe_allow_html=True)
with col_m2:
    st.markdown("<div class='metric-card'><div class='metric-label'>Backend</div><div class='metric-value' style='color:#6366f1;'>FastAPI</div></div>", unsafe_allow_html=True)
with col_m3:
    st.markdown("<div class='metric-card'><div class='metric-label'>Agents</div><div class='metric-value' style='color:#38bdf8;'>3</div></div>", unsafe_allow_html=True)
with col_m4:
    st.markdown("<div class='metric-card'><div class='metric-label'>Host</div><div class='metric-value' style='color:#34d399;font-size:22px;'>Railway</div></div>", unsafe_allow_html=True)

tab_live, tab_history = st.tabs(["🚀 Live Audit", "📜 Audit History"])

with tab_live:
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown("<h3>🌍 GET /v1/suppliers</h3>", unsafe_allow_html=True)
        map_rows = []
        for sid, val in SUPPLIERS.items():
            map_rows.append({
                "Supplier ID": sid,
                "Supplier Name": val["name"],
                "Zone": val["zone"],
                "Country": val["country"],
                "Risk": "Critical" if "High" in val["base_risk"] or "Critical" in val["base_risk"] else "Routine",
                "lat": val["lat"],
                "lon": val["lon"],
            })
        df_map = pd.DataFrame(map_rows)
        fig = px.scatter_mapbox(
            df_map, lat="lat", lon="lon", hover_name="Supplier Name",
            hover_data=["Supplier ID", "Zone", "Country", "Risk"],
            color="Risk", color_discrete_map={"Critical": "#ef4444", "Routine": "#10b981"},
            zoom=1.2, height=400,
        )
        fig.update_layout(
            mapbox_style="carto-darkmatter", margin={"r": 0, "t": 0, "l": 0, "b": 0},
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown("<h3>⚡ POST /v1/audits/run</h3>", unsafe_allow_html=True)
        supplier_key = st.selectbox(
            "Supplier",
            list(SUPPLIERS.keys()),
            format_func=lambda x: f"{SUPPLIERS[x]['name']} ({SUPPLIERS[x]['country']})",
        )
        try:
            detail = api.get_supplier(supplier_key)
            st.info(f"📍 **{detail['base_risk']}** · `{detail['zone']}` · lang `{detail['default_lang']}`")
        except Exception:
            detail = SUPPLIERS[supplier_key]
            st.info(f"📍 `{detail['zone']}`")

        try:
            history = api.supplier_score_history(supplier_key, limit=10)
            if history:
                hdf = pd.DataFrame(history)
                st.caption("GET /v1/suppliers/{id}/score-history")
                st.line_chart(hdf.set_index("created_at")["truth_score"])
        except Exception:
            pass

        audit_clicked = st.button("🚀 Run audit", type="primary", use_container_width=True)

        if hitl_mode and st.session_state.get("pending_state"):
            if st.button("▶️ POST /v1/audits/synthesize", use_container_width=True):
                try:
                    result = api.synthesize(st.session_state["pending_state"], save=True)
                    st.session_state.audit_results = {
                        "final_state": result["state"],
                        "supplier_key": supplier_key,
                        "supplier": SUPPLIERS[supplier_key],
                        "audit_id": result.get("audit_id"),
                    }
                    st.session_state.pending_state = None
                    st.rerun()
                except httpx.HTTPStatusError as exc:
                    st.error(exc.response.text)
                except Exception as exc:
                    st.error(str(exc))

    if "audit_results" not in st.session_state:
        st.session_state.audit_results = None
    if "pending_state" not in st.session_state:
        st.session_state.pending_state = None

    if audit_clicked:
        status = st.status(f"POST /v1/audits/run → {base}", expanded=True)
        step = "agents_only" if hitl_mode else "full"
        try:
            result = api.run_audit(
                supplier_key, scenario_id, simulate_error, step=step, save=not hitl_mode,
            )
        except httpx.HTTPStatusError as exc:
            status.update(label=f"❌ HTTP {exc.response.status_code}", state="error")
            st.error(exc.response.text)
            st.stop()
        except Exception as exc:
            status.update(label="❌ Request failed", state="error")
            st.error(str(exc))
            st.stop()

        if hitl_mode:
            st.session_state.pending_state = result["state"]
            status.update(label="✅ Agents complete — review logs, then synthesize.", state="complete")
            st.session_state.audit_results = {
                "final_state": result["state"],
                "supplier_key": supplier_key,
                "supplier": SUPPLIERS[supplier_key],
                "audit_id": None,
            }
        else:
            status.update(label="✅ Audit complete (full pipeline).", state="complete")
            score = result["state"].get("corporate_truth_score", 0)
            verdict = result["state"].get("status_verdict", "")
            if slack_webhook:
                asyncio.run(send_slack_alert(SUPPLIERS[supplier_key]["name"], score, verdict, slack_webhook))
            st.session_state.audit_results = {
                "final_state": result["state"],
                "supplier_key": supplier_key,
                "supplier": SUPPLIERS[supplier_key],
                "audit_id": result.get("audit_id"),
            }
            st.session_state.pending_state = None
        st.rerun()

    if st.session_state.audit_results:
        r = st.session_state.audit_results
        render_audit_results(r["final_state"], r["supplier_key"], r["supplier"], r.get("audit_id"))

with tab_history:
    st.markdown("<h3>GET /v1/audits</h3>", unsafe_allow_html=True)
    filter_sup = st.selectbox("Filter by supplier", [None] + list(SUPPLIERS.keys()), format_func=lambda x: "All suppliers" if x is None else SUPPLIERS[x]["name"])
    try:
        rows = api.list_audits(limit=50, supplier_id=filter_sup)
        if not rows:
            st.info("No saved audits yet.")
        else:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            audit_pick = st.selectbox("Load audit detail", rows, format_func=lambda r: f"#{r['id']} · {r['supplier_name']} · {r['truth_score']}/100 · {r['created_at'][:19]}")
            if st.button("Load GET /v1/audits/{id}"):
                detail_row = api.get_audit(audit_pick["id"])
                state = detail_row.get("final_state") or {}
                render_audit_results(
                    state,
                    detail_row["supplier_id"],
                    SUPPLIERS.get(detail_row["supplier_id"], {"name": detail_row["supplier_name"]}),
                    detail_row["id"],
                )
    except httpx.HTTPStatusError as exc:
        st.error(exc.response.text)
    except Exception as exc:
        st.error(str(exc))

st.markdown("<hr><p style='text-align:center;font-size:11px;color:#4b5563;'>Veritas AI · Streamlit → Railway FastAPI</p>", unsafe_allow_html=True)
