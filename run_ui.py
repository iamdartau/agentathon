import json
import os
import time

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="CX Intelligence Agent",
    page_icon="🔍",
    layout="wide",
)

st.markdown("""
<style>
    div.stButton > button[kind="primary"] {
        background-color: #28a745;
        border-color: #28a745;
        color: white;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #218838;
        border-color: #1e7e34;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("CX Intelligence Agent")
    st.caption("G42 Agentathon · Use Case 18")
    st.divider()

    api_url = st.text_input("API URL", value=API_URL)

    health_ok = False
    try:
        r = requests.get(f"{api_url}/health", timeout=3)
        h = r.json()
        if h.get("status") == "ok":
            st.success("API connected")
            health_ok = True
        else:
            st.error("API unhealthy")
    except Exception:
        st.error("Cannot reach API")

    st.divider()
    st.markdown("**How it works**")
    st.markdown(
        "1. Paste reviews or use sample data\n"
        "2. Click **Run Analysis**\n"
        "3. Agents run in sequence:\n"
        "   - Discovery → Sentiment\n"
        "   - Journey mapping\n"
        "   - Pain clustering\n"
        "   - Recommendations\n"
        "   - Evaluator critique"
    )

# ── Main ─────────────────────────────────────────────────────────────────────

st.header("Customer Experience Intelligence")

input_mode = st.radio(
    "Input",
    ["Use sample data", "Paste JSON reviews", "Upload JSON file"],
    horizontal=True,
)

reviews = None

if input_mode == "Paste JSON reviews":
    example = json.dumps([
        {"id": "r1", "text": "Waited 45 minutes with a reservation. Hostess was rude.", "rating": 1, "source": "yelp"},
        {"id": "r2", "text": "Amazing food, attentive staff. Will definitely come back!", "rating": 5, "source": "yelp"},
        {"id": "r3", "text": "Food arrived cold and the waiter shrugged when we mentioned it.", "rating": 2, "source": "yelp"},
    ], indent=2)
    raw = st.text_area("Paste reviews as JSON array", value=example, height=200)
    try:
        reviews = json.loads(raw)
        st.caption(f"{len(reviews)} review(s) ready")
    except json.JSONDecodeError:
        st.warning("Invalid JSON")
        reviews = None

elif input_mode == "Upload JSON file":
    uploaded = st.file_uploader("Upload reviews JSON", type=["json"])
    if uploaded:
        try:
            data = json.load(uploaded)
            reviews = data.get("reviews", data) if isinstance(data, dict) else data
            st.caption(f"{len(reviews)} review(s) loaded")
        except Exception:
            st.error("Could not parse file")

else:
    st.info("Will use bundled sample data (20 Yelp restaurant reviews).")

run_btn = st.button("Run Analysis", type="primary", disabled=not health_ok)

# ── Run ───────────────────────────────────────────────────────────────────────

if run_btn:
    payload = {}
    if reviews:
        payload["reviews"] = reviews

    with st.spinner("Running agent pipeline…"):
        t0 = time.time()
        try:
            resp = requests.post(
                f"{api_url}/run",
                json=payload,
                timeout=180,
            )
            data = resp.json()
        except Exception as e:
            st.error(f"Request failed: {e}")
            st.stop()

    if data.get("status") != "success":
        st.error(f"Pipeline error: {data.get('message', 'unknown')}")
        st.stop()

    elapsed = round(time.time() - t0, 1)
    result = data["result"]

    # ── Header metrics ────────────────────────────────────────────────────────
    bc = result.get("business_context", {})
    ss = result.get("sentiment_summary", {})
    pc = result.get("pain_clusters", [])
    recs = result.get("recommendations", [])
    ev = result.get("evaluation", {})

    biz_type = bc.get("business_type", "unknown").title()
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Business type", biz_type)
    m2.metric("Reviews analysed", ss.get("total", 0))
    m3.metric("Pain clusters", len(pc))
    m4.metric("Recommendations", len(recs))
    m5.metric("Runtime", f"{elapsed}s")

    st.divider()

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Sentiment", "Journey", "Pain Clusters", "Recommendations", "Raw JSON"
    ])

    # Sentiment tab
    with tab1:
        st.subheader("Sentiment Summary")

        col_pos, col_neg, col_mix, col_neu = st.columns(4)
        col_pos.metric("Positive", ss.get("positive", 0), delta=None)
        col_neg.metric("Negative", ss.get("negative", 0), delta=None)
        col_mix.metric("Mixed", ss.get("mixed", 0), delta=None)
        col_neu.metric("Neutral", ss.get("neutral", 0), delta=None)

        avg = ss.get("avg_score", 0)
        if avg > 0.1:
            sentiment_label, label_colour = "Positive", "green"
        elif avg < -0.1:
            sentiment_label, label_colour = "Negative", "red"
        else:
            sentiment_label, label_colour = "Neutral", "gray"
        st.metric("Average sentiment score", f"{avg:+.3f}")
        st.markdown(f":{label_colour}[{sentiment_label}]")

        sentiments = result.get("sentiments") or []
        if sentiments:
            st.subheader("Per-review breakdown")
            colour_map = {"positive": "🟢", "negative": "🔴", "mixed": "🟡", "neutral": "⚪"}
            for s in sentiments:
                icon = colour_map.get(s.get("sentiment", "neutral"), "⚪")
                label = f"{icon} `{s['id']}` · **{s.get('sentiment','').upper()}** · score {s.get('score', 0):+.2f}"
                with st.expander(label):
                    st.write(f"**Evidence:** {s.get('evidence', '—')}")
                    st.write(f"**Journey stage hint:** {s.get('journey_stage_hint', '—')}")

    # Journey tab
    with tab2:
        st.subheader("Journey Stage Distribution")
        dist = result.get("journey_distribution", {})
        if dist:
            import pandas as pd
            df = pd.DataFrame(
                sorted(dist.items(), key=lambda x: -x[1]),
                columns=["Stage", "Reviews"]
            )
            st.bar_chart(df.set_index("Stage"))
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No journey distribution data.")

        stages = bc.get("journey_stages", [])
        if stages:
            st.subheader("Inferred journey stages")
            for i, s in enumerate(stages, 1):
                st.markdown(f"{i}. {s}")

    # Pain clusters tab
    with tab3:
        st.subheader("Pain Point Clusters")
        if not pc:
            st.info("No pain clusters detected.")
        else:
            sev_colour = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            for cluster in pc:
                sev = cluster.get("severity", "medium")
                icon = sev_colour.get(sev, "⚪")
                header = f"{icon} **{cluster.get('pain_point', 'Unknown')}** · {sev.upper()} · {cluster.get('frequency', 0)} reviews"
                with st.expander(header, expanded=(sev == "high")):
                    st.write(f"**Journey stage:** {cluster.get('journey_stage', '—')}")
                    st.write(f"**Root cause:** {cluster.get('root_cause', '—')}")
                    supporting = cluster.get("supporting_reviews", [])
                    if supporting:
                        st.write("**Supporting reviews:**")
                        for rev in supporting:
                            st.markdown(f"> {rev[:200]}")

    # Recommendations tab
    with tab4:
        st.subheader("CX Recommendations")

        decision = ev.get("decision", "unknown")
        revisions = result.get("revision_count", 0)
        if decision == "approved":
            st.success(f"Evaluator: APPROVED after {revisions} revision(s)")
        else:
            st.warning(f"Evaluator: {decision.upper()} · {revisions} revision(s)")

        if ev.get("critique"):
            with st.expander("Evaluator critique"):
                st.write(ev["critique"])
                issues = ev.get("specific_issues", [])
                if issues:
                    for issue in issues:
                        st.markdown(f"- {issue}")

        effort_colour = {"low": "🟢", "medium": "🟡", "high": "🔴"}
        for rec in recs:
            effort = rec.get("effort", "medium")
            icon = effort_colour.get(effort, "⚪")
            header = f"#{rec.get('priority', '?')} · {rec.get('recommendation', '')[:80]}"
            with st.expander(header, expanded=(rec.get("priority") == 1)):
                st.write(f"**Pain point addressed:** {rec.get('pain_point_addressed', '—')}")
                st.write(f"**Expected impact:** {rec.get('expected_impact', '—')}")
                st.write(f"**Effort:** {icon} {effort.title()}")
                st.write(f"**Evidence:** {rec.get('evidence', '—')}")

    # Raw JSON tab
    with tab5:
        st.subheader("Full API Response")
        st.json(data)
