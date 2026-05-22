import hashlib
import os
import json
import re
import requests
import urllib3
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_CACHE_PATH = Path("cache/embeddings.json")
_embed_cache: dict[str, list[float]] = {}


def _load_cache() -> None:
    if _CACHE_PATH.exists():
        try:
            _embed_cache.update(json.loads(_CACHE_PATH.read_text()))
        except Exception:
            pass


def _save_cache() -> None:
    _CACHE_PATH.parent.mkdir(exist_ok=True)
    _CACHE_PATH.write_text(json.dumps(_embed_cache))


def _cache_key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


_load_cache()


def _base() -> str:
    return os.environ.get("OPENAI_BASE_URL", "https://api.core42.ai/v1").rstrip("/")


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
        "Content-Type": "application/json",
    }


def _verify() -> bool:
    return os.environ.get("VERIFY_SSL", "false").lower() == "true"


def _is_reasoning_model(model: str) -> bool:
    return "5." in model or model.startswith("o")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
def chat(messages: list[dict], model: str | None = None, max_tokens: int = 1000, temperature: float = 0.2) -> str:
    model = model or os.environ.get("COMPASS_MODEL", "gpt-4.1")
    reasoning = _is_reasoning_model(model)
    token_key = "max_completion_tokens" if reasoning else "max_tokens"
    payload: dict = {"model": model, "messages": messages, token_key: max_tokens, "stream": False}
    if not reasoning:
        payload["temperature"] = temperature
    resp = requests.post(
        f"{_base()}/chat/completions",
        headers=_headers(),
        json=payload,
        verify=_verify(),
        timeout=120,
    )
    if not resp.ok:
        raise requests.HTTPError(f"HTTP {resp.status_code} from chat: {resp.text[:300]}", response=resp)
    return resp.json()["choices"][0]["message"]["content"]


def embed(texts: list[str]) -> list[list[float]]:
    results: list[list[float] | None] = [None] * len(texts)
    missing_indices: list[int] = []
    missing_texts: list[str] = []

    for i, text in enumerate(texts):
        key = _cache_key(text)
        if key in _embed_cache:
            results[i] = _embed_cache[key]
        else:
            missing_indices.append(i)
            missing_texts.append(text)

    if missing_texts:
        fetched = _embed_api(missing_texts)
        for i, (idx, text) in enumerate(zip(missing_indices, missing_texts)):
            results[idx] = fetched[i]
            _embed_cache[_cache_key(text)] = fetched[i]
        _save_cache()

    return results  # type: ignore[return-value]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
def _embed_api(texts: list[str]) -> list[list[float]]:
    model = os.environ.get("COMPASS_EMBEDDING_MODEL", "text-embedding-3-large")
    resp = requests.post(
        f"{_base()}/embeddings",
        headers=_headers(),
        json={"model": model, "input": texts},
        verify=_verify(),
        timeout=120,
    )
    if not resp.ok:
        raise requests.HTTPError(f"HTTP {resp.status_code} from embed: {resp.text[:300]}", response=resp)
    return [item["embedding"] for item in resp.json()["data"]]


def extract_json(text: str) -> dict | list:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Cannot extract JSON from: {text[:200]}")
