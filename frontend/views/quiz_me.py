"""Quiz me: spaced review across every built chapter. Free: no API calls.

Questions you got wrong last time come first, then ones you've never seen,
then the ones you already know.
"""
import streamlit as st

import content
import quiz

st.title("🎯 Quiz me")
st.write("Mixed questions from every chapter you've studied. **Wrong last time → shown first.**")

items = []
for entry in content.syllabus():
    chap = content.chapter(entry)
    if chap:
        items += quiz.chapter_items(chap)

if not items:
    st.info("No quiz questions yet.")
    st.stop()

s = quiz.score([qid for qid, _, _ in items])
c1, c2, c3 = st.columns(3)
c1.metric("Questions in the bank", s["total"])
c2.metric("Answered at least once", s["answered"])
c3.metric("Correct last time", s["correct"])

quiz.mixed_quiz(items, key="quizme", size=5, pick=quiz.review_first)
