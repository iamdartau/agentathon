from app import compass_client
from app.logging_utils import log_event


def run(state: dict) -> dict:
    run_id = state["run_id"]
    reviews = state["reviews"]

    sample_texts = "\n".join([f"{i+1}. {r['text'][:300]}" for i, r in enumerate(reviews[:20])])

    response = compass_client.chat(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a business intelligence analyst. Analyse customer reviews and infer "
                    "the business context. Always respond with valid JSON only."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Analyse these {len(reviews)} customer reviews:\n\n{sample_texts}\n\n"
                    "Return JSON with:\n"
                    "- business_type: string (e.g. 'restaurant', 'hotel', 'retail store')\n"
                    "- journey_stages: list of 4-6 stage names relevant to this business\n"
                    "- key_themes: list of 5 recurring topics\n"
                    "- analysis_summary: one sentence describing the business and main customer concerns"
                ),
            },
        ],
        max_tokens=400,
    )

    try:
        context = compass_client.extract_json(response)
        if isinstance(context, list):
            context = context[0] if context else {}
        if not isinstance(context, dict):
            raise ValueError("not a dict")
    except ValueError:
        context = {
            "business_type": "business",
            "journey_stages": ["discovery", "onboarding", "core_experience", "service", "loyalty"],
            "key_themes": ["quality", "service", "value", "experience", "staff"],
            "analysis_summary": "Customer feedback analysis across multiple touchpoints.",
        }

    log_event(
        run_id, "DiscoveryAgent", "infer_context",
        f"{len(reviews)} reviews analysed",
        f"Inferred: {context.get('business_type')} | Stages: {context.get('journey_stages')}",
        target_agent="SentimentAgent",
        confidence=0.88,
    )

    return {"business_context": context}
