"""Live demo: does option order change the answer? (lesson 06)."""

from collections import Counter
from typing import Any, Dict

import streamlit as st

import api
import charts
import ui
from demos.ch01.common import spent


def option_order(cfg: Dict[str, Any]) -> None:
    KEY = "l01_order"
    model = cfg["default_model"]
    cap = cfg["max_repeated_runs"]

    st.markdown("### 🧪 Experiment 9 · Swap the order, change the answer?")
    st.write(
        "Logically, *\"cat or dog\"* and *\"dog or cat\"* are the same question. "
        "But the model is conditioned on the exact token sequence, and the order "
        "is part of it."
    )
    ui.prediction_box(KEY, "Will the order of the options change which one Claude picks, and how often?")
    c1, c2 = st.columns(2)
    q_a = c1.text_input("Version A", "Pick one: cat or dog. Answer with one word only.", key=f"{KEY}_a")
    q_b = c2.text_input("Version B", "Pick one: dog or cat. Answer with one word only.", key=f"{KEY}_b")
    n = st.slider("Runs per version", 3, min(25, cap), 10, key=f"{KEY}_n")
    ok = ui.estimated_calls_notice(2 * n, 2 * cap, ui.estimate_cost(cfg, model, 2 * n, 25, 3))
    st.caption(f"Model: `{model}` (default settings)")

    if ui.run_button(KEY) and ok:
        out = {}
        for label, q in (("A", q_a), ("B", q_b)):
            msgs = [{"role": "user", "content": q}]
            out[label] = {"q": q, "results": ui.run_repeated(
                lambda: api.call(msgs, model=model, max_tokens=5), n, f"Version {label}")}
        st.session_state[f"{KEY}_out"] = out

    # A fresh run is parked in session_state; save it to disk, then always
    # read from disk so the last run stays visible (for free) next time.
    if f"{KEY}_out" in st.session_state:
        ui.save_run(KEY, st.session_state.pop(f"{KEY}_out"))
    out = ui.load_run(KEY)
    if out:
        groups = {
            f"{label}: “{d['q'].split('.')[0]}”": Counter(
                r["text"].strip().strip(".!").lower() or "(empty)" for r in d["results"])
            for label, d in out.items()
        }
        st.plotly_chart(charts.grouped_bars(groups, "Answers by question wording", "answer"))
        spent([r for d in out.values() for r in d["results"]])
        ui.show_prediction_reminder(KEY)

    ui.what_this_shows(
        KEY,
        "If the bars differ between A and B, a change that means nothing to a "
        "human (the order of two options) changed the output. That's because the "
        "distribution is computed from the exact sequence of tokens; there is no "
        "step that first converts your input into a canonical meaning.\n\n"
        "If they look the same this time, the effect is still there in the "
        "numbers, just not big enough to flip this pick. Try a closer call (e.g. "
        "*tea or coffee*, *Python or JavaScript*) or more runs. A single run "
        "can't tell you about the distribution, which is why real evaluations "
        "repeat a prompt many times.",
    )
