"""Shared building blocks so every experiment follows the same 4-part pattern:

    1. Prediction box  (write your guess BEFORE running)
    2. Run button
    3. Results / chart
    4. "What this shows" (only revealed after a run)

Why force a prediction first? Committing to a guess, then comparing it with
reality, is what makes a result stick.
"""
import json
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import streamlit as st

import store


def prediction_box(key: str, question: str) -> str:
    """Text area for your prediction. `key` must be unique per experiment."""
    return st.text_area(
        f"🔮 Prediction: {question}",
        key=f"{key}_prediction",
        placeholder="Write what you expect to happen before you click Run…",
    )


def run_button(key: str, label: str = "▶ Run") -> bool:
    """Run button that also remembers the experiment has been run.

    Streamlit reruns the whole script on every click, so we store "has run" in
    session_state; otherwise the explanation would vanish on the next click.
    """
    clicked = st.button(label, key=f"{key}_run", type="primary")
    if clicked:
        st.session_state[f"{key}_has_run"] = True
    return clicked


def has_run(key: str) -> bool:
    """True once you've run the experiment, now or in an earlier session."""
    return st.session_state.get(f"{key}_has_run", False) or store.load_run(key) is not None


def save_run(key: str, data: Any) -> None:
    """Keep a live result on disk, so looking at it again later costs nothing."""
    store.save_run(key, data)


def load_run(key: str) -> Optional[Any]:
    """Return the saved result for this experiment (or None), with a banner."""
    saved = store.load_run(key)
    if saved is None:
        return None
    when = datetime.fromisoformat(saved["saved_at"]).strftime("%d %b %Y, %H:%M")
    st.caption(
        f"📼 Saved run from {when}. Viewing it is free; clicking Run again makes new API calls."
    )
    return saved["data"]


def what_this_shows(key: str, explanation: str) -> None:
    """Reveal the explanation only after the experiment has run at least once."""
    if has_run(key):
        st.info(f"**What this shows**\n\n{explanation}")


def show_prediction_reminder(key: str) -> None:
    """Show your prediction next to the result so you can compare them."""
    guess = st.session_state.get(f"{key}_prediction", "").strip()
    if guess:
        st.caption(f"Your prediction was: _{guess}_")


def estimate_cost(cfg: Dict[str, Any], model: str, calls: int, in_tokens: int, out_tokens: int) -> float:
    """Rough cost of an experiment BEFORE running it, from config.yaml prices.

    in_tokens / out_tokens are typical per-call guesses; the real numbers are
    shown after the run.
    """
    m = cfg["models"][model]
    per_call = (in_tokens * m["input_price_per_mtok"] + out_tokens * m["output_price_per_mtok"]) / 1_000_000
    return calls * per_call


def estimated_calls_notice(n_calls: int, cap: int, est_cost: Optional[float] = None) -> bool:
    """Show how many API calls (and roughly what cost) an experiment will make.

    Returns False (and shows an error) if n_calls exceeds the cap, so the page
    can refuse to run.
    """
    if n_calls > cap:
        st.error(f"This would make {n_calls} API calls; the cap is {cap}. Lower it.")
        return False
    cost = f" · ≈ **${est_cost:.4f}**" if est_cost is not None else ""
    st.caption(f"📞 Running this makes **{n_calls}** API call(s){cost}.")
    return True


def result_metrics(result: Dict[str, Any]) -> None:
    """The standard row of numbers shown after any single call."""
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Input tokens", result["input_tokens"])
    c2.metric("Output tokens", result["output_tokens"])
    c3.metric("Stop reason", result["stop_reason"] or "—")
    c4.metric("Est. cost", f"${result['estimated_cost_usd']:.6f}")
    st.caption(f"Model: `{result['model']}`")


def coming_soon(stage: int) -> None:
    st.warning(f"🚧 This page is built in **stage {stage}**.")


def run_repeated(fn: Callable[[], Dict[str, Any]], n: int, label: str) -> List[Dict[str, Any]]:
    """Call `fn` n times with a progress bar; return the successful results.

    Calls run one after another (not in parallel) to stay under the API's
    requests-per-minute limit. A failed call is reported and skipped, so one
    hiccup doesn't throw away the other results.
    """
    results: List[Dict[str, Any]] = []
    bar = st.progress(0.0, text=label)
    errors = []
    for i in range(n):
        try:
            results.append(fn())
        except Exception as e:  # BackendError, but keep going on anything
            errors.append(str(e))
        bar.progress((i + 1) / n, text=f"{label} ({i + 1}/{n})")
    bar.empty()
    if errors:
        st.warning(f"{len(errors)} of {n} calls failed. First error: {errors[0]}")
    return results


def total_cost(results: List[Dict[str, Any]]) -> float:
    return sum(r["estimated_cost_usd"] for r in results)


def show_exchange(request: Dict[str, Any], result: Dict[str, Any]) -> None:
    """Show exactly what went in and what came out of one call.

    The model has no inspectable interior. The input and the output are the
    only things you can see, so a habit of logging both is how you debug.
    """
    with st.expander("🔍 Exactly what went in and what came out"):
        c1, c2 = st.columns(2)
        c1.markdown("**Request sent**")
        c1.code(json.dumps(request, indent=2, ensure_ascii=False), language="json")
        c2.markdown("**Response received**")
        c2.code(json.dumps(result, indent=2, ensure_ascii=False), language="json")


def show_token(token: str) -> str:
    """Make whitespace visible, so ' Paris' and 'Paris' look different."""
    return token.replace(" ", "·").replace("\n", "↵") if token else "∅"
