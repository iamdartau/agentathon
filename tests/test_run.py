"""Tests for FastAPI endpoints — no real API calls."""
import json
import pytest
from unittest.mock import patch, MagicMock
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("OPENAI_BASE_URL", "https://api.core42.ai/v1")
os.environ["SAMPLE_MODE"] = "true"

from fastapi.testclient import TestClient
from run import app, _sentiment_summary, _stage_distribution, _normalise_reviews

client = TestClient(app)


class TestHealth:
    def test_health_returns_ok(self):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["service"] == "cx-intelligence-agent"
        assert "compass_configured" in data
        assert "sample_mode" in data


class TestNormaliseReviews:
    def test_standard_fields(self):
        raw = [{"id": "r1", "text": "Great food", "rating": 5, "source": "yelp"}]
        result = _normalise_reviews(raw)
        assert len(result) == 1
        assert result[0]["id"] == "r1"
        assert result[0]["text"] == "Great food"

    def test_fallback_id(self):
        raw = [{"text": "Good place"}]
        result = _normalise_reviews(raw)
        assert result[0]["id"] == "review_0"

    def test_content_alias(self):
        raw = [{"id": "r1", "content": "Nice spot"}]
        result = _normalise_reviews(raw)
        assert result[0]["text"] == "Nice spot"

    def test_empty_text_filtered(self):
        raw = [{"id": "r1", "text": "  "}, {"id": "r2", "text": "Good"}]
        result = _normalise_reviews(raw)
        assert len(result) == 1
        assert result[0]["id"] == "r2"

    def test_stars_alias(self):
        raw = [{"id": "r1", "text": "Nice", "stars": 4}]
        result = _normalise_reviews(raw)
        assert result[0]["rating"] == 4


class TestSentimentSummary:
    def test_counts_correctly(self):
        sentiments = [
            {"sentiment": "positive", "score": 0.9},
            {"sentiment": "negative", "score": -0.8},
            {"sentiment": "positive", "score": 0.7},
            {"sentiment": "neutral",  "score": 0.0},
            {"sentiment": "mixed",    "score": -0.2},
        ]
        result = _sentiment_summary(sentiments)
        assert result["positive"] == 2
        assert result["negative"] == 1
        assert result["neutral"] == 1
        assert result["mixed"] == 1
        assert result["total"] == 5
        assert result["avg_score"] == round((0.9 - 0.8 + 0.7 + 0.0 - 0.2) / 5, 3)

    def test_empty_returns_empty_dict(self):
        assert _sentiment_summary([]) == {}


class TestStageDistribution:
    def test_counts_stages(self):
        journey = [
            {"journey_stage": "Dining & Service"},
            {"journey_stage": "Dining & Service"},
            {"journey_stage": "Arrival & Seating"},
        ]
        result = _stage_distribution(journey)
        assert result["Dining & Service"] == 2
        assert result["Arrival & Seating"] == 1

    def test_unknown_fallback(self):
        result = _stage_distribution([{"no_stage_key": "x"}])
        assert result["unknown"] == 1


class TestRunEndpoint:
    def test_run_requires_min_two_reviews(self):
        with patch("run.workflow") as mock_wf:
            r = client.post("/run", json={"reviews": [
                {"id": "r1", "text": "Only one review"}
            ]})
        assert r.status_code == 400

    def test_run_no_api_key_returns_500(self):
        original = os.environ.pop("OPENAI_API_KEY", None)
        try:
            r = client.post("/run", json={})
            assert r.status_code == 500
        finally:
            if original:
                os.environ["OPENAI_API_KEY"] = original

    def test_run_with_mocked_workflow(self):
        mock_state = {
            "business_context": {"business_type": "restaurant", "journey_stages": []},
            "sentiments": [
                {"id": "r1", "sentiment": "positive", "score": 0.9},
                {"id": "r2", "sentiment": "negative", "score": -0.8},
            ],
            "journey_mapped": [
                {"journey_stage": "Dining & Service"},
                {"journey_stage": "Arrival & Seating"},
            ],
            "pain_clusters": [{"pain_point": "Slow service", "severity": "high", "frequency": 1}],
            "recommendations": [{"priority": 1, "recommendation": "Fix service"}],
            "evaluation": {"decision": "approved", "confidence": 0.9},
            "revision_count": 0,
        }
        with patch("run.workflow") as mock_wf:
            mock_wf.invoke.return_value = mock_state
            r = client.post("/run", json={"reviews": [
                {"id": "r1", "text": "Great food here!", "rating": 5},
                {"id": "r2", "text": "Service was too slow.", "rating": 2},
            ]})
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "success"
        assert data["use_case_id"] == "18"
        assert data["result"]["sentiment_summary"]["positive"] == 1
        assert data["result"]["sentiment_summary"]["negative"] == 1
        assert len(data["result"]["pain_clusters"]) == 1
        assert len(data["result"]["recommendations"]) == 1
