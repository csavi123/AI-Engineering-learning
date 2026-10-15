"""Live demos about the generation loop (lesson 01)."""

import time
from typing import Any, Dict, List

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import api
import charts
import ui
from demos.ch01.common import completion_request, spent, token_chips


def token_by_token(cfg: Dict[str, Any]) -> None:
    KEY = "l01_tbt"
    model = cfg["sampling_model"]

    st.markdown("### 🧪 Experiment 2 · Run the loop by hand, one token at a time")
    st.write(
        "Each step is a separate API call with `max_tokens=1`. The text so far is "
        "sent as the start of Claude's answer (a *prefill*), so the model can only "
        "add one token to it. **We** are the loop; the model is just the function."
    )
    ui.prediction_box(KEY, "What will the next 12 tokens be? Will the model stop by itself?")
    start = st.text_input("Starting text", "The capital of France is", key=f"{KEY}_start")
    steps = st.slider("Steps", 1, cfg["max_repeated_runs"], 12, key=f"{KEY}_steps")
    ok = ui.estimated_calls_notice(steps, cfg["max_repeated_runs"],
                                  ui.estimate_cost(cfg, model, steps, 70, 1))
    st.caption(f"Model: `{model}` (needs prefill)")

    if ui.run_button(KEY) and ok:
        rows: List[Dict[str, Any]] = []
        results = []
        text = start
        bar = st.progress(0.0)
        for i in range(steps):
            try:
                r = api.call(**completion_request(text, model=model, max_tokens=1))
            except api.BackendError as e:
                st.error(str(e))
                break
            results.append(r)
            rows.append({
                "step": i + 1,
                "input (what the model saw)": text,
                "token picked": ui.show_token(r["text"]) if r["text"] else "⏹ stop",
                "stop_reason": r["stop_reason"],
            })
            bar.progress((i + 1) / steps, text=f"Step {i + 1}/{steps}")
            if r["stop_reason"] == "end_turn":
                break  # the model picked its stop token: the loop is over
            text += r["text"]
        bar.empty()
        st.session_state[f"{KEY}_out"] = {"start": start, "rows": rows, "results": results}

    # A fresh run is parked in session_state; save it to disk, then always
    # read from disk so the last run stays visible (for free) next time.
    if f"{KEY}_out" in st.session_state:
        ui.save_run(KEY, st.session_state.pop(f"{KEY}_out"))
    out = ui.load_run(KEY)
    if out:
        tokens = [r["text"] for r in out["results"] if r["text"]]
        st.markdown("**The tokens the loop added** (each colored chip = one forward pass):")
        token_chips([out["start"]] + tokens)
        st.dataframe(pd.DataFrame(out["rows"]), hide_index=True, width="stretch")
        if out["results"]:
            last = out["results"][-1]
            ui.show_exchange(completion_request(out["rows"][-1]["input (what the model saw)"],
                                                model=last["model"], max_tokens=1), last)
        spent(out["results"])
        ui.show_prediction_reminder(KEY)

    ui.what_this_shows(
        KEY,
        "A whole answer is just this loop. Every row is a **separate, stateless** "
        "call: the model received the full text so far and returned one token. "
        "Look at the *input* column: it grows by exactly one token per step, "
        "because the model's own output is fed back in as input.\n\n"
        "`stop_reason = max_tokens` means we cut it off after one token (on purpose). "
        "`end_turn` means the model picked its stop token, which ends the loop. "
        "Note how tokens start with a space (`·Paris`), and longer words may "
        "arrive in several pieces.",
    )


def streaming(cfg: Dict[str, Any]) -> None:
    KEY = "l01_stream"
    model = cfg["default_model"]

    st.markdown("### 🧪 Experiment 3 · Watch the answer arrive")
    st.write(
        "Normally the loop runs on Anthropic's servers. With **streaming**, the "
        "API sends each piece the moment it's generated instead of waiting for the end."
    )
    ui.prediction_box(KEY, "Will the text arrive in one burst, or steadily over time?")
    prompt = st.text_input("Prompt", "Explain how rain forms to a 7-year-old, in about 120 words.",
                           key=f"{KEY}_prompt")
    ui.estimated_calls_notice(1, cfg["max_repeated_runs"], ui.estimate_cost(cfg, model, 1, 30, 250))
    st.caption(f"Model: `{model}`")

    if ui.run_button(KEY):
        live = st.empty()
        chunks, final, text = [], None, ""
        try:
            for ev in api.stream([{"role": "user", "content": prompt}], model=model, max_tokens=400):
                if ev["type"] == "text":
                    text += ev["text"]
                    chunks.append({"t (s)": ev["t"], "chunk": ev["text"], "chars so far": len(text)})
                    live.markdown(text + " ▌")
                else:
                    final = ev
            live.empty()
            st.session_state[f"{KEY}_out"] = {"chunks": chunks, "final": final, "prompt": prompt}
        except api.BackendError as e:
            st.error(str(e))

    # A fresh run is parked in session_state; save it to disk, then always
    # read from disk so the last run stays visible (for free) next time.
    if f"{KEY}_out" in st.session_state:
        ui.save_run(KEY, st.session_state.pop(f"{KEY}_out"))
    out = ui.load_run(KEY)
    if out and out["final"]:
        st.markdown(out["final"]["text"])
        df = pd.DataFrame(out["chunks"])
        fig = go.Figure(go.Scatter(
            x=df["t (s)"], y=df["chars so far"], mode="lines+markers",
            line=dict(color=charts.SERIES[0], width=2, shape="hv"), marker=dict(size=8),
            hovertemplate="%{x:.2f}s: %{y} characters<extra></extra>",
        ))
        fig.update_layout(title="Characters received over time (each dot = one chunk)",
                          height=320, margin=dict(l=10, r=10, t=50, b=10))
        fig.update_xaxes(title="seconds since request")
        fig.update_yaxes(title="characters received")
        st.plotly_chart(fig)
        f = out["final"]
        st.markdown(
            f"First chunk after **{df['t (s)'].iloc[0]:.2f}s** · {len(df)} chunks · "
            f"**{f['output_tokens']}** output tokens in {f['latency_s']:.2f}s"
        )
        with st.expander("See every chunk"):
            st.dataframe(df, hide_index=True, width="stretch")
        ui.show_exchange({"model": model, "max_tokens": 400,
                          "messages": [{"role": "user", "content": out["prompt"]}]}, f)
        spent([f])
        ui.show_prediction_reminder(KEY)

    ui.what_this_shows(
        KEY,
        "The answer arrives **front to back, steadily**: a staircase, not a single "
        "jump. That's the generation loop happening live. Each chunk holds a few "
        "tokens the model has just produced. This is why chat apps 'type' at you: "
        "the end of the answer genuinely doesn't exist yet when the start appears.",
    )


def input_vs_output(cfg: Dict[str, Any]) -> None:
    KEY = "l01_io"
    model = cfg["default_model"]

    st.markdown("### 🧪 Experiment 4 · Reading is parallel, writing is sequential")
    st.write(
        "Two calls. **A** sends a long input and asks for a tiny output. **B** sends "
        "a tiny input and asks for a long output. Then we compare how long each took."
    )
    ui.prediction_box(KEY, "Which call takes longer, the one with ~2,000 input tokens or the one with ~250 output tokens?")
    ui.estimated_calls_notice(2, cfg["max_repeated_runs"], ui.estimate_cost(cfg, model, 2, 1100, 130))
    st.caption(f"Model: `{model}`")

    filler = ("The quick brown fox jumps over the lazy dog while the farmer counts "
              "sheep in the green valley. ") * 100
    req_a = {"model": model, "max_tokens": 5,
             "messages": [{"role": "user", "content": filler + "\n\nIgnore the text above. Reply with just: OK"}]}
    req_b = {"model": model, "max_tokens": 600,
             "messages": [{"role": "user", "content": "Count from 1 to 120, numbers separated by spaces. Nothing else."}]}

    if ui.run_button(KEY):
        try:
            a = api.call(**req_a)
            time.sleep(0.5)
            b = api.call(**req_b)
            st.session_state[f"{KEY}_out"] = {"a": a, "b": b}
        except api.BackendError as e:
            st.error(str(e))

    # A fresh run is parked in session_state; save it to disk, then always
    # read from disk so the last run stays visible (for free) next time.
    if f"{KEY}_out" in st.session_state:
        ui.save_run(KEY, st.session_state.pop(f"{KEY}_out"))
    out = ui.load_run(KEY)
    if out:
        a, b = out["a"], out["b"]
        labels = [f"A: {a['input_tokens']:,} in → {a['output_tokens']} out",
                  f"B: {b['input_tokens']:,} in → {b['output_tokens']} out"]
        fig = go.Figure(go.Bar(
            x=[a["latency_s"], b["latency_s"]], y=labels, orientation="h",
            marker_color=[charts.SERIES[0], charts.SERIES[1]],
            text=[f"{a['latency_s']:.2f}s", f"{b['latency_s']:.2f}s"], textposition="outside",
            hovertemplate="%{y}<br>%{x:.2f} seconds<extra></extra>",
        ))
        fig.update_layout(title="Wall-clock time per call", height=240, bargap=0.4,
                          margin=dict(l=10, r=40, t=50, b=10))
        fig.update_xaxes(title="seconds")
        st.plotly_chart(fig)

        st.dataframe(pd.DataFrame([
            {"call": "A (long input)", "input tokens": a["input_tokens"], "output tokens": a["output_tokens"],
             "seconds": a["latency_s"], "cost $": round(a["estimated_cost_usd"], 6)},
            {"call": "B (long output)", "input tokens": b["input_tokens"], "output tokens": b["output_tokens"],
             "seconds": b["latency_s"], "cost $": round(b["estimated_cost_usd"], 6)},
        ]), hide_index=True, width="stretch")
        spent([a, b])
        st.caption("Network delays add noise. Run it a couple of times; the pattern holds.")
        ui.show_prediction_reminder(KEY)

    ui.what_this_shows(
        KEY,
        "Call A handled roughly **10× more tokens** in total, yet it's usually "
        "*faster*. The input is processed **in one go**: all 2,000 tokens are "
        "already known, so they can be computed in parallel. Call B's output "
        "needs **one forward pass per token**, each waiting for the previous one.\n\n"
        "The same asymmetry shows up in price: output tokens cost 5× more than "
        "input tokens on this model.",
    )


def compounding(cfg: Dict[str, Any]) -> None:
    KEY = "l01_compound"
    model = cfg["sampling_model"]

    st.markdown("### 🧪 Experiment 5 · Plant a wrong premise and watch it grow")
    st.write(
        "Same question twice. In **B** we write the first words of Claude's answer "
        "for it, including a false claim (Australia's capital is Canberra, not "
        "Sydney). The model then has to continue from text that is now part of "
        "its own output."
    )
    ui.prediction_box(KEY, "Will Claude correct the planted error, or build on it?")
    question = st.text_input("Question", "In three sentences, tell me about the capital city of Australia.",
                             key=f"{KEY}_q")
    planted = st.text_input("Planted start of answer (B)", "Sydney, the capital of Australia, is famous for",
                            key=f"{KEY}_p")
    ui.estimated_calls_notice(2, cfg["max_repeated_runs"], ui.estimate_cost(cfg, model, 2, 40, 150))
    st.caption(f"Model: `{model}` (needs prefill)")

    req_a = {"model": model, "max_tokens": 150, "messages": [{"role": "user", "content": question}]}
    req_b = {"model": model, "max_tokens": 150, "messages": [
        {"role": "user", "content": question}, {"role": "assistant", "content": planted}]}

    if ui.run_button(KEY):
        try:
            st.session_state[f"{KEY}_out"] = {
                "a": api.call(**req_a), "b": api.call(**req_b), "planted": planted,
                "req_a": req_a, "req_b": req_b,
            }
        except api.BackendError as e:
            st.error(str(e))

    # A fresh run is parked in session_state; save it to disk, then always
    # read from disk so the last run stays visible (for free) next time.
    if f"{KEY}_out" in st.session_state:
        ui.save_run(KEY, st.session_state.pop(f"{KEY}_out"))
    out = ui.load_run(KEY)
    if out:
        c1, c2 = st.columns(2)
        with c1.container(border=True):
            st.markdown("**A · Normal answer**")
            st.write(out["a"]["text"])
        with c2.container(border=True):
            st.markdown("**B · Answer that starts with the planted premise**")
            st.markdown(f":red-background[{out['planted']}]" + out["b"]["text"])
            st.caption("Highlighted = text we planted. The rest = the model's continuation.")
        ui.show_exchange(out["req_b"], out["b"])
        spent([out["a"], out["b"]])
        ui.show_prediction_reminder(KEY)

    ui.what_this_shows(
        KEY,
        "From the model's point of view, the planted words are **its own output**: "
        "the sequence it must continue. Every later forward pass is conditioned on "
        "*\"Sydney, the capital of Australia\"* being part of the text, so the most "
        "plausible continuation usually builds on it fluently and confidently.\n\n"
        "If the model *did* correct itself (\"…actually, the capital is Canberra\"), "
        "notice that the false words are **still there**. It can only add text "
        "after them, never delete them. A correction happens only when one is "
        "the most plausible continuation. That's a *learned pattern*, not a truth "
        "check, and it is much less likely when the mistake is subtle.",
    )


def opening_word(cfg: Dict[str, Any]) -> None:
    KEY = "l01_plan"
    model = cfg["sampling_model"]

    st.markdown("### 🧪 Experiment 6 · One opening word steers the whole shape")
    st.write(
        "Same question, two answers. We only choose the **first word** of each "
        "answer. If the model had a plan, the overall shape would be the same."
    )
    ui.prediction_box(KEY, "How different will the two answers look in structure, not just wording?")
    question = st.text_input("Question", "How should I start learning to code?", key=f"{KEY}_q")
    c1, c2 = st.columns(2)
    open_a = c1.text_input("Opening word A", "First,", key=f"{KEY}_a")
    open_b = c2.text_input("Opening word B", "Honestly,", key=f"{KEY}_b")
    ui.estimated_calls_notice(2, cfg["max_repeated_runs"], ui.estimate_cost(cfg, model, 2, 30, 200))
    st.caption(f"Model: `{model}` (needs prefill)")

    def req(opening: str) -> Dict[str, Any]:
        return {"model": model, "max_tokens": 200, "messages": [
            {"role": "user", "content": question}, {"role": "assistant", "content": opening}]}

    if ui.run_button(KEY):
        try:
            st.session_state[f"{KEY}_out"] = [
                (open_a, req(open_a), api.call(**req(open_a))),
                (open_b, req(open_b), api.call(**req(open_b))),
            ]
        except api.BackendError as e:
            st.error(str(e))

    # A fresh run is parked in session_state; save it to disk, then always
    # read from disk so the last run stays visible (for free) next time.
    if f"{KEY}_out" in st.session_state:
        ui.save_run(KEY, st.session_state.pop(f"{KEY}_out"))
    out = ui.load_run(KEY)
    if out:
        cols = st.columns(2)
        for col, (opening, request, r) in zip(cols, out):
            with col.container(border=True):
                st.markdown(f"**Opens with:** `{opening}`")
                st.markdown(f":blue-background[{opening}]" + r["text"])
                st.caption(f"{r['output_tokens']} output tokens · stop: {r['stop_reason']}")
        ui.show_exchange(out[0][1], out[0][2])
        spent([r for _, _, r in out])
        ui.show_prediction_reminder(KEY)

    ui.what_this_shows(
        KEY,
        "A single forced opening token changed the **shape** of everything after "
        "it: list vs. conversational prose, different length, different tone. "
        "There was no outline waiting to be filled in. Each token made some "
        "continuations more likely than others, and the structure **emerged** "
        "token by token. Well-organised answers happen because well-organised "
        "text was common in training, not because a planning step ran.",
    )
