"""Checks whether a DOI exists, using Crossref's free public API.

Crossref is the registry most academic papers' DOIs belong to. It needs no
key and costs nothing. This is not an Anthropic call.
"""
from typing import Dict

import requests
import streamlit as st


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def lookup(doi: str) -> Dict[str, str]:
    """Return {"status": "found" | "not found" | "error", "title": ...}.

    Cached for a day, so checking the same DOI twice doesn't re-ask Crossref.
    """
    try:
        r = requests.get(f"https://api.crossref.org/works/{doi}", timeout=10,
                         headers={"User-Agent": "AI-Engineering-Notebook/1.0"})
    except requests.RequestException as e:
        return {"status": "error", "title": f"Could not reach Crossref: {e.__class__.__name__}"}
    if r.status_code == 404:
        return {"status": "not found", "title": ""}
    if not r.ok:
        return {"status": "error", "title": f"Crossref returned HTTP {r.status_code}"}
    titles = r.json().get("message", {}).get("title") or [""]
    return {"status": "found", "title": titles[0]}
