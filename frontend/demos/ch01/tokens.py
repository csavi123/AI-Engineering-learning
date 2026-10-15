"""Lesson 02 demo: count real Claude tokens for free.

Uses Anthropic's token counting endpoint, which is free (only rate-limited):
nothing is generated, so nothing is billed.
"""
from typing import Any, Dict

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import api
import charts

PRESETS = {
    "Plain English": "The quick brown fox jumps over the lazy dog near the river bank.",
    "Long medical term": "The patient was diagnosed with pneumonoultramicroscopicsilicovolcanoconiosis.",
    "Python code": "def add(a, b):\n    return a + b  # sum two numbers",
    "Phone number": "Call me at +1 (415) 555-0198 or 415.555.0199.",
    "Non-English (Hindi)": "मुझे एक कप गरम चाय चाहिए।",
    "Emojis": "I love pizza 🍕🍕 and rockets 🚀✨🎉",
}


def _overhead(model: str) -> int:
    """Tokens the message wrapper adds, measured once with a 1-character text.

    Every count includes a few tokens of formatting ("this is a user
    message"). Subtracting them leaves (approximately) the text's own tokens.
    """
    key = f"tok_overhead_{model}"
    if key not in st.session_state:
        st.session_state[key] = max(api.count_tokens("x", model=model) - 1, 0)
    return st.session_state[key]


def text_tokens(text: str, model: str) -> int:
    return max(api.count_tokens(text, model=model) - _overhead(model), 1)


def token_counter(cfg: Dict[str, Any]) -> None:
    st.caption("🆓 Free: uses Anthropic's token *counting* endpoint. Nothing is generated or billed.")
    new_model, old_model = cfg["default_model"], cfg["sampling_model"]

    preset = st.radio("Try a preset", list(PRESETS), horizontal=True, key="tok_preset")
    # The key includes the preset, so picking a preset loads its text.
    text = st.text_area("Text", PRESETS[preset], key=f"tok_text_{preset}", height=90)

    if st.button("🔢 Count tokens (free)", key="tok_count", type="primary"):
        try:
            words = len(text.split())
            st.session_state["tok_result"] = {
                "text": text,
                "chars": len(text),
                "words": words,
                "new": text_tokens(text, new_model),
                "old": text_tokens(text, old_model),
                # Every preset on the default model, for the comparison chart.
                "presets": {name: (text_tokens(t, new_model), len(t.split())) for name, t in PRESETS.items()},
            }
        except api.BackendError as e:
            st.error(str(e))

    r = st.session_state.get("tok_result")
    if not r:
        return
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Characters", r["chars"])
    c2.metric("Words", r["words"])
    c3.metric(f"Tokens ({new_model})", r["new"])
    c4.metric("Tokens per word", f"{r['new'] / max(r['words'], 1):.2f}")
    st.caption(
        f"Same text on the older tokenizer ({old_model}): **{r['old']}** tokens. Newer Claude "
        "models split text into more pieces; Anthropic says ~30% more on average."
    )

    names = list(r["presets"])
    ratios = [r["presets"][n][0] / max(r["presets"][n][1], 1) for n in names]
    fig = go.Figure(go.Bar(
        x=ratios, y=names, orientation="h", marker_color=charts.SERIES[0],
        text=[f"{x:.1f}" for x in ratios], textposition="outside",
        customdata=[r["presets"][n][0] for n in names],
        hovertemplate="%{y}: %{x:.2f} tokens per word (%{customdata} tokens)<extra></extra>",
    ))
    fig.update_layout(title="Tokens per word, by kind of text", height=320,
                      margin=dict(l=10, r=40, t=50, b=10))
    st.plotly_chart(fig)

    # Cost calculator, from the prices in config.yaml.
    st.markdown("**💲 What would this text cost as input?**")
    per_day = st.number_input("Requests per day", 1, 1_000_000, 10_000, step=1000, key="tok_per_day")
    rows = []
    for name, tokens in ((new_model, r["new"]), (old_model, r["old"])):
        m = cfg["models"][name]
        one = tokens * m["input_price_per_mtok"] / 1_000_000
        rows.append({"model": name, "tokens": tokens, "one request $": f"{one:.7f}",
                     f"{per_day:,}/day for 30 days $": f"{one * per_day * 30:,.2f}"})
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.caption("Token counts are Anthropic's estimates, minus a few tokens of message wrapper.")
