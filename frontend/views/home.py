"""Home: the whole syllabus on one screen, plus a small setup check."""
import pandas as pd
import streamlit as st

import api
import content
import nav
import quiz

st.title("🧪 AI Engineering Notebook")
st.write(
    "Your visual companion to the course. Each chapter has a one-picture overview "
    "and a 60-second cheat sheet; each lesson has a core idea, a picture, key "
    "points, one demo and a quick quiz."
)

st.subheader("Syllabus")
cols = st.columns(3)
for i, entry in enumerate(content.syllabus()):
    chap = content.chapter(entry)
    with cols[i % 3].container(border=True):
        st.markdown(f"**{entry['number']} · {entry['title']}**")
        if chap is None:
            st.caption("Coming soon")
            continue
        ready = sum(1 for lesson in chap["lessons"] if lesson.get("status") == "ready")
        s = quiz.score(content.question_ids(chap))
        st.caption(f"{ready}/{len(chap['lessons'])} lesson cards · quiz {s['correct']}/{s['total']} correct")
        st.page_link(nav.CHAPTER_PAGES[entry["id"]], label="Open chapter →", icon="📖")

with st.expander("⚙️ Setup check"):
    try:
        health = api.health()
        cfg = api.get_config()
    except api.BackendError as e:
        st.error(str(e))
        st.stop()
    if health["api_key_configured"]:
        st.success("Backend is running and an API key is configured.")
    else:
        st.error("Backend is running, but ANTHROPIC_API_KEY is missing from .env.")
    st.write(
        f"**Default model:** `{cfg['default_model']}` · **Sampling model:** `{cfg['sampling_model']}` · "
        f"**Max repeated runs:** {cfg['max_repeated_runs']} · **Monthly budget:** ${cfg['monthly_budget_usd']:.2f}"
    )
    st.dataframe(pd.DataFrame([
        {
            "model": name,
            "input $/M tokens": m["input_price_per_mtok"],
            "output $/M tokens": m["output_price_per_mtok"],
            "context window": f"{m['context_window']:,}",
            "temperature/top_p/top_k": "yes" if m.get("supports_sampling_params") else "no",
            "prefill": "yes" if m.get("supports_prefill") else "no",
        }
        for name, m in cfg["models"].items()
    ]), hide_index=True)
