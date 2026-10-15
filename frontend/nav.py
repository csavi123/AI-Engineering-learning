"""Holds the chapter page objects created in app.py.

Other pages (like Home) import this to link to chapters with st.page_link,
without importing app.py itself (which would re-run the whole app).
"""
from typing import Dict

import streamlit as st

CHAPTER_PAGES: Dict[str, st.Page] = {}
