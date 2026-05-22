"""Tests for compass_client — pure logic, no API calls."""
import json
import pytest
from unittest.mock import patch, MagicMock
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("OPENAI_BASE_URL", "https://api.core42.ai/v1")

from app.compass_client import extract_json, _is_reasoning_model, _cache_key


class TestExtractJson:
    def test_plain_json_object(self):
        assert extract_json('{"key": "value"}') == {"key": "value"}

    def test_plain_json_array(self):
        assert extract_json('[{"id": "r1"}]') == [{"id": "r1"}]

    def test_markdown_code_block(self):
        text = '```json\n{"key": "value"}\n```'
        assert extract_json(text) == {"key": "value"}

    def test_markdown_code_block_no_language(self):
        text = '```\n{"key": "value"}\n```'
        assert extract_json(text) == {"key": "value"}

    def test_json_embedded_in_text(self):
        text = 'Here is the result: {"decision": "approved", "confidence": 0.9} — done.'
        result = extract_json(text)
        assert result["decision"] == "approved"

    def test_array_embedded_in_text(self):
        text = 'Result: [{"id": "r1", "sentiment": "positive"}] end.'
        result = extract_json(text)
        assert isinstance(result, list)
        assert result[0]["sentiment"] == "positive"

    def test_raises_on_invalid(self):
        with pytest.raises(ValueError):
            extract_json("this is not json at all")

    def test_raises_on_empty(self):
        with pytest.raises(ValueError):
            extract_json("")

    def test_nested_json(self):
        data = {"result": {"pain_point": "slow service", "severity": "high"}}
        assert extract_json(json.dumps(data)) == data


class TestIsReasoningModel:
    def test_gpt51_is_reasoning(self):
        assert _is_reasoning_model("gpt-5.1") is True

    def test_o1_is_reasoning(self):
        assert _is_reasoning_model("o1-preview") is True

    def test_gpt41_is_not_reasoning(self):
        assert _is_reasoning_model("gpt-4.1") is False

    def test_gpt4_is_not_reasoning(self):
        assert _is_reasoning_model("gpt-4") is False


class TestCacheKey:
    def test_same_text_same_key(self):
        assert _cache_key("hello world") == _cache_key("hello world")

    def test_different_text_different_key(self):
        assert _cache_key("hello") != _cache_key("world")

    def test_key_is_hex_string(self):
        key = _cache_key("test")
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)
