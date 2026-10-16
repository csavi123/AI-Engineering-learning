"""FastAPI backend: the only place that talks to the Anthropic API.

Why a separate backend? Streamlit runs code that a browser can influence. If
the API key lived there, a bug could leak it. Here, the key stays in this
process and the frontend only ever sees results.

Run with:  uvicorn backend.main:app --reload --port 8000
"""
import itertools
import json
import os
import secrets
from typing import Any, Dict, List, Optional

import anthropic
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.claude_client import (
    UnsupportedFeatureError, call_claude, count_tokens, stream_claude,
)
from backend import spend
from backend.config import api_key_present, load_config

# Shared secret between the Streamlit app and this backend. When it is set
# (in production), only callers that send it can use the endpoints below, so
# someone who finds this URL can't spend your API credit directly.
# Left unset (local development), the backend stays open as before.
BACKEND_TOKEN = os.environ.get("BACKEND_TOKEN", "")

# With a token set we're in production: hide the auto-generated /docs page,
# which would otherwise list every endpoint and let anyone try them.
_docs_off = {"docs_url": None, "redoc_url": None, "openapi_url": None} if BACKEND_TOKEN else {}
app = FastAPI(title="LLM Learning Lab backend", **_docs_off)


def _require_token(x_backend_token: str = Header(default="")) -> None:
    """Reject requests without the shared secret (when one is configured)."""
    # compare_digest takes the same time whether the guess is close or not,
    # so the token can't be worked out by timing many wrong guesses.
    if BACKEND_TOKEN and not secrets.compare_digest(x_backend_token, BACKEND_TOKEN):
        raise HTTPException(status_code=401, detail="Missing or wrong backend token.")


# /health stays open on purpose: the keep-alive pinger calls it without a
# token, and it only reveals "up" plus a true/false, never the key.
PROTECTED = [Depends(_require_token)]


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class CallRequest(BaseModel):
    """Body of POST /call. Mirrors call_claude's arguments."""

    messages: List[Message]
    model: Optional[str] = None
    system: Optional[str] = None
    # Upper bound protects your budget if a page sends something silly.
    max_tokens: int = Field(default=1024, ge=1, le=8192)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    top_p: Optional[float] = Field(default=None, gt=0.0, le=1.0)
    top_k: Optional[int] = Field(default=None, ge=1)


@app.get("/health")
def health() -> Dict[str, Any]:
    """Lets the frontend check the backend is up and a key is configured."""
    return {"status": "ok", "api_key_configured": api_key_present()}


@app.get("/config", dependencies=PROTECTED)
def get_config() -> Dict[str, Any]:
    """Share model names and prices with the frontend (never the key)."""
    return load_config()


def _to_http_error(e: Exception) -> HTTPException:
    """Turn each kind of failure into a readable message for the UI.

    Specific errors are checked first so the message says *what* went wrong.
    """
    if isinstance(e, spend.BudgetExceededError):
        return HTTPException(status_code=402, detail=str(e))
    if isinstance(e, (UnsupportedFeatureError, KeyError)):
        return HTTPException(status_code=400, detail=str(e).strip("'\""))
    if isinstance(e, anthropic.AuthenticationError):
        return HTTPException(
            status_code=401,
            detail="Anthropic rejected the API key. Check ANTHROPIC_API_KEY in .env.",
        )
    if isinstance(e, anthropic.RateLimitError):
        return HTTPException(
            status_code=429, detail="Rate limited by Anthropic. Wait a bit and retry."
        )
    if isinstance(e, anthropic.BadRequestError):
        # e.g. a setting the API rejects that our checks didn't anticipate.
        return HTTPException(status_code=400, detail=f"Anthropic API said: {e.message}")
    if isinstance(e, anthropic.APIConnectionError):
        return HTTPException(status_code=502, detail="Could not reach the Anthropic API.")
    if isinstance(e, anthropic.APIStatusError):
        return HTTPException(status_code=502, detail=f"Anthropic API error: {e.message}")
    raise e  # a genuine bug in our code: let it show up in the server log


EXPECTED_ERRORS = (
    spend.BudgetExceededError, UnsupportedFeatureError, KeyError, anthropic.APIError,
)


@app.get("/spend", dependencies=PROTECTED)
def get_spend() -> Dict[str, Any]:
    """This month's estimated spend and the budget, for the sidebar."""
    return {"month_total_usd": spend.month_total(), "budget_usd": spend.budget()}


@app.post("/call", dependencies=PROTECTED)
def call(req: CallRequest) -> Dict[str, Any]:
    """Generic single call to Claude via the shared helper."""
    try:
        result = call_claude(
            [m.model_dump() for m in req.messages],
            model=req.model,
            system=req.system,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
            top_p=req.top_p,
            top_k=req.top_k,
        )
    except EXPECTED_ERRORS as e:
        raise _to_http_error(e)
    return result.to_dict()


class CountRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = None
    system: Optional[str] = None


@app.post("/count_tokens", dependencies=PROTECTED)
def count(req: CountRequest) -> Dict[str, Any]:
    """Free: how many input tokens this request would use. Nothing is generated."""
    try:
        n = count_tokens([m.model_dump() for m in req.messages], model=req.model, system=req.system)
    except EXPECTED_ERRORS as e:
        raise _to_http_error(e)
    return {"input_tokens": n, "model": req.model or load_config()["default_model"]}


@app.post("/stream", dependencies=PROTECTED)
def stream(req: CallRequest) -> StreamingResponse:
    """Stream the reply as it is generated, one JSON object per line.

    Sampling settings are ignored here; streaming is about *how* the reply
    arrives, not which reply you get.
    """
    events = stream_claude(
        [m.model_dump() for m in req.messages],
        model=req.model,
        system=req.system,
        max_tokens=req.max_tokens,
    )
    # Pull the first event now, so setup errors (bad key, unsupported model)
    # become a normal error response instead of a half-sent stream.
    try:
        first = next(events)
    except EXPECTED_ERRORS as e:
        raise _to_http_error(e)

    def lines():
        try:
            for event in itertools.chain([first], events):
                yield json.dumps(event) + "\n"
        except EXPECTED_ERRORS as e:
            yield json.dumps({"type": "error", "detail": _to_http_error(e).detail}) + "\n"

    return StreamingResponse(lines(), media_type="application/x-ndjson")
