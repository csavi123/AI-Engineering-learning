"""Lesson 06 demos: a toy picture of attention, and behavioural evidence from Claude.

The Claude API exposes no attention weights, embeddings or probabilities. So
the free demo is a labelled toy, and the live demo is indirect evidence:
we can only watch what the model *does*, not look inside it.
"""
from typing import Any, Dict

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import api
import charts
import ui
from demos.ch01.common import spent

SENTENCE = ["The", "trophy", "didn't", "fit", "in", "the", "suitcase", "because", "it", "was", "too"]
# Toy attention from the token "it" to each earlier token. Illustrative only:
# real models have many attention heads and layers, each with its own pattern.
TOY_ATTENTION = {
    "big":   [0.02, 0.58, 0.04, 0.06, 0.01, 0.02, 0.17, 0.06, 0.0, 0.02, 0.02],
    "small": [0.02, 0.14, 0.04, 0.06, 0.01, 0.03, 0.62, 0.04, 0.0, 0.02, 0.02],
}


def attention_toy(cfg: Dict[str, Any]) -> None:
    st.caption("🆓 Free illustration with made-up weights. Claude's real attention can't be seen through the API.")
    ending = st.radio("Sentence ends with…", ["big", "small"], horizontal=True, key="att_end",
                      format_func=lambda e: f"…because it was too {e}")
    weights = TOY_ATTENTION[ending]
    target = "trophy" if ending == "big" else "suitcase"
    colors = [charts.SERIES[1] if w == max(weights) else charts.SERIES[0] for w in weights]
    fig = go.Figure(go.Bar(
        x=[f"{i}·{t}" for i, t in enumerate(SENTENCE)], y=weights, marker_color=colors,
        hovertemplate="%{x}: %{y:.0%} of 'it''s attention<extra></extra>",
    ))
    fig.update_layout(title=f"Where \"it\" looks when the sentence ends \"too {ending}\" (toy numbers)",
                      height=300, margin=dict(l=10, r=10, t=50, b=10))
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig)
    st.markdown(
        f"Changing **one word at the end** changes what **\"it\"** should refer to (**{target}**). "
        "Attention is the mechanism that lets each token pull in information from the "
        "tokens that matter for it, however far back they are."
    )

    st.markdown("**And why position matters:**")
    c1, c2 = st.columns(2)
    for col, s in zip((c1, c2), ("dog bites man", "man bites dog")):
        col.markdown(f"`{s}` → tokens {sorted(s.split())}")
    st.caption("Same set of tokens, opposite meaning. Attention alone ignores order, so "
               "transformers add position information to every token.")


TESTS = [
    ("The trophy didn't fit in the suitcase because it was too big. What was too big?", "trophy"),
    ("The trophy didn't fit in the suitcase because it was too small. What was too small?", "suitcase"),
    ("The dog bit the man. Who is hurt?", "man"),
    ("The man bit the dog. Who is hurt?", "dog"),
]


def trophy_suitcase(cfg: Dict[str, Any]) -> None:
    KEY = "l06_trophy"
    model = cfg["default_model"]
    st.write("Four tiny questions where one word, or word **order**, flips the right answer.")
    ui.prediction_box(KEY, "Will Claude get all four right? Which one is most likely to trip it?")
    ui.estimated_calls_notice(len(TESTS), cfg["max_repeated_runs"],
                              ui.estimate_cost(cfg, model, len(TESTS), 40, 3))
    st.caption(f"Model: `{model}`")

    if ui.run_button(KEY):
        try:
            rows = []
            results = []
            for question, expected in TESTS:
                r = api.call([{"role": "user", "content": question + " Answer with one word."}],
                             model=model, max_tokens=5)
                results.append(r)
                answer = r["text"].strip().strip(".!").lower()
                rows.append({"question": question, "expected": expected, "Claude": answer,
                             "": "✅" if expected in answer else "❌"})
            st.session_state[f"{KEY}_out"] = {"rows": rows, "results": results}
        except api.BackendError as e:
            st.error(str(e))

    if f"{KEY}_out" in st.session_state:
        ui.save_run(KEY, st.session_state.pop(f"{KEY}_out"))
    out = ui.load_run(KEY)
    if out:
        st.dataframe(pd.DataFrame(out["rows"]), hide_index=True, width="stretch")
        spent(out["results"])
        ui.show_prediction_reminder(KEY)

    ui.what_this_shows(
        KEY,
        "Getting these right needs two things from inside the transformer: **attention** "
        "(linking \"it\" to the right noun, using a word at the far end of the sentence) "
        "and **position** (\"dog bit man\" and \"man bit dog\" contain the same tokens). "
        "This is behavioural evidence only: we see the output, not the attention weights.",
    )
