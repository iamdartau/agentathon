import os
from app import compass_client
from app.logging_utils import log_event


def run(state: dict) -> dict:
    run_id = state["run_id"]
    recommendations = state["recommendations"]
    pain_clusters = state["pain_clusters"]
    revision_count = state.get("revision_count", 0)

    if not recommendations:
        return {"evaluation": {"decision": "approved", "critique": "No pain points to address.", "specific_issues": []}}

    recs_text = "\n".join([
        f"{i+1}. [{r.get('effort','?')} effort] {r.get('recommendation','')}: {r.get('expected_impact','')}"
        for i, r in enumerate(recommendations)
    ])
    pain_text = "\n".join([f"- {c['pain_point']} ({c['severity']}, {c['frequency']} mentions)" for c in pain_clusters])

    response = compass_client.chat(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a critical CX consultant. Evaluate recommendations for specificity, "
                    "actionability, and evidence backing. Be demanding. Respond with JSON only."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Pain points identified:\n{pain_text}\n\n"
                    f"Recommendations to evaluate:\n{recs_text}\n\n"
                    "Evaluate rigorously. Be concise — max 2 sentences for critique, max 3 specific issues. "
                    "Return JSON only: {\"decision\": \"approved|revision_needed\", "
                    "\"critique\": \"2 sentence max\", "
                    "\"specific_issues\": [\"up to 3 short issues\"], "
                    "\"confidence\": 0.0-1.0}"
                ),
            },
        ],
        model=os.environ.get("COMPASS_REASONING_MODEL", "gpt-5.1"),
        max_tokens=1200,
    )

    try:
        evaluation = compass_client.extract_json(response)
        if isinstance(evaluation, list):
            evaluation = evaluation[0] if evaluation else {}
        if not isinstance(evaluation, dict):
            raise ValueError("not a dict")
    except ValueError:
        evaluation = {"decision": "approved", "critique": "Evaluation parse error, approving by default.", "specific_issues": [], "confidence": 0.7}

    decision = evaluation.get("decision", "approved")
    new_revision_count = revision_count + 1 if decision == "revision_needed" else revision_count

    log_event(
        run_id, "Evaluator", "critique_recommendations",
        f"Evaluated {len(recommendations)} recommendations (attempt #{revision_count + 1})",
        f"Decision: {decision.upper()} | {evaluation.get('critique', '')[:150]}",
        target_agent="Recommender" if decision == "revision_needed" else None,
        confidence=evaluation.get("confidence", 0.8),
        status="needs_revision" if decision == "revision_needed" else "success",
    )

    return {"evaluation": evaluation, "revision_count": new_revision_count}
