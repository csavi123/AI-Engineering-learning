"""Live demo: two calls share nothing (lesson 03)."""

from typing import Any, Dict

import streamlit as st

import api
import ui
from demos.ch01.common import spent


def code_word(cfg: Dict[str, Any]) -> None:
    KEY = "l01_memory"
    model = cfg["default_model"]

    st.markdown("### 🧪 Experiment 8 · Two calls share nothing")
    st.write(
        "Call 1 tells Claude a code word. Call 2, a moment later, asks for it. "
        "Call 3 asks again, but this time **we resend call 1 and its reply** "
        "inside the input."
    )
    ui.prediction_box(KEY, "Which of call 2 and call 3 will know the code word?")
    word = st.text_input("Code word", "PELICAN-42", key=f"{KEY}_word")
    ui.estimated_calls_notice(3, cfg["max_repeated_runs"], ui.estimate_cost(cfg, model, 3, 40, 30))
    st.caption(f"Model: `{model}`")

    tell = {"role": "user", "content": f"Remember this code word: {word}. Just reply 'OK'."}
    ask = {"role": "user", "content": "What code word did I give you? If you don't know, say so."}

    if ui.run_button(KEY):
        try:
            r1 = api.call([tell], model=model, max_tokens=20)
            req2 = [ask]
            r2 = api.call(req2, model=model, max_tokens=60)
            req3 = [tell, {"role": "assistant", "content": r1["text"] or "OK"}, ask]
            r3 = api.call(req3, model=model, max_tokens=60)
            st.session_state[f"{KEY}_out"] = [
                ("Call 1 · tell", [tell], r1), ("Call 2 · ask (fresh call)", req2, r2),
                ("Call 3 · ask (history resent)", req3, r3),
            ]
        except api.BackendError as e:
            st.error(str(e))

    # A fresh run is parked in session_state; save it to disk, then always
    # read from disk so the last run stays visible (for free) next time.
    if f"{KEY}_out" in st.session_state:
        ui.save_run(KEY, st.session_state.pop(f"{KEY}_out"))
    out = ui.load_run(KEY)
    if out:
        cols = st.columns(3)
        for col, (title, msgs, r) in zip(cols, out):
            with col.container(border=True):
                st.markdown(f"**{title}**")
                st.markdown("*Input sent:*")
                for m in msgs:
                    st.markdown(f"`{m['role']}`: {m['content']}")
                st.markdown("*Reply:*")
                st.info(r["text"] or "(empty)")
                st.caption(f"{r['input_tokens']} input tokens")
        spent([r for _, _, r in out])
        ui.show_prediction_reminder(KEY)

    ui.what_this_shows(
        KEY,
        "Call 2's input doesn't contain the code word, so the model cannot know it. "
        "Nothing from call 1 was stored anywhere. Call 3 knows it **only because "
        "we put it back into the input** (and notice its input-token count is "
        "higher: you pay for that history every time). Chat apps feel like they "
        "remember only because they resend the conversation on every turn.",
    )
