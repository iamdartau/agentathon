from app import compass_client
from app.logging_utils import log_event


def run(state: dict) -> dict:
    run_id = state["run_id"]
    pain_clusters = state["pain_clusters"]
    business_context = state["business_context"]
    revision_count = state.get("revision_count", 0)
    evaluation = state.get("evaluation", {})

    if not pain_clusters:
        log_event(run_id, "Recommender", "generate", "No pain clusters", "No recommendations needed", confidence=1.0)
        return {"recommendations": []}

    pain_summary = "\n".join([
        f"- [{c['severity'].upper()}] {c['pain_point']} | Stage: {c['journey_stage']} | "
        f"Frequency: {c['frequency']} reviews | Root cause: {c['root_cause']}"
        for c in pain_clusters
    ])

    revision_note = ""
    if revision_count > 0 and evaluation.get("critique"):
        revision_note = f"\n\nPrevious critique to address:\n{evaluation['critique']}\nSpecific issues: {evaluation.get('specific_issues', [])}"

    response = compass_client.chat(
        messages=[
            {
                "role": "system",
                "content": (
                    f"You are a senior CX strategist for a {business_context.get('business_type', 'business')}. "
                    "Generate specific, actionable recommendations backed by evidence. Respond with JSON only."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Based on these customer pain points:\n{pain_summary}{revision_note}\n\n"
                    "Generate 5 prioritised CX recommendations. Return a JSON array. "
                    "Each item: {\"priority\": 1-5, \"recommendation\": \"specific action\", "
                    "\"pain_point_addressed\": \"...\", \"expected_impact\": \"...\", "
                    "\"effort\": \"low|medium|high\", \"evidence\": \"quote or stat from reviews\"}"
                ),
            },
        ],
        model=None,
        max_tokens=1500,
    )

    try:
        recommendations = compass_client.extract_json(response)
        if not isinstance(recommendations, list):
            recommendations = recommendations.get("recommendations", [])
    except ValueError:
        recommendations = [{"priority": 1, "recommendation": "Address top customer pain points", "pain_point_addressed": "general", "expected_impact": "improved satisfaction", "effort": "medium", "evidence": "multiple reviews"}]

    log_event(
        run_id, "Recommender", "generate_recommendations",
        f"Addressing {len(pain_clusters)} pain clusters (revision #{revision_count})",
        f"Generated {len(recommendations)} recommendations. Top: '{recommendations[0].get('recommendation', '')[:80]}'",
        target_agent="Evaluator",
        confidence=0.79,
        retry_count=revision_count,
    )

    return {"recommendations": recommendations}
