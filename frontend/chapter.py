"""Draws a chapter page: overview first, then one lesson at a time.

Showing a single lesson at a time (instead of everything stacked) keeps the
page short, which is the whole point: you should never feel lost.
"""
from typing import Any, Dict

import streamlit as st

import content
import lesson_card
import quiz


def render(chap: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    st.title(f"Chapter {chap['number']} · {chap['title']}")

    lessons = chap["lessons"]
    ready = sum(1 for lesson in lessons if lesson.get("status") == "ready")
    s = quiz.score(content.question_ids(chap))
    c1, c2 = st.columns(2)
    c1.metric("Lesson cards ready", f"{ready} / {len(lessons)}")
    c2.metric("Quiz: correct last time", f"{s['correct']} / {s['total']}")

    # The 60-second refresh: one picture + one line per lesson.
    with st.expander("🗺️ Chapter in one picture + 60-second cheat sheet", expanded=True):
        st.graphviz_chart(chap["picture"], width="stretch")
        for lesson in lessons:
            mark = "" if lesson.get("status") == "ready" else " 🚧"
            st.markdown(f"**{lesson['number']} · {lesson['title']}**{mark}  \n{lesson['one_liner']}")

    st.markdown("### Open a lesson")
    labels = {lesson["id"]: f"{lesson['number']} · {lesson['title']}" for lesson in lessons}
    chosen = st.radio(
        "Lesson", list(labels), format_func=labels.get, horizontal=True,
        key=f"{chap['id']}_lesson", label_visibility="collapsed",
    )
    st.divider()
    lesson = next(lesson for lesson in lessons if lesson["id"] == chosen)
    lesson_card.render(chap, lesson, cfg)
