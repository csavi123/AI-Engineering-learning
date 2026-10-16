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


def chapter_pages(entry):
    """A built chapter's pages: its overview first, then one page per lesson.

    Each lesson gets its own page (and link, e.g. /ch01-l03) so it can be
    opened from the sidebar or shared directly.
    """
    chap = content.chapter(entry)

    def overview():
        chapter.render_overview(chap)
    # Streamlit tells pages apart by function name, so give each a unique one.
    overview.__name__ = f"chapter_{entry['id']}"
    overview_page = st.Page(overview, title="Overview & cheat sheet", icon="🗺️",
                            url_path=entry["id"])
    nav.CHAPTER_PAGES[entry["id"]] = overview_page  # so Home can link to it

    result = [overview_page]
    for lesson in chap["lessons"]:
        def lesson_page(lesson=lesson):  # lesson=lesson: bind THIS loop's lesson
            try:
                cfg = api.get_config()
            except api.BackendError as e:
                st.error(str(e))
                st.stop()
            chapter.render_lesson(chap, lesson, cfg)
        lesson_page.__name__ = f"lesson_{entry['id']}_{lesson['id']}"
        page = st.Page(lesson_page, title=f"{lesson['number']} · {lesson['title']}",
                       url_path=f"{entry['id']}-{lesson['id']}".replace("_", "-"))
        nav.LESSON_PAGES[(entry["id"], lesson["id"])] = page
        result.append(page)
    return result


home_page = st.Page(VIEWS / "home.py", title="Home: syllabus map", icon="🗺️", default=True)
quiz_page = st.Page(VIEWS / "quiz_me.py", title="Quiz me", icon="🎯")
built = [c for c in content.syllabus() if c.get("content")]
pages_by_chapter = {c["id"]: chapter_pages(c) for c in built}

# Streamlit's own sidebar menu can't fold sections, so hide it and draw our
# own below: one fold-out box per chapter, with its lessons inside.
current = st.navigation(
    [home_page, quiz_page] + [p for ps in pages_by_chapter.values() for p in ps],
    position="hidden",
)

# Free hosting puts the backend to sleep when idle. Wake it once per visit,
# behind a spinner, so visitors see "waking up" instead of an error page.
if not st.session_state.get("backend_awake"):
    with st.spinner("Waking up the backend… free hosting naps when idle, so this can take up to a minute."):
        st.session_state["backend_awake"] = api.wait_for_backend()

with st.sidebar:
    st.caption("Start")
    st.page_link(home_page)
    st.page_link(quiz_page)

    st.caption("Chapters")
    for entry in built:
        chap_pages = pages_by_chapter[entry["id"]]
        # Unfold only the chapter you're in, so the sidebar stays short.
        here = any(p.url_path == current.url_path for p in chap_pages)
        with st.expander(f"{entry['number']} · {entry['title']}", expanded=here):
            for p in chap_pages:
                st.page_link(p)

    st.divider()
    # Running total, so spending is never a surprise.
    try:
        s = api.spend()
        # "\\$": a bare "$...$" pair would be drawn as a math formula.
        st.caption(f"💰 Spent this month: **\\${s['month_total_usd']:.4f}** of \\${s['budget_usd']:.2f} budget")
    except api.BackendError:
        st.caption("💰 Spend unavailable (backend not running)")

current.run()
