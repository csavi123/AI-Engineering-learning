"""Holds the chapter and lesson page objects created in app.py.

Other pages (like Home) import this to link to chapters with st.page_link,
without importing app.py itself (which would re-run the whole app).
"""
from typing import Dict, Tuple

import streamlit as st

CHAPTER_PAGES: Dict[str, st.Page] = {}  # chapter id -> overview page
LESSON_PAGES: Dict[Tuple[str, str], st.Page] = {}  # (chapter id, lesson id) -> page
