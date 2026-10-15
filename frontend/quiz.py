"""Multiple-choice self-quiz with instant feedback. Free: no API calls.

The same question block is used in three places: each lesson's quick quiz,
the chapter quiz ("Prove it"), and the Quiz me review page. Every answer is
saved to data/progress.json, so scores survive restarts and Quiz me can
bring back the questions you got wrong.
"""
import random
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

import store

# (question id, question dict, lesson title)
Item = Tuple[str, Dict[str, Any], str]


def question(qid: str, q: Dict[str, Any], number: int, key_prefix: str = "quiz",
             source: Optional[str] = None) -> Optional[bool]:
    """Draw one question. Returns True/False once answered, None before.

    `key_prefix` lets the same question appear on two pages without clashing.
    """
    with st.container(border=True):
        choice = st.radio(f"**{number}. {q['q']}**", q["options"], index=None,
                          key=f"{key_prefix}_{qid}")
        if source:
            st.caption(f"From: {source}")
        if choice is None:
            return None
        correct = q["options"].index(choice) == q["answer"]
        # Streamlit reruns this code on every click, so record an answer only
        # when the selection changes; otherwise one answer would count many times.
        if st.session_state.get(f"{key_prefix}_{qid}_recorded") != choice:
            store.record_answer(qid, correct)
            st.session_state[f"{key_prefix}_{qid}_recorded"] = choice
        if correct:
            st.success(f"✅ Correct. {q['why']}")
        else:
            st.error(f"❌ Not quite. The answer is **{q['options'][q['answer']]}**. {q['why']}")
        return correct


def lesson_quiz(prefix: str, questions: List[Dict[str, Any]]) -> None:
    """A lesson's quick quiz. `prefix` is e.g. 'ch01/l01'."""
    for i, q in enumerate(questions, start=1):
        question(f"{prefix}/q{i}", q, i)


def chapter_items(chap: Dict[str, Any]) -> List[Item]:
    return [
        (f"{chap['id']}/{lesson['id']}/q{i}", q, f"{lesson['number']} · {lesson['title']}")
        for lesson in chap["lessons"]
        for i, q in enumerate(lesson.get("quiz", []), start=1)
    ]


def mixed_quiz(items: List[Item], key: str, size: int, pick=None) -> None:
    """A set of questions drawn from `items`, with a 'New set' button.

    `pick` chooses which questions to show (random by default). The chosen ids
    are kept in session_state so the set doesn't reshuffle on every click.
    """
    pick = pick or (lambda pool, n: random.sample(pool, min(n, len(pool))))
    by_id = {qid: (q, src) for qid, q, src in items}
    if st.button("🔀 New set of questions", key=f"{key}_new") or f"{key}_ids" not in st.session_state:
        st.session_state[f"{key}_ids"] = [qid for qid, _, _ in pick(items, size)]
        st.session_state[f"{key}_round"] = st.session_state.get(f"{key}_round", 0) + 1
    ids = [qid for qid in st.session_state[f"{key}_ids"] if qid in by_id]
    # A new round gets new widget keys, so the radio buttons start blank.
    prefix = f"{key}{st.session_state[f'{key}_round']}"
    results = [question(qid, by_id[qid][0], n, prefix, by_id[qid][1]) for n, qid in enumerate(ids, start=1)]
    answered = [r for r in results if r is not None]
    st.metric("Score this set", f"{sum(answered)} / {len(ids)}", f"{len(answered)} answered", delta_color="off")


def score(question_ids: List[str]) -> Dict[str, int]:
    """How many of these questions you answered correctly most recently."""
    progress = store.load_progress()
    answered = [progress[q] for q in question_ids if q in progress]
    return {
        "total": len(question_ids),
        "answered": len(answered),
        "correct": sum(1 for a in answered if a.get("last_correct")),
    }


def review_first(items: List[Item], n: int) -> List[Item]:
    """Pick for review: wrong last time first, then never answered, then the rest."""
    progress = store.load_progress()

    def priority(item: Item) -> int:
        p = progress.get(item[0])
        if p is None:
            return 1
        return 0 if not p.get("last_correct") else 2

    shuffled = random.sample(items, len(items))  # random order within each group
    return sorted(shuffled, key=priority)[:n]
