"""Draws a chapter's pages: one overview page, plus one page per lesson.

Each lesson is its own page (with its own link) and is opened from the
chapter's fold-out list in the sidebar. Showing a single lesson at a time
keeps every page short, which is the whole point: you should never feel lost.
"""
from typing import Any, Dict

import streamlit as st

import content
import lesson_card
import nav
import quiz


def render_overview(chap: Dict[str, Any]) -> None:
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

    first = lessons[0]
    st.page_link(nav.LESSON_PAGES[(chap["id"], first["id"])],
                 label=f"Start with {first['number']} · {first['title']} →", icon="📖")
    st.caption("All lessons are listed under this chapter in the sidebar.")


def render_lesson(chap: Dict[str, Any], lesson: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    st.caption(f"Chapter {chap['number']} · {chap['title']}")
    lesson_card.render(chap, lesson, cfg)
