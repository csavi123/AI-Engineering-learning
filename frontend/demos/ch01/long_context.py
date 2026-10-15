"""Lesson 07 demos: what to drop when a chat outgrows its budget, a needle
test, and output truncation."""
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

import api
import ui
from demos.ch01.common import spent

# A 12-turn chat. Some turns carry facts the final question depends on.
CHAT = [
    ("user", "Hi! I'm planning dinners for the week. Important: I'm allergic to peanuts.", "allergy"),
    ("assistant", "Got it, no peanuts. How many people are you cooking for?", None),
    ("user", "Just two of us. We love Thai food.", "cuisine"),
    ("assistant", "Two people, Thai flavours. Any time limits?", None),
    ("user", "Weeknights I have about 30 minutes, and my budget is $40 for the week.", "budget"),
    ("assistant", "30 minutes and $40 a week. I'll keep it simple and cheap.", None),
    ("user", "Monday we're out, so skip that day.", None),
    ("assistant", "Skipping Monday.", None),
    ("user", "Can Tuesday be something with rice?", None),
    ("assistant", "Sure: a quick vegetable fried rice on Tuesday.", None),
    ("user", "Sounds good. Wednesday something with noodles?", None),
    ("assistant", "Wednesday: stir-fried noodles with vegetables.", None),
    ("user", "Now suggest Thursday's dinner.", "question"),
]
SYSTEM = ("system", "You are a helpful meal-planning assistant.", None)
# The pre-written summary a "summarize old turns" strategy might produce.
# Like real summaries it is lossy: it keeps the allergy and budget but drops
# the cuisine preference.
SUMMARY = ("system", "Summary of earlier chat: cooking for two, allergic to peanuts, "
                     "30 minutes on weeknights, $40/week budget.", "allergy budget")
FACTS = {"allergy": "Peanut allergy (turn 1)", "cuisine": "Loves Thai (turn 3)",
         "budget": "$40 budget (turn 5)", "question": "Thursday question (turn 13)"}


def approx_tokens(text: str) -> int:
    """Rough estimate: ~1.3 tokens per English word (see lesson 02 for exact counts)."""
    return max(1, round(len(text.split()) * 1.3))


def _fit_from_end(turns: List[tuple], budget: int) -> List[tuple]:
    kept, used = [], 0
    for turn in reversed(turns):
        cost = approx_tokens(turn[1])
        if used + cost > budget:
            break
        kept.insert(0, turn)
        used += cost
    return kept


def apply_strategy(name: str, budget: int, last_n: int) -> List[tuple]:
    """Return the turns that would actually be sent under each strategy."""
    room = budget - approx_tokens(SYSTEM[1])
    if name == "Drop oldest":
        return [SYSTEM] + _fit_from_end(CHAT, room)
    if name == "Keep last N turns":
        return [SYSTEM] + _fit_from_end(CHAT[-last_n:], room)
    # Summarize: summary of everything except the last 4 turns, then those turns.
    room -= approx_tokens(SUMMARY[1])
    return [SYSTEM, SUMMARY] + _fit_from_end(CHAT[-4:], room)


def _facts_kept(turns: List[tuple]) -> Dict[str, bool]:
    tags = " ".join(t[2] for t in turns if t[2])
    return {f: f in tags for f in FACTS}


def truncation_sim(cfg: Dict[str, Any]) -> None:
    st.caption("🆓 Free simulation: no API calls. Token sizes are estimates (~1.3 per word).")
    total = approx_tokens(SYSTEM[1]) + sum(approx_tokens(t[1]) for t in CHAT)
    c1, c2 = st.columns(2)
    budget = c1.slider("Token budget for the input", 40, total, min(110, total), 10, key="trunc_budget",
                       help=f"The full chat is ≈{total} tokens.")
    last_n = c2.slider("N for 'keep last N turns'", 1, len(CHAT), 4, key="trunc_n")

    strategies = ["Drop oldest", "Keep last N turns", "Summarize old turns"]
    grid = {s: _facts_kept(apply_strategy(s, budget, last_n)) for s in strategies}
    st.markdown(f"**Which facts survive a {budget}-token budget?** (full chat ≈ {total} tokens)")
    st.dataframe(pd.DataFrame(
        {s: ["✅" if grid[s][f] else "❌" for f in FACTS] for s in strategies},
        index=list(FACTS.values()),
    ), width="stretch")

    show = st.radio("See what each strategy sends", strategies, horizontal=True, key="trunc_show")
    for role, text, _ in apply_strategy(show, budget, last_n):
        st.markdown(f"`{role}` {text}")
    st.caption("No strategy is free: dropping loses early facts, keeping N is blunt, and a summary "
               "costs an extra model call and can silently leave things out (here: the Thai preference).")


# --- live demos ------------------------------------------------------------
FILLER = ("The town library opened in 1952 and has been renovated twice since then. "
          "Volunteers run a reading club on Thursdays and a repair café on Saturdays. ")
NEEDLE = "The secret ingredient in Grandma's soup is smoked paprika. "
QUESTION = "What is the secret ingredient in Grandma's soup? Answer in a few words."


def build_haystack(n_sentences: int, depth: float) -> str:
    """Filler text with the needle inserted at `depth` (0 = start, 1 = end)."""
    sentences = [s.strip() + "." for s in FILLER.split(". ") if s.strip()] * (n_sentences // 2)
    pos = int(len(sentences) * depth)
    sentences.insert(pos, NEEDLE.strip())
    return " ".join(sentences)


def needle_test(cfg: Dict[str, Any]) -> None:
    KEY = "l07_needle"
    model = cfg["default_model"]
    st.write("Hide one fact (the *needle*) at different depths in filler text, then ask about it.")
    ui.prediction_box(KEY, "Will Claude find the fact at every depth? Does it get harder with more text?")
    sizes = {"≈1,000 tokens": 60, "≈3,000 tokens": 180, "≈8,000 tokens": 480}
    size = st.radio("Haystack size", list(sizes), horizontal=True, key=f"{KEY}_size")
    depths = [0.1, 0.5, 0.9]
    approx_in = int(size.strip("≈ tokens").replace(",", ""))
    ui.estimated_calls_notice(len(depths), cfg["max_repeated_runs"],
                              ui.estimate_cost(cfg, model, len(depths), approx_in, 10))
    st.caption(f"Model: `{model}`")

    if ui.run_button(KEY):
        rows, results = [], []
        try:
            for d in depths:
                text = build_haystack(sizes[size], d)
                r = api.call([{"role": "user", "content": text + "\n\n" + QUESTION}], model=model, max_tokens=20)
                results.append(r)
                rows.append({"depth": f"{d:.0%}", "input tokens": r["input_tokens"],
                             "answer": r["text"].strip(), "found": "✅" if "paprika" in r["text"].lower() else "❌"})
            st.session_state[f"{KEY}_out"] = {"size": size, "rows": rows, "results": results}
        except api.BackendError as e:
            st.error(str(e))

    if f"{KEY}_out" in st.session_state:
        ui.save_run(KEY, st.session_state.pop(f"{KEY}_out"))
    out = ui.load_run(KEY)
    if out:
        st.markdown(f"**Haystack: {out['size']}**")
        st.dataframe(pd.DataFrame(out["rows"]), hide_index=True, width="stretch")
        spent(out["results"])
        ui.show_prediction_reminder(KEY)

    ui.what_this_shows(
        KEY,
        "At these small sizes a modern model usually finds a single, clearly worded fact "
        "anywhere. That's a pass on an *easy* test, not proof that long context is safe. "
        "Recall gets weaker with much longer inputs, with facts reworded so they don't match "
        "the question, and when several facts must be combined; middle positions tend to "
        "suffer first. Meanwhile **cost** grew with every token of haystack. Test with your "
        "own documents and questions before trusting long context.",
    )


def output_truncation(cfg: Dict[str, Any]) -> None:
    KEY = "l07_maxtok"
    model = cfg["default_model"]
    st.write("Output has its own limit: `max_tokens`. Set it low and watch the answer get cut off.")
    ui.prediction_box(KEY, "What will the stop reason be, and where will the answer stop?")
    max_tokens = st.slider("max_tokens", 5, 80, 20, key=f"{KEY}_n")
    ui.estimated_calls_notice(1, cfg["max_repeated_runs"], ui.estimate_cost(cfg, model, 1, 20, max_tokens))
    st.caption(f"Model: `{model}`")

    if ui.run_button(KEY):
        try:
            r = api.call([{"role": "user", "content": "Explain how a rainbow forms."}],
                         model=model, max_tokens=max_tokens)
            st.session_state[f"{KEY}_out"] = {"result": r, "max_tokens": max_tokens}
        except api.BackendError as e:
            st.error(str(e))

    if f"{KEY}_out" in st.session_state:
        ui.save_run(KEY, st.session_state.pop(f"{KEY}_out"))
    out = ui.load_run(KEY)
    if out:
        r = out["result"]
        st.markdown(f"> {r['text']} **✂**")
        st.markdown(f"`max_tokens = {out['max_tokens']}` · output tokens: **{r['output_tokens']}** · "
                    f"stop_reason: **`{r['stop_reason']}`**")
        spent([r])
        ui.show_prediction_reminder(KEY)

    ui.what_this_shows(
        KEY,
        "`stop_reason: max_tokens` means the answer was **cut off**, not finished. It "
        "stops mid-sentence because generation simply ends when the budget runs out "
        "(the model doesn't know the limit in advance). Always check `stop_reason` in "
        "your code: `end_turn` = finished, `max_tokens` = truncated.",
    )
