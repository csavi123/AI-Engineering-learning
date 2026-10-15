"""Lesson 03 demos: what fills the context window, and how chats grow."""
from typing import Any, Dict

import plotly.graph_objects as go
import streamlit as st

import api
import charts
from demos.ch01.tokens import text_tokens

PARTS = {
    "System prompt": "You are a friendly cooking assistant. Keep answers short and practical.",
    "Few-shot examples": (
        "Example question: What can I make with eggs and spinach?\n"
        "Example answer: A spinach omelette. Whisk 2 eggs, wilt the spinach, fold together."
    ),
    "Document": (
        "Pantry list: rice, lentils, onions, garlic, tinned tomatoes, cumin, chilli flakes, "
        "olive oil, pasta, parmesan, frozen peas, eggs, spinach, lemons."
    ),
    "Chat history": (
        "User: I'm vegetarian and allergic to peanuts.\n"
        "Assistant: Noted, no meat and no peanuts.\n"
        "User: I have about 30 minutes tonight."
    ),
    "Current prompt": "What should I cook for dinner?",
}


def context_budget(cfg: Dict[str, Any]) -> None:
    st.caption("🆓 Free: counts tokens with Anthropic's counting endpoint. Nothing is generated or billed.")
    model = cfg["default_model"]
    st.write("Everything below is sent on **every** call. Edit any part, then count.")
    texts = {name: st.text_area(name, default, key=f"ctx_{name}", height=70)
             for name, default in PARTS.items()}
    c1, c2 = st.columns(2)
    limit = c1.number_input("Context limit to compare against (tokens)", 100, 2_000_000, 600, step=100,
                            key="ctx_limit",
                            help=f"Small on purpose so the bar is visible. The real limit for {model} "
                                 f"is {cfg['models'][model]['context_window']:,}.")
    reply = c2.number_input("Room reserved for the reply (max_tokens)", 0, 100_000, 200, step=50,
                            key="ctx_reply")

    if st.button("🔢 Count each part (free)", key="ctx_count", type="primary"):
        try:
            st.session_state["ctx_counts"] = {n: text_tokens(t, model) if t.strip() else 0
                                              for n, t in texts.items()}
        except api.BackendError as e:
            st.error(str(e))

    counts = st.session_state.get("ctx_counts")
    if not counts:
        return
    fig = go.Figure()
    for i, (name, n) in enumerate(counts.items()):
        fig.add_bar(name=name, x=[n], y=["Context window"], orientation="h",
                    marker=dict(color=charts.SERIES[i % len(charts.SERIES)], line=dict(width=2, color="white")),
                    hovertemplate=f"{name}: {n} tokens<extra></extra>")
    fig.add_bar(name="Reserved for reply", x=[reply], y=["Context window"], orientation="h",
                marker=dict(color="rgba(138,137,133,0.35)", pattern_shape="/"),
                hovertemplate=f"Reply room: {reply} tokens<extra></extra>")
    fig.add_vline(x=limit, line_width=2, line_dash="dash", line_color="#e34948",
                  annotation_text=f"limit {limit:,}", annotation_position="top")
    fig.update_layout(barmode="stack", height=220, margin=dict(l=10, r=10, t=40, b=10),
                      legend=dict(orientation="h", y=-0.4))
    fig.update_xaxes(title="tokens")
    st.plotly_chart(fig)

    used = sum(counts.values()) + reply
    if used > limit:
        st.error(f"**{used:,} tokens > limit {limit:,}.** Something must be cut, or the request fails. "
                 "Lesson 07 covers what to cut.")
    else:
        st.success(f"**{used:,} of {limit:,} tokens used.** {limit - used:,} to spare.")
    m = cfg["models"][model]
    st.caption(f"Input cost per call: ${sum(counts.values()) * m['input_price_per_mtok'] / 1e6:.7f}, "
               "paid again on every turn because the whole context is resent.")


def history_growth(cfg: Dict[str, Any]) -> None:
    st.caption("🆓 Free simulation: plain arithmetic, no API calls.")
    model = cfg["default_model"]
    m = cfg["models"][model]
    c1, c2, c3, c4 = st.columns(4)
    turns = c1.slider("Turns", 1, 50, 20, key="grow_turns")
    system = c2.number_input("System prompt tokens", 0, 20_000, 300, key="grow_sys")
    user = c3.number_input("Tokens per message", 1, 5_000, 60, key="grow_user")
    reply = c4.number_input("Tokens per reply", 1, 5_000, 200, key="grow_reply")

    # Turn t sends: system + all earlier (message + reply) pairs + this message.
    inputs = [system + (t - 1) * (user + reply) + user for t in range(1, turns + 1)]
    costs = [(i * m["input_price_per_mtok"] + reply * m["output_price_per_mtok"]) / 1e6 for i in inputs]
    fig = go.Figure(go.Bar(x=list(range(1, turns + 1)), y=inputs, marker_color=charts.SERIES[0],
                           hovertemplate="Turn %{x}: %{y:,} input tokens<extra></extra>"))
    fig.update_layout(title="Input tokens sent on each turn (history is resent every time)",
                      height=300, margin=dict(l=10, r=10, t=50, b=10))
    fig.update_xaxes(title="turn")
    fig.update_yaxes(title="input tokens")
    st.plotly_chart(fig)
    st.markdown(f"Turn {turns} sends **{inputs[-1]:,}** input tokens vs **{inputs[0]:,}** on turn 1. "
                f"Whole chat ≈ **${sum(costs):.5f}** on {model}.")
