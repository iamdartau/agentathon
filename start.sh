#!/bin/bash
echo "Stopping any running servers..."
kill $(lsof -ti:8000) $(lsof -ti:8501) 2>/dev/null
sleep 2

echo "Starting API on http://localhost:8000 ..."
SAMPLE_MODE=true python3 run.py &

echo "Starting UI on http://localhost:8501 ..."
streamlit run run_ui.py --server.port 8501 --server.headless true &

sleep 5
curl -s http://localhost:8000/health > /dev/null && echo "API ready" || echo "API failed"
curl -s http://localhost:8501 > /dev/null && echo "UI ready" || echo "UI failed"
