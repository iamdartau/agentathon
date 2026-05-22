# CX Intelligence Agent — G42 Agentathon

**Use Case 18: Customer Experience Intelligence**

A multi-agent system that ingests customer reviews, detects sentiment, maps friction to customer journey stages, clusters pain points via semantic embeddings, and generates prioritised CX recommendations — with an automatic critique and revision loop.

The system is **vertical-agnostic**: a Discovery Agent infers the business type and journey stages dynamically from the review corpus. The same pipeline works for restaurants, hotels, e-commerce stores, or any other domain without configuration changes.

---

## Architecture

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

---

## Agents

| Agent | Model | Role |
|-------|-------|------|
| `DiscoveryAgent` | gpt-4.1 | Infers business type and customer journey stages from the review corpus |
| `SentimentAgent` | gpt-4.1 | Classifies sentiment and extracts evidence per review |
| `JourneyMapper` | gpt-4.1 | Maps each review to the inferred customer journey stages |
| `PainDetector` | gpt-4.1 + text-embedding-3-large | Clusters pain points using semantic embeddings and labels each cluster |
| `Recommender` | gpt-4.1 | Generates prioritised CX improvement recommendations |
| `Evaluator` | gpt-5.1 | Critiques recommendations and triggers revision loop if output is weak |

---

## Setup

### 1. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set your Compass API key:

```env
OPENAI_API_KEY=your_compass_api_key_here
OPENAI_BASE_URL=https://api.core42.ai/v1
COMPASS_MODEL=gpt-4.1
COMPASS_REASONING_MODEL=gpt-5.1
COMPASS_EMBEDDING_MODEL=text-embedding-3-large
```

### 3. Run

```bash
# Standard mode
python3 run.py

# Sample mode — uses bundled Yelp reviews if no input provided
SAMPLE_MODE=true python3 run.py

# With auto-reload for development
uvicorn run:app --reload --port 8000
```

---

## Docker

```bash
docker build -t cx-intelligence .
docker run -p 8000:8000 --env-file .env cx-intelligence
```

---

## API

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
    "sentiment_summary": {
      "positive": 8, "negative": 10, "neutral": 0, "mixed": 2,
      "avg_score": -0.058, "total": 20
    },
    "journey_distribution": {
      "Dining & Service": 12,
      "Discovery & Reservation": 3,
      "Billing & Departure": 3
    },
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
        "pain_point_addressed": "Reservation system failures",
        "expected_impact": "Reduce no-show incidents by 70%, improve first impression",
        "effort": "medium",
        "evidence": "3 reviews mention lost bookings"
      }
    ],
    "evaluation": {
      "decision": "approved",
      "critique": "Recommendations are specific, actionable and evidence-backed.",
      "confidence": 0.88
    },
    "revision_count": 0
  }
}
```

---

## Examples

Three input/output pairs are included covering different verticals:

| File | Vertical | Reviews |
|------|----------|---------|
| `input_examples/example_1.json` | Restaurant | 20 reviews |
| `input_examples/example_2.json` | Hotel | 15 reviews |
| `input_examples/example_3.json` | E-commerce | 15 reviews |

Run any example:
```bash
curl -s -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d @input_examples/example_2.json | python3 -m json.tool
```

---

## Logs

All agent events are written as JSONL to `logs/agent_trace.jsonl`:

```bash
# Watch live
tail -f logs/agent_trace.jsonl

# Read pretty
cat logs/agent_trace.jsonl | python3 -c "
import sys, json
for line in sys.stdin:
    d = json.loads(line)
    print(d['agent_name'], '|', d['action'], '|', d['output_summary'][:80])
"
```

Each entry contains: `timestamp`, `run_id`, `agent_name`, `action`, `input_summary`, `output_summary`, `confidence`, `status`.

---

## Project Structure

```
agentathon/
├── run.py                        # FastAPI entry point
├── metadata.json                 # Hackathon submission metadata
├── requirements.txt
├── Dockerfile
├── .env.example                  # Copy to .env and fill in API key
│
├── app/
│   ├── compass_client.py         # Core42 Compass HTTP client
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
│   └── yelp_reviews_sample.json  # 20 bundled restaurant reviews
│
├── input_examples/               # 3 example inputs (restaurant, hotel, e-commerce)
├── output_examples/              # 3 real outputs from the pipeline
└── logs/
    └── agent_trace.jsonl         # Live run trace
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | Compass API key (required) |
| `OPENAI_BASE_URL` | `https://api.core42.ai/v1` | Compass base URL |
| `COMPASS_MODEL` | `gpt-4.1` | Main LLM for agents |
| `COMPASS_REASONING_MODEL` | `gpt-5.1` | Model for Evaluator |
| `COMPASS_EMBEDDING_MODEL` | `text-embedding-3-large` | Embeddings for clustering |
| `SAMPLE_MODE` | `false` | Use bundled data if no reviews provided |
| `VERIFY_SSL` | `false` | SSL certificate verification |
| `MAX_REVISIONS` | `2` | Maximum recommendation revision cycles |
| `PORT` | `8000` | Server port |
