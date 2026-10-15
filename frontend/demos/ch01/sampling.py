"""Lesson 04 demos: a free sampling simulator, and live one-token sampling."""
import random
from collections import Counter
from typing import Any, Dict

import plotly.graph_objects as go
import streamlit as st

import api
import charts
import ui
from demos.ch01 import sampling_math
from demos.ch01.common import completion_request, spent


def one_token_sampling(cfg: Dict[str, Any]) -> None:
    KEY = "l01_dist"
    model = cfg["sampling_model"]
    cap = cfg["max_repeated_runs"]

    st.markdown("### 🧪 Experiment 1 · Peek at the distribution")
    st.write(
        "We can't read the probabilities directly, so we do the next best thing: "
        "ask for **one** next token many times at temperature 1 and count the "
        "answers. It's like flipping a coin 30 times to learn how it's weighted."
    )

    ui.prediction_box(
        KEY,
        "How many different next tokens will show up, and how often will the most "
        "common one win?",
    )
    text = st.text_input("Text start", "My favorite food is", key=f"{KEY}_text")
    # min(...) keeps the default valid if you lower the cap in config.yaml.
    n = st.slider("Samples", 5, cap, min(30, cap), key=f"{KEY}_n")

    ok = ui.estimated_calls_notice(n, cap, ui.estimate_cost(cfg, model, n, 60, 1))
    st.caption(f"Model: `{model}` (needs prefill and temperature)")

    if ui.run_button(KEY) and ok:
        req = completion_request(text, model=model, max_tokens=1, temperature=1.0)
        st.session_state[f"{KEY}_out"] = {
            "text": text,
            "request": req,
            "results": ui.run_repeated(lambda: api.call(**req), n, "Sampling"),
        }

    # A fresh run is parked in session_state; save it to disk, then always
    # read from disk so the last run stays visible (for free) next time.
    if f"{KEY}_out" in st.session_state:
        ui.save_run(KEY, st.session_state.pop(f"{KEY}_out"))
    out = ui.load_run(KEY)
    if out and out["results"]:
        counts = Counter(
            ui.show_token(r["text"]) if r["text"] else "⏹ stop" for r in out["results"]
        )
        st.plotly_chart(charts.frequency_bars(counts, f'"{out["text"]} ___"'))
        top, top_n = counts.most_common(1)[0]
        st.markdown(
            f"**{len(counts)}** different tokens in {len(out['results'])} samples · "
            f"top token `{top}` won **{top_n / len(out['results']):.0%}** of the time"
        )
        st.caption("`·` marks a space. Tokens usually *start* with their space, like `·pizza`.")
        ui.show_exchange(out["request"], out["results"][0])
        spent(out["results"])
        ui.show_prediction_reminder(KEY)

    ui.what_this_shows(
        KEY,
        "Each call returned **one** token picked from the model's probability "
        "distribution over every possible next token. Counting many picks lets you "
        "**see the shape of that distribution**: the taller a bar, the more "
        "probability the model put on that token.\n\n"
        "**One tall bar** (like 100% `·pizza`) means the model put almost all its "
        "probability on one token. Chat models like Claude get extra training to give "
        "the single most typical answer, which makes their distributions very "
        "*peaked*, even for opinion questions. If pizza has ~98%, then 16 picks in a "
        "row are all pizza about 7 times out of 10, even with randomness on.\n\n"
        "**Several bars** means the probability was spread out, so the same input "
        "gave different outputs.\n\n"
        "Either way, the model returned a *distribution*, not an answer; something "
        "outside the model picked one token from it. These are estimates from a "
        "limited number of samples, not the true probabilities.",
    )


# Toy scores (logits) for the next token after "My favorite food is".
# Made-up numbers, chosen so the shape looks like a real chat model's:
# one strong favourite and a long tail.
TOY_LOGITS = {
    "·pizza": 4.0, "·pasta": 2.6, "·sushi": 2.4, "·tacos": 2.0,
    "·curry": 1.8, "·burgers": 1.6, "·salad": 1.0, "·ice cream": 0.8,
}


def sampling_simulator(cfg: Dict[str, Any]) -> None:
    st.caption("🆓 Free simulation: no API calls. Toy numbers for \"My favorite food is ___\".")
    c1, c2, c3 = st.columns(3)
    temp = c1.slider("Temperature", 0.0, 2.0, 1.0, 0.1, key="sim_temp",
                     help="0 = always the top token. Higher = flatter, more varied.")
    k = c2.slider("top-k", 1, len(TOY_LOGITS), len(TOY_LOGITS), key="sim_topk",
                  help="Keep only the k most likely tokens. Max = off.")
    p = c3.slider("top-p", 0.05, 1.0, 1.0, 0.05, key="sim_topp",
                  help="Keep the smallest set of top tokens whose probabilities add up to p. 1.0 = off.")

    before = sampling_math.with_temperature(TOY_LOGITS, 1.0)
    after = sampling_math.top_p(sampling_math.top_k(sampling_math.with_temperature(TOY_LOGITS, temp), k), p)

    tokens = list(TOY_LOGITS)
    fig = go.Figure()
    fig.add_bar(name="Model's distribution (temperature 1)", x=tokens, y=[before[t] for t in tokens],
                marker_color=charts.MUTED, hovertemplate="%{x}: %{y:.1%}<extra></extra>")
    fig.add_bar(name="After your settings", x=tokens, y=[after[t] for t in tokens],
                marker_color=charts.SERIES[1], hovertemplate="%{x}: %{y:.1%}<extra></extra>")
    fig.update_layout(barmode="group", height=340, margin=dict(l=10, r=10, t=30, b=10),
                      legend=dict(orientation="h", y=1.12))
    fig.update_yaxes(tickformat=".0%", range=[0, 1.05])
    st.plotly_chart(fig)

    kept = sum(1 for t in tokens if after[t] > 0)
    st.markdown(f"Tokens that can still be picked: **{kept} of {len(tokens)}** · "
                f"top token chance: **{max(after.values()):.0%}**")

    if st.button("🎲 Draw 30 samples (free)", key="sim_draw"):
        st.session_state["sim_samples"] = sampling_math.sample(after, 30, random.Random())
    samples = st.session_state.get("sim_samples")
    if samples:
        counts = Counter(samples)
        st.markdown(f"30 samples gave **{len(counts)}** different tokens: " +
                    ", ".join(f"`{t}` ×{n}" for t, n in counts.most_common()))
        st.caption("Change a slider and draw again to compare.")
