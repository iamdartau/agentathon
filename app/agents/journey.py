from app import compass_client
from app.logging_utils import log_event

BATCH_SIZE = 15


def run(state: dict) -> dict:
    run_id = state["run_id"]
    sentiments = state["sentiments"]
    reviews_by_id = {r["id"]: r for r in state["reviews"]}
    stages = state["business_context"].get("journey_stages", ["discovery", "experience", "service", "loyalty"])

    results = []
    for i in range(0, len(sentiments), BATCH_SIZE):
        batch = sentiments[i: i + BATCH_SIZE]
        batch_text = "\n".join(
            [f'[{s["id"]}] ({s["sentiment"]}) {reviews_by_id.get(s["id"], {}).get("text", "")[:300]}' for s in batch]
        )

        response = compass_client.chat(
            messages=[
                {
                    "role": "system",
                    "content": "You are a customer journey expert. Respond with valid JSON only.",
                },
                {
                    "role": "user",
                    "content": (
                        f"Map each review to the most relevant journey stage from: {stages}.\n\n"
                        f"Return a JSON array. Each item: {{\"id\": \"...\", \"journey_stage\": \"...\", \"confidence\": 0.0-1.0}}:\n\n{batch_text}"
                    ),
                },
            ],
            max_tokens=500,
        )

        try:
            batch_results = compass_client.extract_json(response)
            if isinstance(batch_results, list):
                results.extend(batch_results)
        except ValueError:
            for s in batch:
                results.append({"id": s["id"], "journey_stage": stages[0], "confidence": 0.5})

    sentiment_map = {s["id"]: s for s in sentiments}
    reviews_by_id_full = {r["id"]: r for r in state["reviews"]}
    journey_mapped = []
    for r in results:
        sid = r["id"]
        journey_mapped.append({
            "id": sid,
            "text": reviews_by_id_full.get(sid, {}).get("text", ""),
            "sentiment": sentiment_map.get(sid, {}).get("sentiment", "neutral"),
            "score": sentiment_map.get(sid, {}).get("score", 0.0),
            "evidence": sentiment_map.get(sid, {}).get("evidence", ""),
            "journey_stage": r.get("journey_stage", stages[0]),
            "confidence": r.get("confidence", 0.5),
        })

    stage_counts = {}
    for r in journey_mapped:
        stage_counts[r["journey_stage"]] = stage_counts.get(r["journey_stage"], 0) + 1

    log_event(
        run_id, "JourneyMapper", "map_stages",
        f"Mapped {len(journey_mapped)} reviews to stages: {stages}",
        f"Stage distribution: {stage_counts}",
        target_agent="PainDetector",
        confidence=0.83,
    )

    return {"journey_mapped": journey_mapped}
