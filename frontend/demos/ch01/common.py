"""Small pieces shared by the lesson-01 sections."""
import html
from typing import Any, Dict, List

import streamlit as st

# A "raw completion" setup. Chat models normally answer a question; here we
# want them to just continue a piece of text, which is the closest the API
# lets us get to watching the bare next-token function.
COMPLETION_SYSTEM = (
    "You are a raw text-completion engine. Continue the text in the assistant "
    "turn exactly where it stops. Do not repeat it and do not add commentary."
)


def completion_request(text: str, **settings: Any) -> Dict[str, Any]:
    """Build a request whose assistant turn is pre-filled with `text`.

    The model must continue from the last character of `text`. This needs a
    model that supports prefill (the sampling model in config.yaml).
    """
    return {
        "system": COMPLETION_SYSTEM,
        "messages": [
            {"role": "user", "content": "Continue this text."},
            {"role": "assistant", "content": text},
        ],
        **settings,
    }


def token_chips(tokens: List[str]) -> None:
    """Render tokens as alternating colored chips, so you can see the boundaries.

    Spaces are shown as · because a token's leading space is part of it.
    """
    colors = ["rgba(42,120,214,0.18)", "rgba(235,104,52,0.18)"]
    chips = "".join(
        f'<span style="background:{colors[i % 2]};border-radius:4px;padding:2px 3px;'
        f'margin:1px;display:inline-block;font-family:monospace">'
        f"{html.escape(t.replace(' ', '·')).replace(chr(10), '↵')}</span>"
        for i, t in enumerate(tokens)
    )
    st.markdown(f'<div style="line-height:2">{chips}</div>', unsafe_allow_html=True)


def spent(results: List[Dict[str, Any]]) -> None:
    total = sum(r["estimated_cost_usd"] for r in results)
    st.caption(f"💰 {len(results)} call(s), estimated cost ${total:.6f}")

