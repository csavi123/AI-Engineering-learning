"""Free demos: local simulations that make no API calls.

The numbers here are made up for illustration. Claude's API doesn't expose
real probabilities, so a simulation is the only way to *show* the mechanism
step by step without paying for calls.
"""
from typing import Any, Dict

import plotly.graph_objects as go
import streamlit as st

import charts
from demos.ch01.common import token_chips

# A scripted generation of "Once upon a time, there lived a curious fox."
# Each step: the candidates the model might rank highest, with toy
# probabilities, and the token that was picked. Step 6 deliberately picks a
# token that is NOT the top one, to show the chooser can pick any candidate.
LOOP_STEPS = [
    {"pick": " time", "cands": {" time": 0.93, " day": 0.03, " midnight": 0.02, " star": 0.01}},
    {"pick": ",", "cands": {",": 0.71, " there": 0.18, " in": 0.07, " a": 0.02}},
    {"pick": " there", "cands": {" there": 0.55, " a": 0.20, " in": 0.15, " the": 0.06}},
    {"pick": " lived", "cands": {" lived": 0.48, " was": 0.44, " were": 0.05, " stood": 0.02}},
    {"pick": " a", "cands": {" a": 0.82, " an": 0.12, " two": 0.04, " the": 0.01}},
    {"pick": " curious", "cands": {" young": 0.21, " little": 0.18, " curious": 0.09, " king": 0.07}},
    {"pick": " fox", "cands": {" fox": 0.22, " girl": 0.20, " cat": 0.15, " boy": 0.12}},
    {"pick": ".", "cands": {".": 0.40, " who": 0.35, " named": 0.15, " that": 0.06}},
    {"pick": "⏹ STOP", "cands": {"⏹ STOP": 0.62, " The": 0.20, " She": 0.08, " Every": 0.05}},
]
LOOP_START = "Once upon a"


def loop_stepper(cfg: Dict[str, Any]) -> None:
    st.caption("🆓 Free simulation: no API calls. Probabilities are illustrative, not Claude's real numbers.")
    key = "sim_loop_step"
    step = st.session_state.get(key, 0)

    c1, c2, c3 = st.columns([1, 1, 4])
    if c1.button("▶ Next step", key=f"{key}_next", disabled=step >= len(LOOP_STEPS)):
        step += 1
    if c2.button("↺ Reset", key=f"{key}_reset"):
        step = 0
    step = min(step, len(LOOP_STEPS))  # never step past the end of the script
    st.session_state[key] = step
    c3.markdown(f"**Forward passes run: {step} / {len(LOOP_STEPS)}**")

    picked = [s["pick"] for s in LOOP_STEPS[:step] if s["pick"] != "⏹ STOP"]
    st.markdown("**Sequence so far** (each chip = one token; the first chip is the prompt):")
    token_chips([LOOP_START] + picked)

    if step == 0:
        st.info("Click **Next step** to run one forward pass.")
        return

    current = LOOP_STEPS[step - 1]
    labels = list(current["cands"].keys())[::-1]  # plotly draws bottom-up
    probs = [current["cands"][t] for t in labels]
    colors = [charts.SERIES[1] if t == current["pick"] else charts.SERIES[0] for t in labels]
    fig = go.Figure(go.Bar(
        x=probs, y=[t.replace(" ", "·") for t in labels], orientation="h", marker_color=colors,
        text=[f"{p:.0%}" for p in probs], textposition="outside",
        hovertemplate="%{y}: %{x:.0%}<extra></extra>",
    ))
    fig.update_layout(title=f"Forward pass {step}: top candidates (orange = picked)",
                      height=260, margin=dict(l=10, r=40, t=50, b=10), showlegend=False)
    fig.update_xaxes(tickformat=".0%", range=[0, 1.1])
    st.plotly_chart(fig)

    if current["pick"] == "⏹ STOP":
        st.success("The stop token was picked, so the loop ends. That's the whole answer.")
    elif current["pick"] != max(current["cands"], key=current["cands"].get):
        st.warning("The picked token was **not** the most likely one. The chooser samples, "
                   "so lower-probability tokens sometimes win. That's lesson 04.")
    else:
        st.caption(f"`{current['pick'].replace(' ', '·')}` is appended, and the longer "
                   "sequence becomes the input to the next forward pass.")
