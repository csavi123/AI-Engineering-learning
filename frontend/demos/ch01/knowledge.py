"""Lesson 05 demos: checking citations, and asking for facts that don't exist."""
import re
from collections import Counter
from typing import Any, Dict

import pandas as pd
import streamlit as st

import api
import crossref
import ui
from demos.ch01.common import completion_request, spent


def made_up_fact(cfg: Dict[str, Any]) -> None:
    KEY = "l01_lookup"
    model = cfg["sampling_model"]
    cap = cfg["max_repeated_runs"]

    st.markdown("### 🧪 Experiment 7 · Ask for a fact that doesn't exist")
    st.write(
        "*Veltrania* is a made-up country. A database would answer *\"no row found\"*. "
        "Let's see what a next-token predictor does with the same sentence start. "
        "We sample a few words of continuation several times for each."
    )
    ui.prediction_box(KEY, "What will come after \"The capital of Veltrania is\"? Will it be the same each time?")
    c1, c2 = st.columns(2)
    real = c1.text_input("Real fact", "The capital of France is", key=f"{KEY}_real")
    fake = c2.text_input("Nonexistent fact", "The capital of Veltrania is", key=f"{KEY}_fake")
    n = st.slider("Samples each", 3, min(20, cap), 8, key=f"{KEY}_n")
    ok = ui.estimated_calls_notice(2 * n, 2 * cap, ui.estimate_cost(cfg, model, 2 * n, 60, 8))
    st.caption(f"Model: `{model}` (raw completion via prefill, temperature 1)")

    if ui.run_button(KEY) and ok:
        out = {}
        for label, text in (("real", real), ("fake", fake)):
            r = completion_request(text, model=model, max_tokens=8, temperature=1.0)
            out[label] = {"text": text, "request": r,
                          "results": ui.run_repeated(lambda: api.call(**r), n, f"Sampling '{text}'")}
        st.session_state[f"{KEY}_out"] = out

    # A fresh run is parked in session_state; save it to disk, then always
    # read from disk so the last run stays visible (for free) next time.
    if f"{KEY}_out" in st.session_state:
        ui.save_run(KEY, st.session_state.pop(f"{KEY}_out"))
    out = ui.load_run(KEY)
    if out:
        cols = st.columns(2)
        for col, data in zip(cols, out.values()):
            with col:
                st.markdown(f"**\"{data['text']} …\"**")
                conts = [r["text"].strip() or "⏹ (stopped)" for r in data["results"]]
                st.dataframe(pd.DataFrame({"continuation": conts}), hide_index=True,
                             width="stretch")
                first_words = Counter(c.split()[0].strip(".,") if c.split() else c for c in conts)
                st.markdown(f"**{len(first_words)}** different first words in {len(conts)} samples")
        if out["fake"]["results"]:
            ui.show_exchange(out["fake"]["request"], out["fake"]["results"][0])
        spent([r for d in out.values() for r in d["results"]])
        ui.show_prediction_reminder(KEY)

    ui.what_this_shows(
        KEY,
        "For France, the samples agree: the probability is piled on `Paris`. For "
        "Veltrania, the model still continues the sentence, often with a **fluent, "
        "confident, invented city name**, and the name changes between samples. "
        "There is no row to be missing. There is only a distribution, and a "
        "distribution always has a most-likely next token.\n\n"
        "If some samples *did* say the place isn't real, that's because "
        "\"…is not a real country\" was itself a plausible continuation here. It's "
        "a learned pattern, not a lookup miss, and it fails exactly when the fake "
        "thing sounds real enough. Page 05 tests this systematically.",
    )


DOI_PATTERN = re.compile(r"10\.\d{4,9}/[^\s|,;]+")


def _check_table(dois):
    rows = []
    for doi in dois:
        doi = doi.strip().rstrip(".)")
        res = crossref.lookup(doi)
        mark = {"found": "✅ real", "not found": "❌ not found", "error": "⚠️ error"}[res["status"]]
        rows.append({"DOI": doi, "Crossref says": mark, "Registered title": res["title"]})
    return rows


def doi_checker(cfg: Dict[str, Any]) -> None:
    st.caption("🆓 Free: checks DOIs against Crossref's public registry. No Anthropic call.")
    text = st.text_area(
        "DOIs to check, one per line",
        "10.1038/nature14539\n10.1145/3442188.3445922\n10.9999/llm.citations.2023.0042",
        key="doi_input", height=100,
        help="The first two are real papers; the third is made up, the way a hallucinated citation looks.",
    )
    if st.button("🔎 Check with Crossref (free)", key="doi_check", type="primary"):
        dois = [d for d in text.splitlines() if d.strip()]
        with st.spinner("Asking Crossref…"):
            st.session_state["doi_rows"] = _check_table(dois)
    rows = st.session_state.get("doi_rows")
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.caption("A made-up DOI looks exactly like a real one. Only an outside check can tell them apart.")


def citation_check(cfg: Dict[str, Any]) -> None:
    KEY = "l05_cite"
    model = cfg["default_model"]
    st.write(
        "Ask Claude for papers on a niche topic, then check every DOI it gives against "
        "Crossref. The niche-ier the topic, the more likely some citations don't exist."
    )
    ui.prediction_box(KEY, "How many of the 3 DOIs will turn out to be real?")
    topic = st.text_input("Niche topic", "how tokenization affects arithmetic in small language models",
                          key=f"{KEY}_topic")
    ui.estimated_calls_notice(1, cfg["max_repeated_runs"], ui.estimate_cost(cfg, model, 1, 80, 300))
    st.caption(f"Model: `{model}` · DOI checks via Crossref are free")

    prompt = (f"List 3 peer-reviewed papers about {topic}. One per line, in this exact format:\n"
              "TITLE | FIRST AUTHOR | YEAR | DOI")
    if ui.run_button(KEY):
        try:
            r = api.call([{"role": "user", "content": prompt}], model=model, max_tokens=400)
            dois = DOI_PATTERN.findall(r["text"])
            st.session_state[f"{KEY}_out"] = {"result": r, "rows": _check_table(dois), "topic": topic}
        except api.BackendError as e:
            st.error(str(e))

    if f"{KEY}_out" in st.session_state:
        ui.save_run(KEY, st.session_state.pop(f"{KEY}_out"))
    out = ui.load_run(KEY)
    if out:
        st.markdown("**Claude's answer:**")
        st.code(out["result"]["text"], language=None)
        if out["rows"]:
            st.dataframe(pd.DataFrame(out["rows"]), hide_index=True, width="stretch")
            real = sum(1 for row in out["rows"] if row["Crossref says"].startswith("✅"))
            st.markdown(f"**{real} of {len(out['rows'])}** DOIs exist. Even a real DOI can belong to a "
                        "*different* paper, so compare the registered title with Claude's title.")
        else:
            st.info("No DOIs found in the answer. The model may have declined or used another format.")
        spent([out["result"]])
        ui.show_prediction_reminder(KEY)

    ui.what_this_shows(
        KEY,
        "Every citation came out in the same fluent, confident format, whether or not "
        "it exists. The model produced the most *plausible-looking* reference, and "
        "nothing in the generation loop checked it against a registry. That check had "
        "to happen outside the model (Crossref). If all of them were real this time, "
        "try a more obscure topic: invented citations appear most on rare, specific, "
        "or recent subjects.",
    )
