"""Streamlit entry point: sidebar navigation for the whole app.

Run with:  streamlit run frontend/app.py

The sidebar lists only Home plus the chapters that are built, so it stays
short. The full 17-chapter map lives on the Home page.
"""
import sys
from pathlib import Path

import streamlit as st

# Make `import api`, `import ui`, etc. work from every page.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import api  # noqa: E402  (needs the sys.path line above)
import chapter  # noqa: E402
import content  # noqa: E402
import nav  # noqa: E402

st.set_page_config(page_title="AI Engineering Notebook", page_icon="🧪", layout="wide")

VIEWS = Path(__file__).resolve().parent / "views"


def chapter_page(entry):
    """One sidebar page per built chapter, all drawn by the same renderer."""
    def page():
        try:
            cfg = api.get_config()
        except api.BackendError as e:
            st.error(str(e))
            st.stop()
        chapter.render(content.chapter(entry), cfg)
    # Streamlit tells pages apart by function name, so give each a unique one.
    page.__name__ = f"chapter_{entry['id']}"
    st_page = st.Page(page, title=f"{entry['number']} · {entry['title']}", url_path=entry["id"])
    nav.CHAPTER_PAGES[entry["id"]] = st_page  # so Home can link to it
    return st_page


built = [c for c in content.syllabus() if c.get("content")]
pages = {
    "Start": [
        st.Page(VIEWS / "home.py", title="Home: syllabus map", icon="🗺️", default=True),
        st.Page(VIEWS / "quiz_me.py", title="Quiz me", icon="🎯"),
    ],
    "Chapters": [chapter_page(c) for c in built],
}

# Free hosting puts the backend to sleep when idle. Wake it once per visit,
# behind a spinner, so visitors see "waking up" instead of an error page.
if not st.session_state.get("backend_awake"):
    with st.spinner("Waking up the backend… free hosting naps when idle, so this can take up to a minute."):
        st.session_state["backend_awake"] = api.wait_for_backend()

# Running total, so spending is never a surprise.
with st.sidebar:
    try:
        s = api.spend()
        st.caption(f"💰 Spent this month: **${s['month_total_usd']:.4f}** of ${s['budget_usd']:.2f} budget")
    except api.BackendError:
        st.caption("💰 Spend unavailable (backend not running)")

st.navigation(pages).run()
