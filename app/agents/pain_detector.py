import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize
from app import compass_client
from app.logging_utils import log_event


def run(state: dict) -> dict:
    run_id = state["run_id"]
    journey_mapped = state["journey_mapped"]

    negative_reviews = [r for r in journey_mapped if r["sentiment"] in ("negative", "mixed")]

    if len(negative_reviews) < 2:
        log_event(run_id, "PainDetector", "cluster", "No negative reviews to cluster", "0 pain clusters found", confidence=1.0)
        return {"pain_clusters": []}

    texts = [r["text"] for r in negative_reviews]
    embeddings = compass_client.embed(texts)

    n_clusters = min(5, max(2, len(negative_reviews) // 3))
    X = normalize(np.array(embeddings))
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = km.fit_predict(X)

    clusters: dict[int, list] = {}
    for idx, label in enumerate(labels):
        clusters.setdefault(int(label), []).append(negative_reviews[idx])

    pain_clusters = []
    for cluster_id, cluster_reviews in clusters.items():
        sample_texts = "\n".join([f"- {r['text'][:250]}" for r in cluster_reviews[:5]])
        response = compass_client.chat(
            messages=[
                {"role": "system", "content": "You are a CX analyst. Respond with a single JSON object only. No explanation, no markdown, no extra text."},
                {
                    "role": "user",
                    "content": (
                        f"These reviews share a common complaint:\n{sample_texts}\n\n"
                        "Return a single JSON object: {\"pain_point\": \"3-5 word label\", \"journey_stage\": \"...\", "
                        "\"severity\": \"low|medium|high\", \"root_cause\": \"one sentence max\"}"
                    ),
                },
            ],
            max_tokens=350,
        )
        try:
            label_data = compass_client.extract_json(response)
            if isinstance(label_data, list):
                label_data = label_data[0] if label_data else {}
            if not isinstance(label_data, dict):
                raise ValueError("not a dict")
        except ValueError:
            label_data = {"pain_point": f"Issue group {cluster_id}", "severity": "medium", "journey_stage": "unknown", "root_cause": ""}

        pain_clusters.append({
            "cluster_id": cluster_id,
            "pain_point": label_data.get("pain_point", "Unknown issue"),
            "journey_stage": label_data.get("journey_stage", cluster_reviews[0].get("journey_stage", "unknown")),
            "severity": label_data.get("severity", "medium"),
            "root_cause": label_data.get("root_cause", ""),
            "frequency": len(cluster_reviews),
            "supporting_reviews": [r["text"][:200] for r in cluster_reviews[:3]],
        })

    severity_order = {"high": 0, "medium": 1, "low": 2}
    pain_clusters.sort(key=lambda x: (severity_order.get(x["severity"], 1), -x["frequency"]))

    log_event(
        run_id, "PainDetector", "cluster_pain_points",
        f"Embedded and clustered {len(negative_reviews)} negative reviews into {n_clusters} groups",
        f"Top pain: '{pain_clusters[0]['pain_point']}' ({pain_clusters[0]['severity']} severity, {pain_clusters[0]['frequency']} reviews)",
        target_agent="Recommender",
        confidence=0.81,
    )

    return {"pain_clusters": pain_clusters}
