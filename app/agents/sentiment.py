import json
from app import compass_client
from app.logging_utils import log_event

BATCH_SIZE = 5


def run(state: dict) -> dict:
    run_id = state["run_id"]
    reviews = state["reviews"]
    business_type = state["business_context"].get("business_type", "business")

    results = []
    for i in range(0, len(reviews), BATCH_SIZE):
        batch = reviews[i: i + BATCH_SIZE]
        batch_text = "\n".join(
            [f'[{r["id"]}] {r["text"][:400]}' for r in batch]
        )

        response = compass_client.chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a sentiment analyst for {business_type} reviews. "
                        "Respond with valid JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Analyse these reviews and return a JSON array. "
                        f"Each item: {{\"id\": \"...\", \"sentiment\": \"positive|negative|neutral|mixed\", "
                        f"\"score\": -1.0 to 1.0, \"evidence\": \"key phrase from review\", "
                        f"\"journey_stage_hint\": \"which stage this review likely relates to\"}}:\n\n{batch_text}"
                    ),
                },
            ],
            max_tokens=800,
        )

        try:
            batch_results = compass_client.extract_json(response)
            if isinstance(batch_results, list):
                results.extend(batch_results)
        except ValueError:
            for r in batch:
                results.append({"id": r["id"], "sentiment": "neutral", "score": 0.0, "evidence": "", "journey_stage_hint": ""})

    positive = sum(1 for r in results if r.get("sentiment") == "positive")
    negative = sum(1 for r in results if r.get("sentiment") == "negative")

    log_event(
        run_id, "SentimentAgent", "analyse_sentiment",
        f"Processed {len(reviews)} reviews in {len(reviews) // BATCH_SIZE + 1} batches",
        f"Positive: {positive}, Negative: {negative}, Other: {len(results) - positive - negative}",
        target_agent="JourneyMapper",
        confidence=0.85,
    )

    return {"sentiments": results}
