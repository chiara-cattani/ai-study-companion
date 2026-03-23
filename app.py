import streamlit as st
import os
from pathlib import Path

st.set_page_config(
    page_title="Study Companion AI",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="collapsed",
)


def load_css():
    css_path = Path(__file__).parent / "assets" / "styles.css"
    if css_path.exists():
        with open(css_path, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


load_css()

# Inject JS to colour radio buttons green when selected.
# CSS alone cannot reach BaseWeb's dynamically-rendered circle.
import streamlit.components.v1 as components
components.html("""
<script>
(function() {
    function applyRadioStyles() {
        var doc = window.parent.document;
        doc.querySelectorAll('.stRadio label').forEach(function(label) {
            var input = label.querySelector('input[type="radio"]');
            if (!input) return;
            // Find the visual circle — first <div> or <span> inside the label
            var circle = label.querySelector('div > div, span > span, div');
            if (!circle) return;
            if (input.checked) {
                circle.style.setProperty('background', '#4CAF82', 'important');
                circle.style.setProperty('border-color', '#4CAF82', 'important');
                circle.style.setProperty('outline', '2px solid #4CAF82', 'important');
            } else {
                circle.style.removeProperty('background');
                circle.style.removeProperty('border-color');
                circle.style.removeProperty('outline');
            }
        });
    }
    // Run once on load, then watch for any DOM/attribute changes
    applyRadioStyles();
    var observer = new MutationObserver(applyRadioStyles);
    observer.observe(window.parent.document.body, {
        subtree: true, childList: true, attributes: true, attributeFilter: ['aria-checked']
    });
})();
</script>
""", height=0)

from utils.persistence import load as _load_data, delete as _delete_data  # noqa: E402
from utils.state_manager import init_session_state  # noqa: E402

# Restore persisted data once per session (before init fills in defaults)
if not st.session_state.get("_data_loaded"):
    _load_data(st.session_state)
    st.session_state["_data_loaded"] = True

init_session_state()

# Restore page from URL on refresh, then keep URL in sync
_qp = st.query_params.get("p", "")
if _qp and not st.session_state.get("_page_synced"):
    if st.session_state.get("onboarded"):
        st.session_state.current_page = _qp
    st.session_state["_page_synced"] = True

if st.session_state.get("onboarded"):
    st.query_params["p"] = st.session_state.get("current_page", "dashboard")

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Settings")

    demo_on = st.toggle("Demo Mode (no API key needed)", value=st.session_state.get("demo_mode", True))
    st.session_state.demo_mode = demo_on

    if demo_on:
        st.session_state.llm_provider = "demo"
        st.info("Running in Demo Mode — simulated AI responses.")
    else:
        provider = st.selectbox("AI Provider", ["openai", "anthropic"])
        st.session_state.llm_provider = provider

        if provider == "openai":
            key = st.text_input(
                "OpenAI API Key",
                type="password",
                value=os.getenv("OPENAI_API_KEY", ""),
                placeholder="sk-...",
            )
            if key:
                os.environ["OPENAI_API_KEY"] = key
        else:
            key = st.text_input(
                "Anthropic API Key",
                type="password",
                value=os.getenv("ANTHROPIC_API_KEY", ""),
                placeholder="sk-ant-...",
            )
            if key:
                os.environ["ANTHROPIC_API_KEY"] = key

    st.markdown("---")

    if st.session_state.get("onboarded"):
        st.markdown(f"**Participant:** {st.session_state.user_name}")
        st.markdown(f"**Goal:** {st.session_state.study_goal}")
        if st.session_state.get("baseline_symptoms"):
            st.markdown(f"**Baseline:** {', '.join(st.session_state.baseline_symptoms)}")

        st.markdown("---")

        if st.button("Reset / New Session", use_container_width=True):
            _delete_data()
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    st.markdown("---")
    st.caption("Study Companion AI v1.0 — For research demonstration only.")

# ── Routing ────────────────────────────────────────────────────────────────
page = st.session_state.get("current_page", "onboarding")

if not st.session_state.get("onboarded"):
    from components.onboarding import render_onboarding
    render_onboarding()

elif page == "dashboard":
    from components.dashboard import render_dashboard
    render_dashboard()

elif page == "chat":
    from components.chatbot import render_chatbot
    render_chatbot()

elif page == "diary":
    from components.diary import render_diary
    render_diary()

elif page == "meal_log":
    from components.diary import render_meal_log
    render_meal_log()

elif page == "progress":
    from components.dashboard import render_progress
    render_progress()

else:
    from components.dashboard import render_dashboard
    render_dashboard()
