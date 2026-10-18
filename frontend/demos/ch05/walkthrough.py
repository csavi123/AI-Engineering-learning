"""The Prompt Lab explained like you're 12, in six steps you can click through.

Every step has the same three boxes:
  🧒 a plain-language explanation
  💻 the REAL code that does it (read from the files with `inspect`, so it can
     never drift from what actually runs)
  🎤 one line to say to an interviewer

Step 6 and the downloadable case study answer the four interview questions
from your saved runs, so every answer is a number you measured.
"""
import inspect
from datetime import date
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

from demos.ch05 import scoring
from demos.ch05.prompts import LABELS, VERSIONS, build_request, load_dataset

KEY = "ch05_walk"
CALLS_PER_DAY = 10_000  # used to make per-call costs feel real


def pct(x) -> str:
    return "—" if x is None else f"{x:.0%}"


# --- Numbers shared by step 6, the lab's tab ①, and the case study ----------
def pick_pair(runs: Dict[str, Dict[str, Any]]) -> Optional[Tuple[str, str]]:
    """The comparison to tell the story with: v2 → v5 if both exist.

    v2 → v5 isolates the few-shot change. v1 → v2 is mostly "add a contract",
    which is a huge but obvious jump.
    """
    with_test = [v for v in VERSIONS if v in runs and scoring.summary(runs[v], ["test"])["cases"]]
    if len(with_test) < 2:
        return None
    before = "v2" if "v2" in with_test and with_test[-1] != "v2" else with_test[0]
    after = "v5" if "v5" in with_test and before != "v5" else with_test[-1]
    return before, after


def headline(before: Dict[str, Any], after: Dict[str, Any]) -> str:
    """The 'what good looks like' sentence, built from two saved runs."""
    b, a = scoring.summary(before, ["test"]), scoring.summary(after, ["test"])
    bn, an = VERSIONS[before["version"]].name, VERSIONS[after["version"]].name
    pairs = scoring.paired(before, after, ["test"])
    diff, lo, hi = scoring.bootstrap_diff(pairs)
    fixed, broken = scoring.fixed_and_broken(pairs)
    extra_cost = (a["cost_per_call"] - b["cost_per_call"]) * CALLS_PER_DAY
    return (
        f"changing **{bn} → {an}** moved held-out accuracy from **{pct(b['accuracy'])} to "
        f"{pct(a['accuracy'])}** ({diff * 100:+.0f} pts, 95% interval {lo * 100:+.0f} to "
        f"{hi * 100:+.0f}) on the same {len(pairs)} test messages. It fixed {len(fixed)} and "
        f"broke {len(broken)}. Contract-valid outputs went {pct(b['valid'])} → {pct(a['valid'])}. "
        f"It adds {a['avg_input_tokens'] - b['avg_input_tokens']:+.0f} input tokens per call "
        f"({extra_cost:+.3f} USD per {CALLS_PER_DAY:,} calls)."
    )


def answers(runs: Dict[str, Dict[str, Any]]) -> Optional[List[Tuple[str, str]]]:
    """The four interview questions, each answered from your own runs."""
    pair = pick_pair(runs)
    if not pair:
        return None
    before, after = runs[pair[0]], runs[pair[1]]
    bn, an = VERSIONS[pair[0]].name, VERSIONS[pair[1]].name
    pairs = scoring.paired(before, after, ["test"])
    diff, lo, hi = scoring.bootstrap_diff(pairs)
    fixed, broken = scoring.fixed_and_broken(pairs)
    flips = scoring.summary(after, ["test"])["flip_rate"]

    luck = ("The whole interval is above zero, so it is very unlikely to be luck."
            if lo > 0 else "The interval crosses zero, so with this many messages I can't yet "
            "rule out luck; I'd add cases before shipping it.")
    noise = (f" Run-to-run noise: {pct(flips)} of messages changed label between repeats."
             if flips is not None else "")
    worse = _overcorrection(runs)
    q1 = (f"I don't read outputs and decide. I score a fixed, labelled set and compare on the "
          f"same messages. {bn} → {an} changed held-out accuracy by {diff * 100:+.0f} pts "
          f"(95% interval {lo * 100:+.0f} to {hi * 100:+.0f}). {luck}{noise} I also check which "
          f"messages moved: {len(fixed)} fixed, {len(broken)} broken, and whether any label got "
          f"worse.{worse}")

    t, p = scoring.summary(after, ["test"]), scoring.summary(after, ["prod"])
    prod_rows = [r for r in scoring.rows_in(after, ["prod"]) if not scoring.passes(r)]
    top = scoring.confusions(prod_rows).most_common(1)
    top_txt = (f" The biggest production failure was '{top[0][0][0]}' answered as '{top[0][0][1]}' "
               f"({scoring.failure_kind(top[0][0][1])} problem).") if top else ""
    gap = (f"{an} scores {pct(t['accuracy'])} on clean test messages and {pct(p['accuracy'])} on "
           f"messy production-like ones.{top_txt} " if p["cases"] else "")
    q2 = (f"{gap}My steps: reproduce with the real input; print the fully assembled prompt the "
          "model actually saw; name the failure: shape (invalid output), behaviour (valid but wrong) "
          "or difficulty (scattered); add the message to the eval set so it can't silently return; "
          "change one thing and re-measure on the same set.")

    tokens = scoring.summary(after)["avg_input_tokens"]
    q3 = (f"By how often it changes and who knows it's needed. The labels, rules and examples are "
          f"the same every call, so they're the system prompt, placed first so they can be cached "
          f"(about {tokens:.0f} input tokens per call in {an}, paid on every call). The customer's "
          "message changes per request, so it's the context. Anything private, live or needed only "
          "sometimes, like a customer's refund eligibility, would be a tool the model calls.")

    q4 = "A before/after on held-out data, with its uncertainty and its cost: " + headline(before, after)
    return [
        ("How do you know a prompt change actually improved the system?", q1),
        ("How would you debug a prompt that works in testing but fails in production?", q2),
        ("What goes in the system prompt vs the context window vs a tool call?", q3),
        ("What does good look like?", q4),
    ]


def _overcorrection(runs: Dict[str, Dict[str, Any]]) -> str:
    """One sentence about v4's overcorrection, if both v2 and v4 were run."""
    if "v2" not in runs or "v4" not in runs:
        return ""
    b = scoring.summary(runs["v2"], ["test"])["per_class"]
    a = scoring.summary(runs["v4"], ["test"])["per_class"]
    drops = [(lbl, b[lbl], a[lbl]) for lbl in a if lbl in b and a[lbl] < b[lbl] - 0.05]
    if not drops:
        return ""
    lbl, was, now = max(drops, key=lambda d: d[1] - d[2])
    return (f" Example: adding one example with no counter-example (v4) dropped '{lbl}' "
            f"accuracy from {pct(was)} to {pct(now)}, which the overall number hid.")


# --- The case study you can download ----------------------------------------
def case_study(runs: Dict[str, Dict[str, Any]], cases: List[Dict[str, Any]]) -> str:
    """A one-page Markdown write-up of the experiment, from your saved runs."""
    split_counts = {s: sum(c["split"] == s for c in cases) for s in ("dev", "test", "prod")}
    rows = ["| Version | The one change | Contract valid | Test acc | Prod acc | Input tokens/call |",
            "|---|---|---|---|---|---|"]
    for v, run in runs.items():
        every, t, p = scoring.summary(run), scoring.summary(run, ["test"]), scoring.summary(run, ["prod"])
        # "<message>" would vanish on GitHub, which hides unknown HTML tags.
        change = VERSIONS[v].change.replace("<", "&lt;")
        rows.append(f"| {VERSIONS[v].name} | {change} | {pct(every['valid'])} | "
                    f"{pct(t.get('accuracy'))} | {pct(p.get('accuracy'))} | {every['avg_input_tokens']:.0f} |")
    model = next(iter(runs.values()))["model"] if runs else "—"
    pair = pick_pair(runs)
    qa = answers(runs) or []
    lines = [
        "# Measuring a prompt change: support-ticket triage",
        f"*{date.today():%d %B %Y} · model `{model}`*",
        "",
        "## Problem",
        f"Classify customer messages into exactly one of: {', '.join(LABELS)}. "
        "Downstream code routes tickets on that label, so a wrong-but-plausible label is a silent routing error.",
        "",
        "## Method",
        f"- **Answer key first:** {len(cases)} messages labelled by a written policy before any prompt was tried.",
        f"- **Three sets:** dev ({split_counts['dev']}, used to choose examples), test ({split_counts['test']}, "
        f"held out: the headline number), prod ({split_counts['prod']}, messy production-like input).",
        "- **One change per version**, every version scored by the same code, compared on the same messages.",
        "- **Contract check:** an output counts only if it is exactly one allowed label.",
        "- **Is it real?** Paired bootstrap 95% interval on the accuracy change; fixed vs broken messages; per-label accuracy.",
        "- **Leakage check:** the lab refuses to run if a test/prod message appears in a prompt.",
        "",
        "## Results",
        *rows,
        "",
        *([f"**Headline:** {headline(runs[pair[0]], runs[pair[1]])}", ""] if pair else []),
        "## The four questions, answered from this experiment",
        *[f"**{q}**\n\n{a}\n" for q, a in qa],
        "## Limits and next steps",
        "- 28 test messages can only detect large changes; the interval is wide. Next: more labelled cases.",
        "- Labels come from one person's policy; a second labeller would measure agreement.",
        "- Shape is only *requested* here; structured output (constrained decoding) would guarantee it.",
        "- Code: `frontend/demos/ch05/` (prompts.py, scoring.py, lab.py).",
    ]
    return "\n".join(lines)


# --- The six steps -----------------------------------------------------------
def _step_job(runs, cases) -> None:
    examples = [c for c in cases if c["id"] in ("d01", "d02", "d03", "d07")]
    st.dataframe(pd.DataFrame([{"message": c["text"], "goes in box": c["label"]} for c in examples]),
                 hide_index=True, width="stretch")


def _step_answer_key(runs, cases) -> None:
    st.markdown("**The grading rule** (from `ch05_triage_cases.yaml`):")
    st.markdown("- " + "\n- ".join(load_dataset()["policy"][:4]))
    st.markdown("**How the code grades one answer:**")
    st.dataframe(pd.DataFrame([{"Claude said": repr(o), "counts as": scoring.parse_label(o) or "❌ broken answer"}
                               for o in ["bug", "Bug.", "Label: bug", "It's probably a bug"]]),
                 hide_index=True)


def _step_fair_test(runs, cases) -> None:
    st.dataframe(pd.DataFrame([
        {"set": "dev", "like": "📘 practice paper", "size": sum(c["split"] == "dev" for c in cases),
         "rule": "look at mistakes here, pick examples from here"},
        {"set": "test", "like": "📕 the real exam (sealed)", "size": sum(c["split"] == "test" for c in cases),
         "rule": "never copied into a prompt; the score that counts"},
        {"set": "prod", "like": "🌪️ the messy real world", "size": sum(c["split"] == "prod" for c in cases),
         "rule": "empty, forwarded, other languages, tricks"},
    ]), hide_index=True, width="stretch")
    st.dataframe(pd.DataFrame([{"version": v.name, "the ONE change": v.change} for v in VERSIONS.values()]),
                 hide_index=True, width="stretch")


def _step_run(runs, cases) -> None:
    req = build_request("v5", "Is the app supposed to freeze when I upload a photo?")
    c1, c2 = st.columns(2)
    with c1.container(border=True):
        st.markdown("**🧱 System prompt** = the rulebook (same every time)")
        st.code(req["system"], language=None)
    with c2.container(border=True):
        st.markdown("**📨 User message** = today's letter (changes every time)")
        st.code(req["messages"][0]["content"], language=None)


def _step_scoreboard(runs, cases) -> None:
    pair = pick_pair(runs)
    if not pair:
        st.info("Run at least two versions in the lab below (try v2 and v5) and this step fills in with your numbers.")
        return
    st.success("**From your own runs:** " + headline(runs[pair[0]], runs[pair[1]]))
    st.caption("Fixed / broken lists, the interval and per-label bars are in the lab's tabs ① and ② below.")


def _step_answers(runs, cases) -> None:
    qa = answers(runs)
    if not qa:
        st.info("Run at least two versions on the test set (v1, v2, v4, v5 tell the full story). "
                "Then these four answers write themselves from your numbers.")
        return
    for q, a in qa:
        with st.container(border=True):
            st.markdown(f"**❓ {q}**")
            st.markdown(a)


def _code(*objs: Callable) -> str:
    return "\n\n".join(inspect.getsource(o) for o in objs)


def _steps():
    from demos.ch05 import lab  # imported here: lab imports this module
    return [
        dict(
            title="The job",
            kid="Imagine a post office for an app's help desk. Letters arrive from customers, and "
                "a helper has to drop each one into **one of four boxes**: 🐞 something is broken "
                "(bug), 💡 they want something new (feature_request), ❓ they need help (question), "
                "or 🗑️ nothing to do (no_action). Claude is the helper. Our **prompt** is the "
                "instructions we give it. We want to find out which instructions make it sort best.",
            code=lambda: "LABELS = " + repr(LABELS),
            interview="The task has a contract: four labels, nothing else. Downstream code routes "
                      "tickets on that label, so a plausible wrong label is a silent bug.",
            extra=_step_job,
        ),
        dict(
            title="The answer key",
            kid="Before a teacher grades a test, she writes down the right answers. We did the same: "
                "**64 letters, each with its correct box written down first**, plus a rule for the "
                "tricky ones (\"a question about something broken is still a 🐞\"). Then grading is "
                "just checking, not opinion. And if Claude writes \"Label: bug\" instead of \"bug\", "
                "the computer that sorts the mail can't read it, so it counts as wrong.",
            code=lambda: _code(scoring.parse_label),
            interview="I wrote a labelling policy and the gold labels before trying any prompt, "
                      "so accuracy measures the prompt, not my opinion.",
            extra=_step_answer_key,
        ),
        dict(
            title="Fair-test rules",
            kid="Three rules make it a fair test, like a science experiment:\n\n"
                "1. **Same exam for everyone:** every prompt version gets the exact same letters.\n"
                "2. **Change one thing at a time:** v2 → v3 only adds one sentence; v2 → v5 only "
                "adds examples. So if the score moves, we know why.\n"
                "3. **A sealed exam paper:** we pick examples from the *practice* letters (dev), "
                "never the *exam* letters (test). Otherwise Claude would just be copying the answers. "
                "The code even checks this and refuses to run if it finds a copied letter.",
            code=lambda: _code(scoring.leakage),
            interview="It's a controlled experiment: same inputs, one variable changed per version, "
                      "and a held-out test set with an automatic leakage check.",
            extra=_step_fair_test,
        ),
        dict(
            title="Run the experiment",
            kid="For every letter, we send Claude two things: the **rulebook** (system prompt: the "
                "same every time) and **today's letter** (user message: different every time). We "
                "wrap the letter in `<message>` tags so if a letter says *\"ignore your rules\"*, "
                "Claude treats it as just words in a letter. We keep **every answer exactly as "
                "Claude wrote it**, so we can look at the mistakes later.",
            code=lambda: _code(build_request, lab._run),
            interview="Stable rules and examples go in the system prompt, first, so they can be "
                      "cached; the per-request message is delimited as data. I store raw outputs, "
                      "not just scores, so every failure is debuggable.",
            extra=_step_run,
        ),
        dict(
            title="Read the scoreboard",
            kid="Now we count. But a good scientist asks three more questions:\n\n"
                "- **Was it luck?** We reshuffle the results 2,000 times to see how much the score "
                "could wobble by chance. If even the wobbly range is above zero, it's a real win.\n"
                "- **Did we break something?** \"+3 overall\" could be *5 fixed and 2 broken*. So we "
                "list both.\n"
                "- **Did one box get worse?** v4 teaches \"questions can be bugs\" and Claude starts "
                "calling *every* question a bug. The total hides it; the per-box score shows it.",
            code=lambda: _code(scoring.case_score, scoring.fixed_and_broken, scoring.bootstrap_diff),
            interview="I compare on the same cases, report a bootstrap interval on the difference, "
                      "list fixed vs broken cases, and check per-class accuracy for regressions.",
            extra=_step_scoreboard,
        ),
        dict(
            title="Your four answers",
            kid="Here's the payoff. Every answer below is built from **your** runs. When an "
                "interviewer asks, you don't say \"I think it got better\". You say the number, "
                "how sure you are, what broke, and what it cost.",
            code=lambda: _code(headline),
            interview="Each answer below is evidence from my own experiment, not from memory.",
            extra=_step_answers,
        ),
    ]


def render(runs: Dict[str, Dict[str, Any]], cases: List[Dict[str, Any]]) -> None:
    steps = _steps()
    i = min(st.session_state.get(f"{KEY}_step", 0), len(steps) - 1)
    step = steps[i]

    st.progress((i + 1) / len(steps), text=f"Step {i + 1} of {len(steps)} · {step['title']}")
    with st.container(border=True):
        st.markdown("**🧒 Like you're 12**")
        st.markdown(step["kid"])
        step["extra"](runs, cases)
    with st.expander("💻 The real code that does it (read live from the file)"):
        st.code(step["code"](), language="python")
    st.info(f"**🎤 Say this to the interviewer:** {step['interview']}")

    c1, c2, c3 = st.columns([1, 3, 1])
    if c1.button("◀ Back", key=f"{KEY}_back", disabled=i == 0):
        st.session_state[f"{KEY}_step"] = i - 1
        st.rerun()
    if c3.button("Next ▶", key=f"{KEY}_next", disabled=i == len(steps) - 1):
        st.session_state[f"{KEY}_step"] = i + 1
        st.rerun()
