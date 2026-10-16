"""Tiny client the Streamlit pages use to talk to the FastAPI backend.

Why go through HTTP instead of importing the backend directly? It keeps a hard
wall between the UI and the API key: this process never loads .env's key.
"""
import json
import os
import time
from typing import Any, Dict, Iterator, List, Optional

import requests

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

# Shared secret the backend checks (set in Streamlit secrets in production).
# This runs on the Streamlit server, so visitors' browsers never see it.
_TOKEN = os.environ.get("BACKEND_TOKEN", "")
HEADERS = {"X-Backend-Token": _TOKEN} if _TOKEN else {}

# Free hosting (Render) puts the backend to sleep when nobody has used it for a
# while. While it wakes up, the host answers with its OWN HTML error page
# (502/503/504) instead of our JSON, so we must never show that page as is.
WAKING_STATUSES = (502, 503, 504)
WAKING_MESSAGE = (
    "The backend is waking up (free hosting sleeps when nobody has used it for a "
    "while). Give it about a minute, then refresh the page."
)


class BackendError(Exception):
    """Raised with a human-readable message when the backend call fails."""


def _handle(resp: requests.Response) -> Dict[str, Any]:
    if resp.ok:
        return resp.json()
    # FastAPI puts our friendly error text in "detail".
    try:
        detail = resp.json().get("detail", resp.text)
    except ValueError:
        # Not JSON, so it came from the host, not our backend (e.g. an HTML
        # "502" page). Replace it with a short message instead of dumping it.
        if resp.status_code in WAKING_STATUSES:
            detail = WAKING_MESSAGE
        else:
            detail = f"The backend returned an unexpected error (HTTP {resp.status_code})."
    raise BackendError(str(detail))


def _get(path: str) -> Dict[str, Any]:
    try:
        return _handle(requests.get(f"{BACKEND_URL}{path}", headers=HEADERS, timeout=10))
    except requests.ConnectionError:
        raise BackendError(
            f"Can't reach the backend at {BACKEND_URL}. Is uvicorn running?"
        )
    except requests.Timeout:
        # A sleeping backend can take longer than 10s to answer.
        raise BackendError(WAKING_MESSAGE)


def wait_for_backend(max_wait_s: float = 90) -> bool:
    """Ping /health until the backend answers, for up to max_wait_s seconds.

    Free: /health never calls Anthropic. Run once per visit so a sleeping
    backend shows a "waking up" spinner instead of an error. Only the free GET
    is retried, never a paid call, so a retry can't charge you twice.
    Returns True once the backend is up.
    """
    deadline = time.monotonic() + max_wait_s
    while True:
        try:
            health()
            return True
        except BackendError:
            if time.monotonic() >= deadline:
                return False
            time.sleep(3)


def _post(path: str, body: Dict[str, Any], timeout: float = 120) -> Dict[str, Any]:
    try:
        return _handle(requests.post(f"{BACKEND_URL}{path}", json=body, headers=HEADERS, timeout=timeout))
    except requests.ConnectionError:
        raise BackendError(
            f"Can't reach the backend at {BACKEND_URL}. Is uvicorn running?"
        )
    except requests.Timeout:
        raise BackendError("The backend took too long to answer. Please try again.")


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
        with requests.post(f"{BACKEND_URL}/stream", json=body, headers=HEADERS, stream=True, timeout=120) as resp:
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
