import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

load_dotenv()

from app.orchestration import workflow
from app.schemas import RunRequest

app = FastAPI(title="CX Intelligence Agent — G42 Agentathon", version="1.0.0")

SAMPLE_DATA_PATH = Path("data/sample/yelp_reviews_sample.json")


def _load_sample_reviews() -> list[dict]:
    with SAMPLE_DATA_PATH.open() as f:
        return json.load(f)


def _normalise_reviews(raw: list[dict]) -> list[dict]:
    normalised = []
    for i, r in enumerate(raw):
        normalised.append({
            "id": r.get("id", f"review_{i}"),
            "text": r.get("text", r.get("content", "")),
            "rating": r.get("rating", r.get("stars")),
            "source": r.get("source", "input"),
        })
    return [r for r in normalised if r["text"].strip()]


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "cx-intelligence-agent",
        "compass_configured": bool(os.getenv("OPENAI_API_KEY")),
        "sample_mode": os.getenv("SAMPLE_MODE", "false").lower() == "true",
    }


@app.post("/run")
def run(request: RunRequest):
    start = time.time()
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    sample_mode = os.getenv("SAMPLE_MODE", "false").lower() == "true"

    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not set")

    if request.reviews:
        reviews = _normalise_reviews(request.reviews)
    elif sample_mode or not request.reviews:
        if not SAMPLE_DATA_PATH.exists():
            raise HTTPException(status_code=500, detail="No reviews provided and sample data not found")
        reviews = _normalise_reviews(_load_sample_reviews())
        sample_mode = True
    else:
        raise HTTPException(status_code=400, detail="Provide 'reviews' in request body")

    if len(reviews) < 2:
        raise HTTPException(status_code=400, detail="At least 2 reviews required")

    initial_state = {
        "run_id": run_id,
        "reviews": reviews,
        "sample_mode": sample_mode,
        "business_context": {},
        "sentiments": [],
        "journey_mapped": [],
        "pain_clusters": [],
        "recommendations": [],
        "evaluation": {},
        "revision_count": 0,
    }

    try:
        final_state = workflow.invoke(initial_state)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "trace_id": run_id, "message": str(exc)},
        )

    runtime = round(time.time() - start, 2)

    return {
        "status": "success",
        "use_case_id": "18",
        "trace_id": run_id,
        "runtime_seconds": runtime,
        "sample_mode": sample_mode,
        "agents_used": ["DiscoveryAgent", "SentimentAgent", "JourneyMapper", "PainDetector", "Recommender", "Evaluator"],
        "result": {
            "business_context": final_state.get("business_context", {}),
            "sentiments": final_state.get("sentiments", []),
            "sentiment_summary": _sentiment_summary(final_state.get("sentiments", [])),
            "journey_distribution": _stage_distribution(final_state.get("journey_mapped", [])),
            "pain_clusters": final_state.get("pain_clusters", []),
            "recommendations": final_state.get("recommendations", []),
            "evaluation": final_state.get("evaluation", {}),
            "revision_count": final_state.get("revision_count", 0),
        },
    }


def _sentiment_summary(sentiments: list[dict]) -> dict:
    if not sentiments:
        return {}
    counts = {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}
    total_score = 0.0
    for s in sentiments:
        counts[s.get("sentiment", "neutral")] = counts.get(s.get("sentiment", "neutral"), 0) + 1
        total_score += s.get("score", 0.0)
    return {**counts, "avg_score": round(total_score / len(sentiments), 3), "total": len(sentiments)}


def _stage_distribution(journey_mapped: list[dict]) -> dict:
    dist: dict[str, int] = {}
    for r in journey_mapped:
        stage = r.get("journey_stage", "unknown")
        dist[stage] = dist.get(stage, 0) + 1
    return dist


def _cli_run(input_path: str, output_path: str) -> None:
    """Run the pipeline on a local file and write results to output_path, then exit."""
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set. Copy .env.example to .env and fill in your Compass key.", file=sys.stderr)
        sys.exit(1)

    raw = json.loads(Path(input_path).read_text())
    # Accept both {"reviews": [...]} and bare [...]
    if isinstance(raw, list):
        reviews = _normalise_reviews(raw)
    elif isinstance(raw, dict) and "reviews" in raw:
        reviews = _normalise_reviews(raw["reviews"])
    else:
        print("ERROR: Input must be a JSON array of reviews or an object with a 'reviews' key.", file=sys.stderr)
        sys.exit(1)

    if len(reviews) < 2:
        print("ERROR: At least 2 reviews are required.", file=sys.stderr)
        sys.exit(1)

    run_id = f"run_{uuid.uuid4().hex[:8]}"
    start = time.time()

    initial_state = {
        "run_id": run_id,
        "reviews": reviews,
        "sample_mode": False,
        "business_context": {},
        "sentiments": [],
        "journey_mapped": [],
        "pain_clusters": [],
        "recommendations": [],
        "evaluation": {},
        "revision_count": 0,
    }

    final_state = workflow.invoke(initial_state)
    runtime = round(time.time() - start, 2)

    result = {
        "status": "success",
        "use_case_id": "18",
        "trace_id": run_id,
        "runtime_seconds": runtime,
        "sample_mode": False,
        "agents_used": ["DiscoveryAgent", "SentimentAgent", "JourneyMapper", "PainDetector", "Recommender", "Evaluator"],
        "result": {
            "business_context": final_state.get("business_context", {}),
            "sentiments": final_state.get("sentiments", []),
            "sentiment_summary": _sentiment_summary(final_state.get("sentiments", [])),
            "journey_distribution": _stage_distribution(final_state.get("journey_mapped", [])),
            "pain_clusters": final_state.get("pain_clusters", []),
            "recommendations": final_state.get("recommendations", []),
            "evaluation": final_state.get("evaluation", {}),
            "revision_count": final_state.get("revision_count", 0),
        },
    }

    Path(output_path).write_text(json.dumps(result, indent=2))
    print(f"Done. Output written to {output_path} ({runtime}s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CX Intelligence Agent — G42 Agentathon Use Case 18")
    parser.add_argument("--input", help="Path to input JSON file (CLI mode)")
    parser.add_argument("--output", help="Path to write output JSON file (CLI mode)")
    args = parser.parse_args()

    if args.input or args.output:
        if not args.input or not args.output:
            print("ERROR: Both --input and --output are required for CLI mode.", file=sys.stderr)
            sys.exit(1)
        _cli_run(args.input, args.output)
    else:
        port = int(os.getenv("PORT", "8000"))
        uvicorn.run(app, host="0.0.0.0", port=port)
