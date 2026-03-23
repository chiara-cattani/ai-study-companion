"""
Onboarding flow: 3 steps — name, study goal, baseline symptoms.
"""

import streamlit as st
from datetime import date
from utils.state_manager import add_chat_message
from utils.persistence import save as _save

STUDY_GOALS = [
    "Improve digestion",
    "Reduce bloating",
    "Increase energy levels",
    "Manage IBS symptoms",
    "Improve gut health",
    "Support healthy weight",
    "Reduce inflammation",
    "Better sleep through nutrition",
]

BASELINE_SYMPTOMS = [
    "Bloating",
    "Gas",
    "Constipation",
    "Diarrhoea",
    "Abdominal pain",
    "Fatigue",
    "Acid reflux",
    "Nausea",
    "Brain fog",
    "Low energy",
]


def render_onboarding():
    # App hero
    st.markdown("""
    <div class="hero">
        <div class="hero-logo">🌿</div>
        <h1 class="hero-title">Study Companion AI</h1>
        <p class="hero-sub">Your personal AI guide for the nutrition study</p>
    </div>
    """, unsafe_allow_html=True)

    step = st.session_state.get("onboarding_step", 1)

    # Step indicator
    st.markdown(f"""
    <div class="step-bar">
        <div class="step-dot {'active' if step >= 1 else ''}">1</div>
        <div class="step-line {'done' if step > 1 else ''}"></div>
        <div class="step-dot {'active' if step >= 2 else ''}">2</div>
        <div class="step-line {'done' if step > 2 else ''}"></div>
        <div class="step-dot {'active' if step >= 3 else ''}">3</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    if step == 1:
        _step_name()
    elif step == 2:
        _step_goal()
    elif step == 3:
        _step_symptoms()


def _step_name():
    st.markdown("#### Step 1 of 3 — What's your name?")
    st.markdown('<p style="color:#4B5563;font-size:0.92rem;margin-top:-0.4rem">We\'ll use this to personalise your experience.</p>', unsafe_allow_html=True)

    name = st.text_input(
        "Your first name",
        placeholder="e.g. Sarah",
        key="input_name",
        label_visibility="collapsed",
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if st.button("Next →", type="primary", use_container_width=True):
        if name.strip():
            st.session_state.user_name = name.strip()
            st.session_state.onboarding_step = 2
            st.rerun()
        else:
            st.error("Please enter your name to continue.")


def _step_goal():
    st.markdown(f"#### Step 2 of 3 — Hi {st.session_state.user_name}! What's your main study goal?")
    st.markdown('<p style="color:#4B5563;font-size:0.92rem;margin-top:-0.4rem">This helps your AI coach tailor its guidance.</p>', unsafe_allow_html=True)

    goal = st.selectbox(
        "Study goal",
        STUDY_GOALS,
        label_visibility="collapsed",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state.onboarding_step = 1
            st.rerun()
    with col2:
        if st.button("Next →", type="primary", use_container_width=True):
            st.session_state.study_goal = goal
            st.session_state.onboarding_step = 3
            st.rerun()


def _step_symptoms():
    st.markdown("#### Step 3 of 3 — Any baseline symptoms?")
    st.markdown('<p style="color:#4B5563;font-size:0.92rem;margin-top:-0.4rem">Optional — helps us measure your improvement over time.</p>', unsafe_allow_html=True)

    symptoms = []
    cols = st.columns(2)
    for i, symptom in enumerate(BASELINE_SYMPTOMS):
        with cols[i % 2]:
            if st.checkbox(symptom, key=f"sym_{i}"):
                symptoms.append(symptom)

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state.onboarding_step = 2
            st.rerun()
    with col2:
        if st.button("Start my study ✓", type="primary", use_container_width=True):
            st.session_state.baseline_symptoms = symptoms
            st.session_state.onboarded = True
            st.session_state.study_start_date = date.today()
            st.session_state.current_page = "dashboard"

            # Seed initial chat greeting
            name = st.session_state.user_name
            goal = st.session_state.study_goal
            add_chat_message(
                "assistant",
                f"Hi {name}! I'm your Study Companion AI. "
                f"I'm here to support your goal to **{goal.lower()}**. "
                "Let's make this study a success together! What would you like to do today?",
            )
            _save(st.session_state)
            st.rerun()
