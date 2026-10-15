"""Draws one lesson in the same 6-part format every time:

    1. Core idea   2. Picture   3. Key points   4. Demo   5. Quiz   6. Go deeper

Keeping every lesson identical is deliberate: once you know the layout, any
lesson in any chapter can be scanned in a minute.
"""
from typing import Any, Dict

import streamlit as st

import demos
import quiz


def _demo(demo_id: str, cfg: Dict[str, Any]) -> None:
    demo = demos.get(demo_id)
    badge = "🆓 free" if demo.kind == "free" else "💲 live: costs only when you click Run"
    st.markdown(f"##### 🧪 {demo.title}  ·  <small>{badge}</small>", unsafe_allow_html=True)
    demo.fn(cfg)


def render(chap: Dict[str, Any], lesson: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    chapter_id = chap["id"]
    st.markdown(f"## {lesson['number']} · {lesson['title']}")
    if lesson.get("draft"):
        st.caption("📝 Draft: written from general knowledge, not your course text. "
                   "Paste the lesson in chat to align it with the course.")

    if lesson.get("status") != "ready":
        _coming(lesson, cfg)
        return
    if lesson.get("kind") == "prove_it":
        _prove_it(chap, lesson)
        return

    # 1. Core idea
    st.success(f"**💡 If you remember one thing:** {lesson['core_idea']}")

    # 2. Picture
    st.graphviz_chart(lesson["picture"], width="stretch")

    # 3. Key points
    st.markdown("\n".join(f"- {p}" for p in lesson["key_points"]))

    # 4. Demo
    st.divider()
    _demo(lesson["demo"], cfg)

    # 5. Quiz
    st.divider()
    st.markdown("#### 📝 Quick quiz")
    quiz.lesson_quiz(f"{chapter_id}/{lesson['id']}", lesson.get("quiz", []))

    # 6. Go deeper: off by default, so the lesson stays one screen. A toggle
    # (not an expander) because the demos inside use expanders themselves.
    deeper = lesson.get("deeper")
    if deeper:
        st.divider()
        if st.toggle("🔎 Go deeper: more notes and experiments", key=f"deeper_{chapter_id}_{lesson['id']}"):
            if deeper.get("notes"):
                st.markdown(deeper["notes"])
            ow = deeper.get("own_words")
            if ow:
                with st.container(border=True):
                    st.markdown(f"**✍️ In your own words:** {ow['q']}")
                    st.text_area("Your answer", key=f"ow_{chapter_id}_{lesson['id']}",
                                 label_visibility="collapsed", placeholder="Your answer…")
                    if st.checkbox("Show a model answer", key=f"owa_{chapter_id}_{lesson['id']}"):
                        st.info(ow["answer"])
            for demo_id in deeper.get("demos", []):
                st.divider()
                _demo(demo_id, cfg)

    if lesson.get("source"):
        st.caption(f"Source: {lesson['source']}")


def _coming(lesson: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    st.info(f"**Preview:** {lesson['one_liner']}")
    st.warning(
        "🚧 This card isn't built yet. Paste this lesson's text in the chat and "
        "it will get the full format: picture, key points, demo and quiz."
    )
    for demo_id in lesson.get("early_demos", []):
        st.caption("This lesson's demo is already available:")
        _demo(demo_id, cfg)


def _prove_it(chap: Dict[str, Any], lesson: Dict[str, Any]) -> None:
    st.success(f"**🏁 {lesson['core_idea']}**")
    st.markdown("**Can you, from memory…**")
    for i, item in enumerate(lesson.get("can_you", [])):
        st.checkbox(item, key=f"canyou_{chap['id']}_{i}")
    st.divider()
    st.markdown("#### 📝 Chapter quiz: 10 questions from every lesson")
    quiz.mixed_quiz(quiz.chapter_items(chap), key=f"chq_{chap['id']}", size=10)
    if lesson.get("source"):
        st.caption(f"Source: {lesson['source']}")
