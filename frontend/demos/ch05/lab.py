"""Chapter 5 Prompt Lab: change a prompt, then MEASURE the change.

The method in one breath: a fixed set of labelled messages, one prompt
change per version, every version scored by the same code, and Before vs
After compared on the SAME messages. Each tab answers one interview
question using your own saved numbers, not an opinion.

Runs are saved per version (data/runs/ch05_eval_<version>.json), so you can
run one version at a time and every comparison afterwards is free.

Showcase: data/runs isn't committed and the hosted app's disk resets, so
"Save as showcase" copies your runs into content/ch05_showcase/. Commit that
folder and every visitor sees your real numbers without any API calls.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
import streamlit as st

import api
import charts
import store
import ui
from demos.ch05 import scoring, walkthrough
from demos.ch05.prompts import VERSIONS, build_request, load_dataset, system_prompt, user_message

KEY = "ch05_lab"
SPLITS = ["dev", "test", "prod"]
# A label is 1-4 tokens. v1's chatty answers get cut off here, which is fine:
# they break the contract either way, and it keeps v1 cheap.
MAX_TOKENS = 20
CALLS_PER_DAY = walkthrough.CALLS_PER_DAY
SHOWCASE_DIR = Path(__file__).resolve().parents[3] / "content" / "ch05_showcase"


def _run_key(version: str) -> str:
    return f"ch05_eval_{version}"


def _pct(x) -> str:
    return "—" if x is None else f"{x:.0%}"


def _short(text: str, n: int = 70) -> str:
    one_line = " ".join(text.split()) or "(empty)"
    return one_line if len(one_line) <= n else one_line[: n - 1] + "…"


# --- Running one version ---------------------------------------------------
def _run(version: str, cases: List[Dict[str, Any]], repeats: int, model: str) -> Dict[str, Any]:
    """Send every chosen message `repeats` times and keep every raw output.

    Raw outputs are stored, not just "right/wrong", so a failure can be
    inspected later exactly as the model wrote it (tab 3).
    """
    rows, skipped = [], []
    total, done = len(cases) * repeats, 0
    bar = st.progress(0.0, text=f"Running {version}")
    for case in cases:
        row = {
            "id": case["id"], "split": case["split"], "tag": case["tag"],
            "gold": case["label"], "text": case["text"],
            "outputs": [], "input_tokens": [], "output_tokens": [], "cost": 0.0,
        }
        req = build_request(version, case["text"])
        for _ in range(repeats):
            try:
                r = api.call(req["messages"], system=req["system"], model=model, max_tokens=MAX_TOKENS)
                row["outputs"].append(r["text"])
                row["input_tokens"].append(r["input_tokens"])
                row["output_tokens"].append(r["output_tokens"])
                row["cost"] += r["estimated_cost_usd"]
            except api.BackendError as e:
                msg = str(e)
                if msg.startswith("Anthropic API said"):
                    # The API refused this input (v1 sends an empty message
                    # as-is). The pipeline got no label: a contract failure,
                    # and exactly the "define empty input" lesson.
                    row["outputs"].append(f"⚠️ request rejected: {msg}")
                    row["input_tokens"].append(0)
                    row["output_tokens"].append(0)
                else:
                    skipped.append(f"{case['id']}: {msg}")
                    if msg.startswith("Monthly budget reached"):
                        bar.empty()
                        st.error(msg)
                        return {}
            done += 1
            bar.progress(done / total, text=f"Running {version} ({done}/{total})")
        rows.append(row)
    bar.empty()
    if skipped:
        st.warning(f"{len(skipped)} call(s) failed and were left out. First: {skipped[0]}")
    return {
        "version": version, "name": VERSIONS[version].name, "model": model,
        "repeats": repeats, "system": system_prompt(version), "rows": rows,
    }


def _run_section(cfg: Dict[str, Any], cases: List[Dict[str, Any]]) -> None:
    st.markdown("#### 1 · Run one prompt version")
    c1, c2, c3 = st.columns([2, 2, 1])
    version = c1.selectbox("Prompt version", list(VERSIONS),
                           format_func=lambda v: VERSIONS[v].name, key=f"{KEY}_version")
    splits = c2.multiselect("Message sets", SPLITS, default=["test", "prod"], key=f"{KEY}_splits")
    repeats = c3.selectbox("Repeats", [1, 3], key=f"{KEY}_repeats",
                           help="3 repeats measure the noise: does the same message get the same label every time?")
    v = VERSIONS[version]
    st.caption(f"**The one change:** {v.change} · **meant to fix:** {v.targets}")

    chosen = [c for c in cases if c["split"] in splits]
    model = cfg["default_model"]
    n_calls = len(chosen) * repeats
    # Rough guess: ~4 characters per token, plus the message itself.
    est = ui.estimate_cost(cfg, model, n_calls, len(system_prompt(version)) // 4 + 60, MAX_TOKENS)
    ok = bool(chosen) and ui.estimated_calls_notice(n_calls, cfg.get("eval_max_calls", 200), est)
    st.caption(f"Model: `{model}` · max {MAX_TOKENS} output tokens · one call after another (~1 s each)")
    ui.prediction_box(KEY, "What accuracy do you expect from this version on test, and on prod?")

    if ui.run_button(KEY, f"▶ Run {version} on {', '.join(splits) or 'nothing'}") and ok:
        run = _run(version, chosen, repeats, model)
        if run:
            ui.save_run(_run_key(version), run)
            cost = sum(r["cost"] for r in run["rows"])
            st.success(f"Saved {version}: {sum(len(r['outputs']) for r in run['rows'])} calls, "
                       f"estimated cost USD {cost:.5f}.")


# --- Overview of every saved run -------------------------------------------
def _local_runs() -> Dict[str, Dict[str, Any]]:
    runs = {}
    for v in VERSIONS:
        saved = store.load_run(_run_key(v))
        if saved:
            runs[v] = saved["data"]
    return runs


def _showcase_runs() -> Dict[str, Dict[str, Any]]:
    runs = {}
    for v in VERSIONS:
        try:
            runs[v] = json.loads((SHOWCASE_DIR / f"{v}.json").read_text())["data"]
        except (FileNotFoundError, json.JSONDecodeError):
            pass
    return runs


def _saved_runs() -> Tuple[Dict[str, Dict[str, Any]], str]:
    """Your own local runs if you have any, else the committed showcase."""
    local = _local_runs()
    if local:
        return local, "local"
    return _showcase_runs(), "showcase"


def _showcase_controls(runs: Dict[str, Dict[str, Any]], source: str) -> None:
    if source == "showcase" and runs:
        st.caption("📌 Showing the saved showcase results. Viewing them is free.")
    # BACKEND_TOKEN is set only in production, so on the hosted app visitors
    # can't overwrite the showcase; it's a button for you, locally.
    if source != "local" or os.environ.get("BACKEND_TOKEN"):
        return
    if st.button("📌 Save these runs as the showcase", key=f"{KEY}_showcase"):
        SHOWCASE_DIR.mkdir(parents=True, exist_ok=True)
        for v in VERSIONS:
            saved = store.load_run(_run_key(v))
            if saved:
                (SHOWCASE_DIR / f"{v}.json").write_text(json.dumps(saved, indent=2, ensure_ascii=False))
        st.success(f"Saved {len(runs)} run(s) to `content/ch05_showcase/`. Commit and push that "
                   "folder, and the hosted app shows these numbers to every visitor.")


def _overview(runs: Dict[str, Dict[str, Any]]) -> None:
    table = []
    for v, run in runs.items():
        every, dev, test, prod = (scoring.summary(run, s) for s in (None, ["dev"], ["test"], ["prod"]))
        table.append({
            "version": VERSIONS[v].name,
            "repeats": run["repeats"],
            "contract valid": _pct(every["valid"]),
            "dev acc": _pct(dev.get("accuracy")),
            "test acc (held out)": _pct(test.get("accuracy")),
            "prod acc (messy)": _pct(prod.get("accuracy")),
            "flips": _pct(every["flip_rate"]),
            "avg input tokens": round(every["avg_input_tokens"]),
            f"USD per {CALLS_PER_DAY:,} calls": round(every["cost_per_call"] * CALLS_PER_DAY, 3),
        })
    st.dataframe(pd.DataFrame(table), hide_index=True, width="stretch")


# --- Tab 1: what good looks like -------------------------------------------
def _tab_before_after(before, after) -> None:
    b, a = scoring.summary(before, ["test"]), scoring.summary(after, ["test"])
    if not b["cases"] or not a["cases"]:
        st.warning("Both versions need a run that includes the **test** set: that's where the headline number comes from.")
        return
    bn, an = VERSIONS[before["version"]].name, VERSIONS[after["version"]].name
    pairs = scoring.paired(before, after, ["test"])
    b_cost, a_cost = b["cost_per_call"] * CALLS_PER_DAY, a["cost_per_call"] * CALLS_PER_DAY

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Accuracy (held-out test)", _pct(a["accuracy"]), f"{(a['accuracy'] - b['accuracy']) * 100:+.0f} pts")
    c2.metric("Contract valid", _pct(a["valid"]), f"{(a['valid'] - b['valid']) * 100:+.0f} pts")
    c3.metric("Avg input tokens", round(a["avg_input_tokens"]),
              f"{a['avg_input_tokens'] - b['avg_input_tokens']:+.0f}", delta_color="inverse")
    c4.metric(f"USD per {CALLS_PER_DAY:,} calls", f"{a_cost:.3f}", f"{a_cost - b_cost:+.3f}", delta_color="inverse")
    st.caption(f"Before = {bn}, After = {an}. Deltas are After minus Before, on the same {len(pairs)} test messages.")

    st.plotly_chart(
        charts.percent_bars({f"Before · {bn}": b["per_class"], f"After · {an}": a["per_class"]},
                            "Accuracy per correct label · test set"),
        key=f"{KEY}_perclass",
    )
    st.success("**Your answer, from your own numbers:** " + walkthrough.headline(before, after))
    st.caption("That sentence is what 'good' looks like: a number, on held-out data, against a baseline, with its cost.")


# --- Tab 2: is it real? ----------------------------------------------------
def _case_table(pairs) -> pd.DataFrame:
    return pd.DataFrame([{
        "id": a["id"], "message": _short(a["text"]), "correct": a["gold"],
        "before said": scoring.majority(b), "after said": scoring.majority(a),
    } for b, a in pairs])


def _tab_is_it_real(before, after) -> None:
    pairs = scoring.paired(before, after, ["test"])
    if not pairs:
        st.warning("Both versions need the **test** set to compare.")
        return
    diff, lo, hi = scoring.bootstrap_diff(pairs)
    st.markdown(f"**1. Is the change bigger than luck?** Change: **{diff * 100:+.0f} pts**, "
                f"95% interval **{lo * 100:+.0f} to {hi * 100:+.0f} pts**.")
    if lo > 0:
        st.success("The whole interval is above zero: this improvement is very unlikely to be luck in which messages were in the set.")
    elif hi < 0:
        st.error("The whole interval is below zero: this change made things worse.")
    else:
        st.warning("The interval crosses zero: with this many messages you **can't tell this change from noise**. "
                   "It might be real, but you haven't shown it. Add cases or repeats before believing it.")

    st.markdown("**2. How noisy is the model on its own?** The same prompt and the same message can get different labels.")
    flips = {VERSIONS[r["version"]].name: scoring.summary(r, ["test"])["flip_rate"] for r in (before, after)}
    if any(f is None for f in flips.values()):
        st.info("Run a version with **3 repeats** to measure this. A change smaller than the run-to-run noise is not a change.")
    else:
        st.write(" · ".join(f"{name}: {_pct(f)} of messages flipped between repeats" for name, f in flips.items()))

    st.markdown("**3. Which messages moved?** A net +2 can hide 5 fixed and 3 broken.")
    fixed, broken = scoring.fixed_and_broken(pairs)
    c1, c2 = st.columns(2)
    c1.markdown(f"✅ **Fixed ({len(fixed)})**")
    if fixed:
        c1.dataframe(_case_table(fixed), hide_index=True)
    c2.markdown(f"❌ **Broken ({len(broken)})**")
    if broken:
        c2.dataframe(_case_table(broken), hide_index=True)

    st.markdown("**4. Did a fix in one place break another?**")
    b_pc = scoring.summary(before, ["test"])["per_class"]
    a_pc = scoring.summary(after, ["test"])["per_class"]
    worse = [lbl for lbl in a_pc if lbl in b_pc and a_pc[lbl] < b_pc[lbl] - 0.05]
    if worse:
        st.warning("Got worse: " + ", ".join(f"**{lbl}** {_pct(b_pc[lbl])} → {_pct(a_pc[lbl])}" for lbl in worse)
                   + ". This is overcorrection, hidden inside the overall number. Compare v4 (one example) with v5 (plus counter-examples).")
    else:
        st.write("No label got more than 5 pts worse.")

    st.markdown("**5. Did you tune to the messages you looked at?**")
    dev, test = scoring.summary(after, ["dev"]), scoring.summary(after, ["test"])
    if dev["cases"]:
        st.write(f"{VERSIONS[after['version']].name}: dev {_pct(dev['accuracy'])} vs held-out test {_pct(test['accuracy'])}. "
                 "If dev is much higher, the prompt learned your dev cases, not the task.")
    else:
        st.info("Include the **dev** set in a run to compare dev and held-out test.")


# --- Tab 3: works in testing, fails in production --------------------------
def _tab_production(runs, after) -> None:
    gap = {VERSIONS[v].name: (scoring.summary(r, ["test"]).get("accuracy"), scoring.summary(r, ["prod"]).get("accuracy"))
           for v, r in runs.items()}
    gap = {k: t for k, t in gap.items() if t[0] is not None and t[1] is not None}
    if gap:
        st.plotly_chart(charts.percent_bars(
            {"test (clean)": {k: t for k, (t, _) in gap.items()},
             "prod (messy)": {k: p for k, (_, p) in gap.items()}},
            "Same prompt, clean test messages vs messy production messages"), key=f"{KEY}_gap")
    else:
        st.info("Run versions on both **test** and **prod** to see the gap.")

    left, right = st.columns([1, 2])
    with left:
        st.markdown(
            "**🛠️ Debugging playbook**\n\n"
            "1. **Reproduce** with the real failing input, not a cleaned-up copy.\n"
            "2. **Print what the model actually saw:** the fully assembled prompt (right).\n"
            "3. **Name the failure:** shape (invalid output), behaviour (valid but wrong), "
            "or difficulty (scattered, no single pattern).\n"
            "4. **Add the case to the eval set**, so it can never silently come back.\n"
            "5. **Change one thing, re-run, compare** on the same cases (tabs 1–2)."
        )
    with right:
        name = VERSIONS[after["version"]].name
        rows = [r for r in scoring.rows_in(after, ["test", "prod"]) if not scoring.passes(r)]
        st.markdown(f"**Failures of {name}** (test + prod, grouped by confusion)")
        conf = scoring.confusions(rows)
        if not conf:
            st.success("No failures on test or prod in this run.")
            return
        st.dataframe(pd.DataFrame([
            {"correct": g, "model said": p, "calls": n, "kind": scoring.failure_kind(p)}
            for (g, p), n in conf.most_common()]), hide_index=True)
        pick = st.selectbox("Inspect a failing message", rows, key=f"{KEY}_inspect",
                            format_func=lambda r: f"{r['id']} [{r['split']}] {_short(r['text'], 50)}")
        st.markdown(f"Correct: **{pick['gold']}** · model said: "
                    + ", ".join(f"`{o.strip() or '(empty)'}`" for o in pick["outputs"]))
        st.caption("Exactly what was sent. The system prompt is the one saved with the run, not today's code.")
        st.code(after["system"], language=None)
        st.code(user_message(after["version"], pick["text"]), language=None)


# --- Tab 4: where information lives ----------------------------------------
TOOL_SKETCH = """{
  "name": "get_customer_account",
  "description": "Current plan, renewal date and refund eligibility",
  "input_schema": {"type": "object",
                   "properties": {"customer_id": {"type": "string"}}}
}"""


def _tab_placement(cases, key: str = f"{KEY}_place") -> None:
    """Also drawn by lesson 04, which passes its own `key` so widgets don't clash."""
    version = st.selectbox("Version", list(VERSIONS), index=len(VERSIONS) - 1,
                           format_func=lambda v: VERSIONS[v].name, key=f"{key}_v")
    case = st.selectbox("Message", cases, key=f"{key}_c",
                        format_func=lambda c: f"{c['id']} {_short(c['text'], 60)}")
    req = build_request(version, case["text"])

    c1, c2, c3 = st.columns(3)
    with c1.container(border=True):
        st.markdown("**🧱 System prompt**: same every call")
        st.code(req["system"], language=None)
        st.caption("Rules, labels and examples. Stable, so it goes FIRST: a repeated prefix can be cached.")
    with c2.container(border=True):
        st.markdown("**📨 Context**: changes every call")
        st.code(req["messages"][0]["content"], language=None)
        st.caption("This customer's message. You know before the call that it's needed.")
    with c3.container(border=True):
        st.markdown("**🔧 Tool**: fetched only when needed")
        st.code(TOOL_SKETCH, language="json")
        st.caption("Not used by this classifier. If a reply had to say *whether this customer gets a refund*, "
                   "that answer is private, changes over time, and is needed only sometimes: a tool, not the prompt.")

    if st.button("🔢 Count the tokens of each part (free)", key=f"{key}_count"):
        try:
            total = api.count_tokens(req["messages"][0]["content"], system=req["system"])
            context_only = api.count_tokens(req["messages"][0]["content"])
            st.session_state[f"{key}_tokens"] = (version, case["id"], total, context_only)
        except api.BackendError as e:
            st.error(str(e))
    counted = st.session_state.get(f"{key}_tokens")
    if counted and counted[:2] == (version, case["id"]):
        _, _, total, context_only = counted
        st.write(f"System prompt ≈ **{total - context_only}** tokens, paid on every call · "
                 f"context ≈ **{context_only}** tokens · total **{total}**.")

    st.markdown(
        "| Ask | Goes in | In this lab |\n|---|---|---|\n"
        "| Same every time, needed every time? | **System prompt** | labels, rules, examples |\n"
        "| Changes per request, known before the call? | **Context window** | the customer's message |\n"
        "| Needed only sometimes, too big, private or too fresh to preload? | **Tool call** | account / refund status |"
    )


# --- The page --------------------------------------------------------------
def prompt_lab(cfg: Dict[str, Any]) -> None:
    data = load_dataset()
    cases = data["cases"]
    runs, source = _saved_runs()

    with st.expander("🧒 Explain it like I'm 12: the whole lab in 6 steps", expanded=True):
        walkthrough.render(runs, cases)

    st.markdown(
        "**The method:** ① a fixed set of labelled messages → ② one prompt change per version → "
        "③ the same scoring code for every version → ④ Before vs After on the **same** messages. "
        "Then every claim is a number you can point at."
    )

    # Refuse to score a prompt that contains a scored message.
    leaks = {v: scoring.leakage(ver.examples, cases) for v, ver in VERSIONS.items()}
    leaks = {v: ids for v, ids in leaks.items() if ids}
    if leaks:
        st.error(f"Leakage: these test/prod messages appear as few-shot examples: {leaks}. "
                 "The score would measure memory, not the prompt. Use dev messages for examples.")
        return

    with st.expander("📏 The labeling policy and the message sets"):
        st.markdown("\n".join(f"- {p}" for p in data["policy"]))
        counts = pd.crosstab(pd.Series([c["split"] for c in cases], name="set"),
                             pd.Series([c["label"] for c in cases], name="label"))
        st.dataframe(counts.reindex(SPLITS))
        st.caption("dev: look at failures here to choose examples · test: held out, the headline number · "
                   "prod: messy, production-like input")

    _run_section(cfg, cases)

    st.divider()
    st.markdown("#### 2 · Compare saved runs (free)")
    runs, source = _saved_runs()  # again: a run just now may have added one
    if runs:
        _overview(runs)
        _showcase_controls(runs, source)
        st.download_button("📄 Download my case study (Markdown)", walkthrough.case_study(runs, cases),
                           file_name="prompt_lab_case_study.md", mime="text/markdown", key=f"{KEY}_case_study")
    if len(runs) >= 2:
        names = list(runs)
        c1, c2 = st.columns(2)
        b = c1.selectbox("Before", names, index=0, format_func=lambda v: VERSIONS[v].name, key=f"{KEY}_before")
        a = c2.selectbox("After", names, index=len(names) - 1,
                         format_func=lambda v: VERSIONS[v].name, key=f"{KEY}_after")

    tabs = st.tabs(["① What good looks like", "② Is it real?", "③ Test vs production", "④ Where info goes"])
    with tabs[3]:
        _tab_placement(cases)
    if len(runs) < 2:
        for t in tabs[:3]:
            t.info("Run at least two versions (start with **v1** and **v2**, then **v5**) to compare them here.")
        return

    with tabs[0]:
        _tab_before_after(runs[b], runs[a])
    with tabs[1]:
        _tab_is_it_real(runs[b], runs[a])
    with tabs[2]:
        _tab_production(runs, runs[a])
