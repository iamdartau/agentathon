"""Generate synthetic customer reviews for multiple verticals using Compass API."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app import compass_client

VERTICALS = [
    {
        "name": "airline",
        "description": "A mid-range international airline",
        "journey_stages": ["booking", "check-in", "boarding", "in-flight", "arrival", "baggage", "customer support"],
        "output": "input_examples/example_4.json",
    },
    {
        "name": "bank",
        "description": "A retail bank with mobile and branch services",
        "journey_stages": ["account opening", "mobile app", "branch visit", "loan/card application", "customer support", "fraud/dispute"],
        "output": "input_examples/example_5.json",
    },
    {
        "name": "gym",
        "description": "A mid-range urban gym and fitness centre",
        "journey_stages": ["membership signup", "facilities", "classes", "personal training", "equipment", "staff", "cancellation"],
        "output": "input_examples/example_6.json",
    },
    {
        "name": "clinic",
        "description": "A private healthcare clinic",
        "journey_stages": ["appointment booking", "waiting room", "consultation", "diagnosis", "follow-up", "billing", "reception"],
        "output": "input_examples/example_7.json",
    },
]

PROMPT = """Generate {n} realistic customer reviews for {description}.

Requirements:
- Mix of sentiments: roughly 40% negative, 35% positive, 15% mixed, 10% neutral
- Cover these journey stages naturally: {stages}
- Reviews should be 1-4 sentences, written in first person
- Vary the writing style (formal, casual, angry, enthusiastic)
- Include specific details (waiting times, staff names, prices, app features etc.)
- Ratings: 1-2 for negative, 4-5 for positive, 3 for mixed/neutral

Return a JSON array only. Each item:
{{"id": "r001", "text": "...", "rating": 1-5, "source": "google"}}

Number reviews sequentially: r001, r002, etc.
"""


def generate(vertical: dict, n: int = 30) -> list[dict]:
    print(f"Generating {n} reviews for {vertical['name']}...")
    response = compass_client.chat(
        messages=[
            {"role": "system", "content": "You are a dataset generator. Return only valid JSON arrays with no extra text."},
            {"role": "user", "content": PROMPT.format(
                n=n,
                description=vertical["description"],
                stages=", ".join(vertical["journey_stages"]),
            )},
        ],
        max_tokens=4000,
    )
    reviews = compass_client.extract_json(response)
    if isinstance(reviews, dict):
        reviews = reviews.get("reviews", [])
    print(f"  Got {len(reviews)} reviews")
    return reviews


def main():
    for vertical in VERTICALS:
        reviews = generate(vertical, n=30)
        out_path = Path(vertical["output"])
        out_path.parent.mkdir(exist_ok=True)
        out_path.write_text(json.dumps({"reviews": reviews}, indent=2))
        print(f"  Saved to {out_path}")
    print("\nDone.")


if __name__ == "__main__":
    main()
