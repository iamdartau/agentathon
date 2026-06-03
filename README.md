# CX Intelligence Agent — G42 Agentathon

**Use Case 18: Customer Experience Intelligence**

## 1. Problem Statement

Businesses receive thousands of customer reviews across platforms but cannot extract actionable intelligence from them at scale. Manual review is too slow. Generic sentiment tools return a score but not a fix. CX teams cannot tell which stage of the customer journey is broken, which complaints are clustered around the same root cause, or which interventions will have the highest impact.

## 2. Use Case ID

**Use Case 18 — Customer Experience Intelligence**

Domain: Customer / Commercial | Difficulty: Medium | Output type: text

## 3. Solution Overview

A multi-agent system that ingests customer reviews, detects sentiment, maps friction to customer journey stages, clusters pain points via semantic embeddings, and generates prioritised CX recommendations — with an automatic critique and revision loop.

The system is **vertical-agnostic**: a Discovery Agent infers the business type and journey stages dynamically from the review corpus. The same pipeline works for restaurants, hotels, e-commerce stores, airlines, clinics, or any other domain without configuration changes.

## 4. Agent Architecture

```
Reviews in
    │
    ▼
DiscoveryAgent ──► infers business type + journey stages from corpus
    │
    ▼
SentimentAgent ──► classifies each review (positive/negative/neutral/mixed)
    │
    ▼
JourneyMapper ──► assigns each review to an inferred journey stage
    │
    ▼
PainDetector ──► embeds negative reviews → KMeans clusters → labels each cluster
    │
    ▼
Recommender ──► generates 5 prioritised CX recommendations
    │
    ▼
Evaluator ──► critiques recommendations
    │
    ├── revision_needed? ──► back to Recommender (max 2 revisions)
    │
    └── approved? ──► END
```

Orchestrated with **LangGraph** StateGraph. All LLM calls go through **Core42 Compass** (`gpt-4.1` for agents, `gpt-5.1` for evaluation, `text-embedding-3-large` for clustering).

| Agent | Model | Role |
|-------|-------|------|
| `DiscoveryAgent` | gpt-4.1 | Infers business type and customer journey stages from the review corpus |
| `SentimentAgent` | gpt-4.1 | Classifies sentiment and extracts evidence per review |
| `JourneyMapper` | gpt-4.1 | Maps each review to the inferred customer journey stages |
| `PainDetector` | gpt-4.1 + text-embedding-3-large | Clusters pain points using semantic embeddings and labels each cluster |
| `Recommender` | gpt-4.1 | Generates prioritised CX improvement recommendations |
| `Evaluator` | gpt-5.1 | Critiques recommendations and triggers revision loop if output is weak |

## 5. Agent Collaboration Flow

```
DiscoveryAgent → SentimentAgent → JourneyMapper → PainDetector → Recommender ⇄ Evaluator
```

The non-linear element is the **Recommender ↔ Evaluator** loop. After Recommender produces recommendations, Evaluator (running on gpt-5.1) critiques them. If they are too vague or lack specificity, it returns `revision_needed` and Recommender runs again with the critique as context. This repeats up to `MAX_REVISIONS` times (default: 2). All interactions are logged to `logs/agent_trace.jsonl`.

## 6. Tools, Frameworks, and Models Used

| Category | Technology |
|----------|-----------|
| Language | Python 3.12 |
| API Framework | FastAPI |
| Agent Orchestration | LangGraph (StateGraph) |
| LLM Provider | Core42 Compass (OpenAI-compatible API) |
| Models | gpt-4.1, gpt-5.1, text-embedding-3-large |
| Clustering | scikit-learn (KMeans), numpy |
| UI | Streamlit |
| Containerisation | Docker |

## 7. Data Sources

| Source | Type | Usage |
|--------|------|-------|
| `data/sample/yelp_reviews_sample.json` | Bundled sample (Yelp Open Dataset subset) | Default data when `SAMPLE_MODE=true` |
| `input_examples/*.json` | Hand-crafted examples | 9 examples across 7 verticals |

No external APIs are called at runtime. All LLM/embedding calls go through Compass.

## 8. Repository Structure

```
agentathon/
├── run.py                        # FastAPI entry point + optional CLI mode
├── run_ui.py                     # Streamlit UI (port 8001)
├── metadata.json                 # Hackathon submission metadata
├── requirements.txt
├── Dockerfile
├── .env.example                  # Copy to .env and fill in API key
│
├── app/
│   ├── compass_client.py         # Core42 Compass HTTP client + embedding cache
│   ├── logging_utils.py          # JSONL trace logger
│   ├── orchestration.py          # LangGraph workflow
│   ├── schemas.py                # Pydantic request/response models
│   └── agents/
│       ├── discovery.py
│       ├── sentiment.py
│       ├── journey.py
│       ├── pain_detector.py
│       ├── recommender.py
│       └── evaluator.py
│
├── data/sample/
│   └── yelp_reviews_sample.json  # Bundled restaurant reviews
│
├── input_examples/               # 9 example inputs across 7 verticals
├── output_examples/              # 7 real outputs from the pipeline
├── tests/                        # Pytest suite (29 tests, no API calls)
└── logs/
    ├── agent_trace.jsonl         # Live run trace
    └── sample_trace.jsonl        # Pre-generated sample trace
```

## 9. Environment Variables

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `OPENAI_API_KEY` | ✅ | — | Compass API key |
| `OPENAI_BASE_URL` | ✅ | `https://api.core42.ai/v1` | Compass base URL |
| `COMPASS_MODEL` | No | `gpt-4.1` | Main LLM for agents |
| `COMPASS_REASONING_MODEL` | No | `gpt-5.1` | Model for Evaluator |
| `COMPASS_EMBEDDING_MODEL` | No | `text-embedding-3-large` | Embeddings for clustering |
| `SAMPLE_MODE` | No | `false` | Use bundled data if no reviews provided |
| `VERIFY_SSL` | No | `false` | SSL certificate verification |
| `MAX_REVISIONS` | No | `2` | Maximum recommendation revision cycles |
| `PORT` | No | `8000` | Server port |

## 10. Setup Instructions

### Prerequisites

- Python 3.11+
- Git
- Docker (recommended)
- Compass API key

### 1. Clone the repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd agentathon
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY to your Compass key
```

## 11. How to Run Locally

### API server mode (primary)

```bash
source .env
python3 run.py
```

Server starts on `http://localhost:8000`. Test with:

```bash
curl http://localhost:8000/health
```

### CLI mode (file-based, for local testing)

```bash
source .env && python3 run.py --input input_examples/example_1.json --output output.json
```

Runs the full pipeline, writes the result JSON to `output.json`, and exits.

### Sample mode (no reviews required)

```bash
SAMPLE_MODE=true python3 run.py
```

## 12. How to Run with Docker

### Step 1 — Build the image

```bash
docker build -t cx-intelligence .
```

### Step 2 — Create your `.env` file (if you haven't already)

```bash
cp .env.example .env
# Open .env and set OPENAI_API_KEY to your Compass key
```

### Step 3 — Start the API container

```bash
docker run -d --name cx-agent -p 8000:8000 --env-file .env cx-intelligence
```

> **Why `--env-file .env`?** This is the safest way to pass credentials — no risk of accidentally passing an empty string, no secrets in your shell history.

### Step 4 — Verify it started correctly

```bash
curl http://localhost:8000/health
```

Expected response — **`compass_configured` must be `true`** before proceeding:

```json
{
  "status": "ok",
  "service": "cx-intelligence-agent",
  "compass_configured": true,
  "sample_mode": false
}
```

If you see `compass_configured: false`, the API key was not passed. Stop the container and check your `.env` file:

```bash
docker stop cx-agent && docker rm cx-agent
# Fix .env, then run Step 3 again
```

### Step 5 — Run a test request

```bash
curl -s -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d @input_examples/example_1.json | python3 -m json.tool
```

### Step 6 — Start the UI (optional)

The UI runs outside Docker and connects to the API on port 8000:

```bash
streamlit run run_ui.py --server.port 8001
```

Open **http://localhost:8001**. Check the sidebar — it must show **"API connected"** before clicking Run Analysis.

### Stop the container

```bash
docker stop cx-agent && docker rm cx-agent
```

## 13. API Usage

### `GET /health`

```json
{
  "status": "ok",
  "service": "cx-intelligence-agent",
  "compass_configured": true,
  "sample_mode": false
}
```

### `POST /run`

**Request:**
```json
{
  "reviews": [
    {"id": "r001", "text": "Waited 45 minutes with a reservation. Hostess was rude.", "rating": 1, "source": "yelp"},
    {"id": "r002", "text": "Amazing food and attentive staff. Will be back.", "rating": 5, "source": "yelp"}
  ]
}
```

If `reviews` is omitted and `SAMPLE_MODE=true`, the system uses bundled sample data.

**Response:**
```json
{
  "status": "success",
  "use_case_id": "18",
  "trace_id": "run_abc12345",
  "runtime_seconds": 28.3,
  "sample_mode": false,
  "agents_used": ["DiscoveryAgent", "SentimentAgent", "JourneyMapper", "PainDetector", "Recommender", "Evaluator"],
  "result": {
    "business_context": {
      "business_type": "restaurant",
      "journey_stages": ["Discovery & Reservation", "Arrival & Seating", "Dining & Service", "Billing & Departure", "Post-Visit Support"],
      "analysis_summary": "..."
    },
    "sentiment_summary": {"positive": 8, "negative": 10, "neutral": 0, "mixed": 2, "avg_score": -0.058, "total": 20},
    "journey_distribution": {"Dining & Service": 12, "Discovery & Reservation": 3},
    "pain_clusters": [
      {
        "pain_point": "Reservation system failures",
        "journey_stage": "Discovery & Reservation",
        "severity": "high",
        "root_cause": "Online booking system loses reservations and sends no confirmation",
        "frequency": 3
      }
    ],
    "recommendations": [
      {
        "priority": 1,
        "recommendation": "Audit and upgrade the online reservation system...",
        "expected_impact": "Reduce no-show incidents by 70%",
        "effort": "medium",
        "evidence": "3 reviews mention lost bookings"
      }
    ],
    "evaluation": {"decision": "approved", "confidence": 0.88},
    "revision_count": 0
  }
}
```

## 14. Input and Output Examples

Nine input examples covering 7 verticals:

| File | Vertical | Reviews |
|------|----------|---------|
| `input_examples/example_1.json` | Restaurant (mixed) | 20 |
| `input_examples/example_2.json` | Hotel (mixed) | 15 |
| `input_examples/example_3.json` | E-commerce (mixed) | 15 |
| `input_examples/example_4.json` | Airline (mixed) | 30 |
| `input_examples/example_5.json` | Bank (mixed) | 30 |
| `input_examples/example_6.json` | Gym (mixed) | 30 |
| `input_examples/example_7.json` | Clinic (mixed) | 30 |
| `input_examples/example_positive.json` | Restaurant (all positive) | 20 |
| `input_examples/example_negative.json` | Restaurant (all negative) | 20 |

Corresponding real outputs are in `output_examples/`.

Run any example:
```bash
curl -s -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d @input_examples/example_4.json | python3 -m json.tool
```

## 15. Logs and Traces

All agent events are written as JSONL to `logs/agent_trace.jsonl`:

```bash
# Watch live
tail -f logs/agent_trace.jsonl

# Read formatted
cat logs/agent_trace.jsonl | python3 -c "
import sys, json
for line in sys.stdin:
    d = json.loads(line)
    print(d['agent_name'], '|', d['action'], '|', d['output_summary'][:80])
"
```

Each entry contains: `timestamp`, `run_id`, `agent_name`, `action`, `input_summary`, `output_summary`, `target_agent`, `confidence`, `retry_count`, `status`.

A pre-generated sample trace is at `logs/sample_trace.jsonl`.

## 16. Demo Video

[To be added before submission]

The demo covers: problem overview, 6-agent pipeline, live `/run` execution, revision loop in action, Streamlit UI walkthrough.

## 17. Streamlit UI (Optional)

A visual interface is included for interactive demos.

```bash
# Start the API first
python3 run.py &

# Start the UI on port 8001
streamlit run run_ui.py --server.port 8001
```

Open **http://localhost:8001**. Features:
- Upload any JSON file or paste reviews directly
- Sentiment tab — per-review breakdown with evidence quotes
- Journey tab — stage distribution bar chart
- Pain Clusters tab — severity-sorted cards with root causes
- Recommendations tab — evaluator critique + 5 priority actions
- Raw JSON tab — full API response

## 18. Tests

```bash
python3 -m pytest tests/ -v
```

29 tests covering `extract_json`, review normalisation, sentiment summary, stage distribution, and API endpoints. No API calls required — all external dependencies are mocked.

## 19. Compass Integration

This project uses Compass through the OpenAI-compatible API. Set `OPENAI_API_KEY` and `OPENAI_BASE_URL` in your `.env` file.

Verify your Compass connection:
```bash
curl "$OPENAI_BASE_URL/models" -H "Authorization: Bearer $OPENAI_API_KEY"
```

## 20. Known Limitations

1. Runtime on large review sets (100+) may approach 5–8 minutes due to batched LLM calls.
2. Embedding cache is in-process memory; cleared on restart (disk cache in `cache/` persists across restarts).
3. KMeans cluster count is fixed at min(4, n_negative_reviews); very small sets produce fewer clusters.
4. No authentication on the `/run` endpoint — not suitable for production without an API gateway.
5. The revision loop caps at `MAX_REVISIONS=2`; the Evaluator may still flag weaknesses on the final pass.

## 21. Future Improvements

1. **Streaming responses** — push agent status updates to the client as they happen via SSE.
2. **Multi-source ingestion** — Google Maps, TripAdvisor, App Store reviews via adapters.
3. **Trend analysis** — compare current review batch against historical baseline to detect sentiment drift.
4. **Human-in-the-loop** — optional review of recommendations before output is finalised.
5. **Production deployment** — containerise with persistent volume for cache/logs, add auth, deploy to Kubernetes.
