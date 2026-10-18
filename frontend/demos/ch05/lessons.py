"""Free demos for the chapter 5 lesson cards. None of these call Claude;
prompt_cost uses the free token-counting endpoint only."""
from typing import Any, Dict

import pandas as pd
import streamlit as st

import api
from demos.ch05 import lab, scoring
from demos.ch05.prompts import VERSIONS, build_request, load_dataset, user_message


# --- Lesson 01 -------------------------------------------------------------
SAMPLE_OUTPUTS = "bug\nBug.\n  bug  \nBUG\nLabel: bug\nThis looks like a bug.\nbugs\nvery high"


def contract_checker(cfg: Dict[str, Any]) -> None:
    st.write("Your code expects exactly one of: "
             + ", ".join(f"`{lbl}`" for lbl in scoring.LABELS)
             + ". Paste model outputs, one per line. Which ones can the code use?")
    text = st.text_area("Model outputs", SAMPLE_OUTPUTS, height=190, key="ch05_contract_text")
    lines = text.split("\n")
    first = lines[0] if lines else ""
    st.dataframe(pd.DataFrame([{
        "output": repr(line),
        f"byte-identical to {first!r}": "✅" if line == first else "—",
        "contract-valid": "✅" if scoring.parse_label(line) else "❌",
        "label the code gets": scoring.parse_label(line) or "(none: code must guess)",
    } for line in lines]), hide_index=True, width="stretch")
    st.info("**What this shows:** most rows are byte-different from the first one yet still "
            "contract-valid, and production only needs that. `Label: bug` and `bugs` look "
            "almost right but break the contract, and nothing crashes: your code just has "
            "no label. This exact check (`scoring.parse_label`) scores every run in the "
            "Prompt Lab.")


# --- Lesson 02 -------------------------------------------------------------
def prompt_versions(cfg: Dict[str, Any]) -> None:
    st.dataframe(pd.DataFrame([{"version": v.name, "the one change": v.change, "meant to fix": v.targets}
                               for v in VERSIONS.values()]), hide_index=True, width="stretch")
    version = st.radio("Show version", list(VERSIONS), index=4, horizontal=True,
                       format_func=lambda v: VERSIONS[v].name, key="ch05_versions_pick")
    base = dict(VERSIONS["v2"].blocks)
    for name, text in VERSIONS[version].blocks:
        same = version != "v1" and base.get(name) == text
        st.markdown(f"**{name}** · " + ("same as v2" if same else "➕ **new in this version**"))
        st.code(text, language=None)
    st.caption("Plus the user turn, e.g.:")
    st.code(user_message(version, "Is the app supposed to freeze when I upload a photo?"), language=None)
    st.info("**What to notice:** v4 and v5 both add examples, but v4 shows only the "
            "question-shaped bug. With no counter-example, the model can learn "
            "'question-shaped means bug', and **question** accuracy drops. v5's two "
            "counter-examples pin the boundary from both sides. All examples come "
            "from the dev set, never from test. Run v4 and v5 in the Prompt Lab and "
            "look at tab ② to see it in numbers.")


# --- Lesson 03 -------------------------------------------------------------
CONTRACT = {
    1: "The buyer pays each invoice within 30 days.",
    2: "The supplier delivers within 10 working days of an order.",
    3: "The supplier's total liability is capped at the fees paid in the last month.",
    4: "Either party may end this agreement with 90 days' written notice.",
    5: "The supplier may end this agreement immediately if any invoice is 5 days late.",
    6: "Both parties keep the other's information confidential.",
}

ONE_SHOT = {
    "risk": "high",
    "clauses": [5, 9],
    "justification": "Clause 9 stops the buyer ending the agreement early, and clause 5 lets the supplier leave at once.",
}

# Step 1 output: what the extraction call returned. Row 5 is invented on purpose.
EXTRACTED = [
    (1, "The buyer pays each invoice within 30 days.", "payment"),
    (3, "The supplier's total liability is capped at the fees paid in the last month.", "liability"),
    (4, "Either party may end this agreement with 90 days' written notice.", "termination"),
    (5, "The supplier may end this agreement immediately if any invoice is 5 days late.", "termination"),
    (9, "The buyer may not end this agreement early.", "termination"),
]

# Step 2 output: the reasoning call's verdict per clause (risk for the buyer).
REASONING = {
    1: ("low", "Standard 30-day payment terms."),
    3: ("high", "A one-month fee cap leaves the buyer mostly unprotected."),
    4: ("low", "Mutual, with long notice."),
    5: ("high", "One invoice 5 days late lets the supplier walk away at once."),
}


def _verified(number: Any, text: str) -> bool:
    """The check only decomposition makes possible: is the quote really in the contract?"""
    try:
        return str(text).strip() in CONTRACT.get(int(number), "")
    except (TypeError, ValueError):
        return False


def decomposition_checker(cfg: Dict[str, Any]) -> None:
    st.caption("Pre-written outputs: nothing here calls Claude.")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**The contract**")
        st.markdown("\n".join(f"{n}. {t}" for n, t in CONTRACT.items()))
    with c2:
        st.markdown("**One-shot prompt** (find, judge and format in one call)")
        st.json(ONE_SHOT)
        st.error("Clause 9 doesn't exist, but nothing flags it, and you can't tell "
                 "which part (finding or judging) went wrong.")

    st.markdown("**Decomposed: ① Extract** (quote clauses verbatim, no judging). "
                "Edit any cell to see the check react.")
    rows = st.data_editor(
        pd.DataFrame(EXTRACTED, columns=["clause_number", "clause_text_verbatim", "category"]),
        hide_index=True, width="stretch", key="ch05_decomp_extract")
    rows["really in the contract?"] = ["✅" if _verified(n, t) else "❌ dropped"
                                       for n, t in zip(rows["clause_number"], rows["clause_text_verbatim"])]
    st.dataframe(rows[["clause_number", "really in the contract?"]], hide_index=True)

    st.markdown("**② Reason** (judges only the verified clauses, not the whole contract)")
    checked = [int(n) for n, t in zip(rows["clause_number"], rows["clause_text_verbatim"]) if _verified(n, t)]
    verdicts = {n: REASONING.get(n, ("low", "(no pre-written verdict for this clause in the demo)"))
                for n in checked}
    st.dataframe(pd.DataFrame([{"clause": n, "risk": r, "why": why} for n, (r, why) in verdicts.items()]),
                 hide_index=True, width="stretch")

    st.markdown("**③ Format** (plain Python, no model call)")
    high = [n for n, (r, _) in verdicts.items() if r == "high"]
    st.json({
        "risk": "high" if high else "low",
        "clauses": high,
        "justification": " ".join(verdicts[n][1] for n in high) or "No high-risk clauses found.",
    })
    st.info("**What this shows:** the invented clause 9 is caught by a one-line code check "
            "after step ①, before any judging happens. When the final answer is wrong, you can "
            "look at the in-between tables and see which step failed. The price: up to 2 model "
            "calls plus code instead of 1 call, so more latency, tokens and code to maintain.")


# --- Lesson 04 -------------------------------------------------------------
SORTER = [
    ("Reply with one of four labels only", "System prompt", "Same rule every call."),
    ("The customer's message", "Context window", "Changes every request, known before the call."),
    ("This customer's current account balance", "Tool call", "Private and changes over time: fetch it fresh."),
    ("Three boundary examples", "System prompt", "Stable, needed every call, and cacheable."),
    ("The last five turns of this conversation", "Context window", "Per request, and you know you need it."),
    ("Whether this order has shipped yet", "Tool call", "Live data, needed only for some messages."),
    ("Help articles retrieved for this question", "Context window", "Your app picks them before the call (retrieval)."),
]


def prompt_inspector(cfg: Dict[str, Any]) -> None:
    lab._tab_placement(load_dataset()["cases"], key="ch05_l04_place")
    st.markdown("##### Where does it go?")
    places = ["System prompt", "Context window", "Tool call"]
    for i, (item, answer, why) in enumerate(SORTER):
        c1, c2 = st.columns([3, 2])
        pick = c1.selectbox(item, places, index=None, key=f"ch05_sort_{i}", placeholder="Choose…")
        if pick:
            (c2.success if pick == answer else c2.error)(
                f"{'✅' if pick == answer else '❌ ' + answer + '.'} {why}")


# --- Lesson 05 -------------------------------------------------------------
def prompt_cost(cfg: Dict[str, Any]) -> None:
    st.caption("🆓 Free: uses Anthropic's token *counting* endpoint. Nothing is generated or billed.")
    model = cfg["default_model"]
    price = cfg["models"][model]["input_price_per_mtok"]
    calls = st.select_slider("Calls per day", [1_000, 10_000, 100_000], value=10_000, key="ch05_cost_calls")
    sample = "Is the app supposed to freeze when I upload a photo?"

    if st.button("🔢 Count tokens for every version (free)", key="ch05_cost_count", type="primary"):
        try:
            counts = {}
            for v in VERSIONS:
                req = build_request(v, sample)
                counts[v] = api.count_tokens(req["messages"][0]["content"], model=model, system=req["system"])
            st.session_state["ch05_cost_counts"] = counts
        except api.BackendError as e:
            st.error(str(e))

    counts = st.session_state.get("ch05_cost_counts")
    if not counts:
        return
    base = counts["v2"]
    df = pd.DataFrame([{
        "version": VERSIONS[v].name,
        "input tokens per call": n,
        "extra vs v2": n - base,
        "USD per day (input)": round(n * calls * price / 1_000_000, 3),
        "USD per 30 days": round(n * calls * price * 30 / 1_000_000, 2),
    } for v, n in counts.items()])
    st.dataframe(df, hide_index=True, width="stretch")
    st.bar_chart(df.set_index("version")["input tokens per call"], horizontal=True)
    st.info(f"**What this shows:** v5's examples add **{counts['v5'] - base} tokens to every call**, "
            f"easy messages included. At {calls:,} calls a day that's "
            f"{(counts['v5'] - base) * calls:,} extra input tokens daily. So the question is never "
            "'do examples help?' but 'do they buy more accuracy than they cost?' The Prompt Lab "
            "answers that: put the accuracy gain from tab ① next to this number.")
