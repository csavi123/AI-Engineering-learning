"""Tiny client the Streamlit pages use to talk to the FastAPI backend.

Why go through HTTP instead of importing the backend directly? It keeps a hard
wall between the UI and the API key: this process never loads .env's key.
"""
import json
import os
from typing import Any, Dict, Iterator, List, Optional

import requests

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


class BackendError(Exception):
    """Raised with a human-readable message when the backend call fails."""


def _handle(resp: requests.Response) -> Dict[str, Any]:
    if resp.ok:
        return resp.json()
    # FastAPI puts our friendly error text in "detail".
    try:
        detail = resp.json().get("detail", resp.text)
    except ValueError:
        detail = resp.text
    raise BackendError(str(detail))


def _get(path: str) -> Dict[str, Any]:
    try:
        return _handle(requests.get(f"{BACKEND_URL}{path}", timeout=10))
    except requests.ConnectionError:
        raise BackendError(
            f"Can't reach the backend at {BACKEND_URL}. Is uvicorn running?"
        )


def _post(path: str, body: Dict[str, Any], timeout: float = 120) -> Dict[str, Any]:
    try:
        return _handle(requests.post(f"{BACKEND_URL}{path}", json=body, timeout=timeout))
    except requests.ConnectionError:
        raise BackendError(
            f"Can't reach the backend at {BACKEND_URL}. Is uvicorn running?"
        )


def health() -> Dict[str, Any]:
    return _get("/health")


def get_config() -> Dict[str, Any]:
    return _get("/config")


def call(
    messages: List[Dict[str, str]],
    *,
    model: Optional[str] = None,
    system: Optional[str] = None,
    max_tokens: int = 1024,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    top_k: Optional[int] = None,
) -> Dict[str, Any]:
    """One Claude call. Returns text, input_tokens, output_tokens,
    stop_reason, estimated_cost_usd, model."""
    body = {
        "messages": messages,
        "model": model,
        "system": system,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "top_k": top_k,
    }
    return _post("/call", body)


def stream(
    messages: List[Dict[str, str]],
    *,
    model: Optional[str] = None,
    system: Optional[str] = None,
    max_tokens: int = 1024,
) -> Iterator[Dict[str, Any]]:
    """Yield streaming events from the backend as they arrive.

    Each event is {"type": "text", "text", "t"} and the last one is
    {"type": "done", ...same fields as call()...}.
    """
    body = {"messages": messages, "model": model, "system": system, "max_tokens": max_tokens}
    try:
        # stream=True tells requests not to wait for the whole response.
        with requests.post(f"{BACKEND_URL}/stream", json=body, stream=True, timeout=120) as resp:
            if not resp.ok:
                _handle(resp)  # raises BackendError with the message
            for line in resp.iter_lines():
                if not line:
                    continue
                event = json.loads(line)
                if event["type"] == "error":
                    raise BackendError(event["detail"])
                yield event
    except requests.ConnectionError:
        raise BackendError(
            f"Can't reach the backend at {BACKEND_URL}. Is uvicorn running?"
        )


def spend() -> Dict[str, Any]:
    """This month's estimated spend and the monthly budget."""
    return _get("/spend")


def count_tokens(text: str, *, model: Optional[str] = None, system: Optional[str] = None) -> int:
    """FREE: count the input tokens of `text` sent as one user message."""
    body = {"messages": [{"role": "user", "content": text}], "model": model, "system": system}
    return _post("/count_tokens", body, timeout=30)["input_tokens"]
