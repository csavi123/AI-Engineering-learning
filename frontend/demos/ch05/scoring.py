"""Turns saved Prompt Lab runs into numbers. Pure Python: no Streamlit, no API.

A saved run looks like:

    {"version": "v5", "system": "...", "model": "...", "repeats": 3,
     "rows": [{"id": "t04", "split": "test", "tag": "boundary", "gold": "bug",
               "text": "...", "outputs": ["bug", "bug", "question"],
               "input_tokens": [412, 412, 412], "output_tokens": [3, 3, 3],
               "cost": 0.00012}, ...]}

Words used below:
  call   one API request; a case run with 3 repeats is 3 calls
  valid  the output is exactly one allowed label (the contract held)
  score  of a case: the share of its calls that were correct (0..1)
  passes a case passes when most of its calls were correct
"""
import random
import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Tuple

from demos.ch05.prompts import LABELS

INVALID = "(invalid)"  # how a contract-breaking output shows up in tables


# --- The contract check ----------------------------------------------------
def parse_label(output: str) -> Optional[str]:
    """The label if the output honours the contract, else None.

    Contract-identical, not byte-identical: "Bug." and " bug\\n" are fine
    (trim spaces, quotes, a trailing full stop, case). "Label: bug",
    "This is a bug." or "very high" are not: code that expects one of four
    words would have to guess, and guessing is how routing errors start.
    """
    s = output.strip().strip("`'\"").strip().rstrip(".!").strip().lower()
    return s if s in LABELS else None


def predictions(row: Dict[str, Any]) -> List[str]:
    """Each call's label, with INVALID where the contract broke."""
    return [parse_label(o) or INVALID for o in row["outputs"]]


# --- Per-case numbers ------------------------------------------------------
def case_score(row: Dict[str, Any]) -> float:
    preds = predictions(row)
    return sum(p == row["gold"] for p in preds) / len(preds)


def majority(row: Dict[str, Any]) -> str:
    """The answer this case gives most often (first seen wins a tie)."""
    return Counter(predictions(row)).most_common(1)[0][0]


def passes(row: Dict[str, Any]) -> bool:
    return case_score(row) > 0.5


def flipped(row: Dict[str, Any]) -> bool:
    """Same prompt, same input, different answers across repeats?"""
    return len(set(predictions(row))) > 1


# --- Whole-run summary -----------------------------------------------------
def rows_in(run: Dict[str, Any], splits: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
    splits = set(splits) if splits else None
    return [r for r in run["rows"] if r["outputs"] and (splits is None or r["split"] in splits)]


def summary(run: Dict[str, Any], splits: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    """The headline numbers for one run, optionally for some splits only."""
    rows = rows_in(run, splits)
    if not rows:
        return {"cases": 0}
    calls = [(p, r["gold"]) for r in rows for p in predictions(r)]
    in_tok = [t for r in rows for t in r["input_tokens"]]
    out_tok = [t for r in rows for t in r["output_tokens"]]
    return {
        "cases": len(rows),
        "calls": len(calls),
        "valid": sum(p != INVALID for p, _ in calls) / len(calls),
        "accuracy": sum(case_score(r) for r in rows) / len(rows),
        "per_class": per_class(rows),
        # Noise only exists with repeats; one call per case can't flip.
        "flip_rate": (sum(flipped(r) for r in rows) / len(rows)) if run.get("repeats", 1) > 1 else None,
        "avg_input_tokens": sum(in_tok) / len(in_tok) if in_tok else 0,
        "avg_output_tokens": sum(out_tok) / len(out_tok) if out_tok else 0,
        "cost_per_call": sum(r["cost"] for r in rows) / len(calls),
    }


def per_class(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    """Accuracy for each correct label. A fix for one class can hide a
    drop in another; the overall number alone would never show it."""
    out = {}
    for label in LABELS:
        mine = [r for r in rows if r["gold"] == label]
        if mine:
            out[label] = sum(case_score(r) for r in mine) / len(mine)
    return out


def confusions(rows: List[Dict[str, Any]]) -> Counter:
    """(correct label, what the model said) for every wrong call."""
    return Counter((r["gold"], p) for r in rows for p in predictions(r) if p != r["gold"])


def failure_kind(pred: str) -> str:
    """Which of the guide's three sources a wrong answer points to.

    An invalid output is a SHAPE problem (fix: contract / structured output).
    A valid but wrong label is a BEHAVIOUR problem (fix: rule or examples).
    Scattered failures with no single pattern would hint at DIFFICULTY.
    """
    return "shape" if pred == INVALID else "behaviour"


# --- Comparing two runs ----------------------------------------------------
def paired(before: Dict[str, Any], after: Dict[str, Any],
           splits: Optional[Iterable[str]] = None) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """(before row, after row) for every case present in both runs.

    Comparing the SAME cases is what makes the difference meaningful: a score
    on different inputs would mix the prompt's effect with the inputs' effect.
    """
    b = {r["id"]: r for r in rows_in(before, splits)}
    return [(b[r["id"]], r) for r in rows_in(after, splits) if r["id"] in b]


def fixed_and_broken(pairs) -> Tuple[List, List]:
    fixed = [(b, a) for b, a in pairs if not passes(b) and passes(a)]
    broken = [(b, a) for b, a in pairs if passes(b) and not passes(a)]
    return fixed, broken


def bootstrap_diff(pairs, n: int = 2000, seed: int = 0) -> Tuple[float, float, float]:
    """Accuracy change (after - before) with a 95% interval.

    Resample the cases with replacement many times and recompute the change
    each time. If 95% of those changes are above zero, the improvement is
    unlikely to be luck in which cases happened to be in the set. With ~30
    cases the interval is wide, which is itself the lesson: small eval sets
    can only detect big changes.
    """
    diffs = [case_score(a) - case_score(b) for b, a in pairs]
    if not diffs:
        return 0.0, 0.0, 0.0
    rng = random.Random(seed)  # fixed seed: same data, same interval
    k = len(diffs)
    samples = sorted(sum(rng.choice(diffs) for _ in range(k)) / k for _ in range(n))
    return sum(diffs) / k, samples[int(0.025 * n)], samples[int(0.975 * n) - 1]


# --- Keeping the test set honest -------------------------------------------
def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def leakage(examples: List[Tuple[str, str]], cases: List[Dict[str, Any]]) -> List[str]:
    """Ids of test/prod cases that also appear as a few-shot example.

    If a scored case is in the prompt, the model is shown the answer, and
    the score measures memory, not the prompt. Dev cases are allowed: that
    split exists to be looked at.
    """
    seen = {_norm(text) for text, _ in examples}
    return [c["id"] for c in cases if c["split"] != "dev" and _norm(c["text"]) in seen]
