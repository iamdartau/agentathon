#!/bin/bash
# CX Intelligence Agent — Demo Script
# Run this while screen recording for the hackathon video.
# Servers must be running: python3 run.py & streamlit run run_ui.py &

BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

pause() { sleep "$1"; }

banner() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

run_example() {
    local file=$1
    local label=$2
    echo -e "${YELLOW}▶  Running: $label${NC}"
    echo -e "   Input: $file"
    echo ""
    result=$(curl -s -X POST http://localhost:8000/run \
        -H "Content-Type: application/json" \
        -d @"$file")
    echo "$result" | python3 -c "
import json, sys
d = json.load(sys.stdin)
r = d.get('result', {})
bc = r.get('business_context', {})
ss = r.get('sentiment_summary', {})
pc = r.get('pain_clusters', [])
recs = r.get('recommendations', [])
ev = r.get('evaluation', {})

print(f'  Business type  : {bc.get(\"business_type\", \"?\").upper()}')
print(f'  Journey stages : {len(bc.get(\"journey_stages\", []))} inferred')
print(f'  Reviews        : {ss.get(\"total\", 0)} analysed')
print(f'  Sentiment      : {ss.get(\"positive\",0)} positive  {ss.get(\"negative\",0)} negative  {ss.get(\"mixed\",0)} mixed  {ss.get(\"neutral\",0)} neutral')
print(f'  Avg score      : {ss.get(\"avg_score\", 0):+.3f}')
print()
print(f'  Pain clusters ({len(pc)}):')
for c in pc:
    sev = c.get(\"severity\",\"?\")
    icon = \"🔴\" if sev==\"high\" else (\"🟡\" if sev==\"medium\" else \"🟢\")
    print(f'    {icon} [{sev.upper()}] {c.get(\"pain_point\",\"?\")}  ({c.get(\"frequency\",0)} reviews)')
print()
print(f'  Top recommendation:')
if recs:
    print(f'    #{recs[0].get(\"priority\")} {recs[0].get(\"recommendation\",\"\")[:90]}')
print()
decision = ev.get('decision','?')
icon = '✅' if decision == 'approved' else '🔄'
print(f'  Evaluator: {icon} {decision.upper()}  (confidence: {ev.get(\"confidence\",0):.2f})')
print(f'  Revisions: {r.get(\"revision_count\",0)}')
print(f'  Runtime  : {d.get(\"runtime_seconds\",0)}s')
"
    echo ""
}

# ── START ──────────────────────────────────────────────────────────────────

clear
banner "CX Intelligence Agent — G42 Agentathon — Use Case 18"
echo -e "  Multi-agent system: 6 LangGraph agents powered by Core42 Compass"
echo -e "  Vertical-agnostic: infers business type from review corpus"
echo ""
pause 2

# ── HEALTH ────────────────────────────────────────────────────────────────

banner "Step 1 — API Health Check"
echo -e "${YELLOW}▶  GET /health${NC}"
echo ""
curl -s http://localhost:8000/health | python3 -m json.tool
echo ""
pause 2

# ── RESTAURANT ────────────────────────────────────────────────────────────

banner "Step 2 — Restaurant Reviews (20 reviews, mixed sentiment)"
run_example "input_examples/example_1.json" "Restaurant"
pause 2

# ── AIRLINE ───────────────────────────────────────────────────────────────

banner "Step 3 — Airline Reviews (30 reviews — different vertical)"
run_example "input_examples/example_4.json" "Airline"
pause 2

# ── NEGATIVE ──────────────────────────────────────────────────────────────

banner "Step 4 — All-Negative Reviews (stress test)"
run_example "input_examples/example_negative.json" "All-negative restaurant"
pause 2

# ── POSITIVE ──────────────────────────────────────────────────────────────

banner "Step 5 — All-Positive Reviews (no pain points expected)"
run_example "input_examples/example_positive.json" "All-positive restaurant"
pause 2

# ── LOGS ──────────────────────────────────────────────────────────────────

banner "Step 6 — Agent Trace Log (last run)"
echo -e "${YELLOW}▶  tail logs/agent_trace.jsonl${NC}"
echo ""
tail -6 logs/agent_trace.jsonl | python3 -c "
import sys, json
for line in sys.stdin:
    d = json.loads(line.strip())
    ts = d['timestamp'][11:19]
    agent = d['agent_name']
    status = d['status']
    summary = d['output_summary'][:70]
    icon = '✅' if status == 'success' else ('🔄' if status == 'needs_revision' else '❌')
    print(f'  {ts}  {icon}  {agent:<15}  {summary}')
"
echo ""
pause 2

# ── UI ────────────────────────────────────────────────────────────────────

banner "Step 7 — Streamlit UI"
echo -e "  Open your browser at: ${GREEN}http://localhost:8501${NC}"
echo ""
echo -e "  Features:"
echo -e "    • Upload any JSON file or paste reviews"
echo -e "    • Sentiment tab — per-review breakdown with evidence"
echo -e "    • Journey tab — stage distribution chart"
echo -e "    • Pain Clusters — severity-sorted with root causes"
echo -e "    • Recommendations — evaluator critique + 5 actions"
echo ""
pause 2

# ── END ───────────────────────────────────────────────────────────────────

banner "Done"
echo -e "  Repo  : https://github.com/iamdartau/agentathon"
echo -e "  Tests : python3 -m pytest tests/ -v  (29 tests)"
echo -e "  Docker: docker build -t cx-intelligence . && docker run -p 8000:8000 --env-file .env cx-intelligence"
echo ""
