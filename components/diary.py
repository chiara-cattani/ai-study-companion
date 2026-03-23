"""
Daily diary form and meal logger.
"""

import streamlit as st
from datetime import date, datetime
from utils.state_manager import save_diary_entry, save_meal_log
from utils.llm_client import get_diary_feedback, get_meal_feedback

SYMPTOMS = [
    "Bloating", "Gas", "Cramps", "Nausea",
    "Constipation", "Diarrhoea", "Fatigue", "Heartburn",
    "Low appetite", "Headache",
]

MOOD_MAP = {
    "😄 Great": 5,
    "🙂 Good": 4,
    "😐 Okay": 3,
    "😕 Not great": 2,
    "😞 Bad": 1,
}

SCORE_LABELS = {
    1: "😣 Very bad",
    2: "😕 Poor",
    3: "😐 Okay",
    4: "🙂 Good",
    5: "😄 Excellent",
}


# ── Daily Diary ────────────────────────────────────────────────────────────

def render_diary():
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("← Back"):
            st.session_state.current_page = "dashboard"
            st.rerun()
    with col2:
        st.markdown("## 📝 Daily Diary")

    today = date.today().isoformat()
    already_done = today in st.session_state.diary_entries

    if already_done and not st.session_state.get("edit_diary", False):
        _diary_done_view()
        return

    st.markdown(f"**{date.today().strftime('%A, %B %d, %Y')}**")
    st.caption("Takes about 2 minutes. Your data really matters.")
    st.markdown("---")

    # ── Digestion score
    st.markdown("#### How was your digestion today?")
    digestion_score = st.select_slider(
        "Digestion",
        options=[1, 2, 3, 4, 5],
        value=3,
        format_func=lambda x: SCORE_LABELS[x],
        label_visibility="collapsed",
    )

    st.markdown("---")

    # ── Symptoms
    st.markdown("#### Any symptoms? *(select all that apply)*")
    symptoms = []
    scols = st.columns(2)
    for i, s in enumerate(SYMPTOMS):
        with scols[i % 2]:
            if st.checkbox(s, key=f"ds_{i}"):
                symptoms.append(s)

    st.markdown("---")

    # ── Mood
    st.markdown("#### How's your mood?")
    mood = st.radio(
        "Mood",
        list(MOOD_MAP.keys()),
        horizontal=True,
        label_visibility="collapsed",
    )

    st.markdown("---")

    # ── Notes
    st.markdown("#### Anything else to note? *(optional)*")
    notes = st.text_area(
        "Notes",
        placeholder="e.g. Had a heavy lunch, slept poorly last night...",
        label_visibility="collapsed",
        height=80,
    )

    st.markdown("---")

    _, bcol = st.columns([1, 2])
    with bcol:
        if st.button("Submit Diary ✓", type="primary", use_container_width=True):
            entry = {
                "date": today,
                "digestion_score": digestion_score,
                "symptoms": symptoms,
                "mood": mood,
                "mood_score": MOOD_MAP[mood],
                "notes": notes,
            }
            save_diary_entry(entry)

            ctx = {"name": st.session_state.user_name, "goal": st.session_state.study_goal}
            provider = st.session_state.get("llm_provider", "demo")
            st.session_state.diary_feedback = get_diary_feedback(entry, ctx, provider)
            st.session_state.diary_submitted = True
            st.session_state.edit_diary = False
            st.rerun()


def _diary_done_view():
    entry = st.session_state.diary_entries.get(date.today().isoformat(), {})
    feedback = st.session_state.get("diary_feedback", "")

    st.markdown("""
    <div class="success-card">
        <div class="success-icon">✅</div>
        <h3>Diary submitted!</h3>
        <p>Thank you for completing today's entry.</p>
    </div>
    """, unsafe_allow_html=True)

    if feedback:
        st.markdown(f"""
        <div class="ai-fb-card">
            <span class="ai-fb-tag">🤖 AI Coach</span>
            <p>{feedback}</p>
        </div>
        """, unsafe_allow_html=True)

    if entry:
        st.markdown("#### Today's Summary")
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Digestion Score", f"{entry.get('digestion_score', '-')}/5")
        with c2:
            mood = entry.get("mood", "-")
            st.metric("Mood", mood.split(" ")[0] if mood else "-")

        syms = entry.get("symptoms", [])
        if syms:
            st.markdown(f"**Symptoms logged:** {', '.join(syms)}")
        else:
            st.markdown("**Symptoms:** None reported 🎉")

        if entry.get("notes"):
            st.markdown(f"**Notes:** _{entry['notes']}_")

    st.markdown("---")
    if st.button("Edit Entry", use_container_width=True):
        st.session_state.edit_diary = True
        st.rerun()


# ── Meal Logger ────────────────────────────────────────────────────────────

def render_meal_log():
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("← Back"):
            st.session_state.current_page = "dashboard"
            st.rerun()
    with col2:
        st.markdown("## 🍽️ Log a Meal")

    today = date.today().isoformat()
    today_meals = st.session_state.meal_logs.get(today, [])

    # Show previously logged meals
    if today_meals:
        st.markdown(f"**{len(today_meals)} meal(s) logged today:**")
        for meal in today_meals:
            st.markdown(f"""
            <div class="meal-card">
                <span class="meal-type">{meal.get('type', '')}</span>
                <span class="meal-desc">{meal.get('description', '')}</span>
                <span class="meal-time">{meal.get('time', '')}</span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("---")

    # Meal type
    st.markdown("#### What type of meal?")
    meal_type = st.radio(
        "Meal type",
        ["🌅 Breakfast", "☀️ Lunch", "🌙 Dinner", "🍎 Snack"],
        horizontal=True,
        label_visibility="collapsed",
    )

    # Description
    st.markdown("#### Describe what you ate:")
    meal_text = st.text_area(
        "Description",
        placeholder="e.g. Grilled salmon, mixed salad, glass of water...",
        label_visibility="collapsed",
        height=90,
    )

    # Photo upload
    st.markdown("#### Or upload a photo: *(optional)*")
    photo = st.file_uploader(
        "Meal photo",
        type=["jpg", "jpeg", "png", "webp"],
        label_visibility="collapsed",
    )
    if photo:
        st.image(photo, caption="Your meal photo", use_container_width=True)
        st.info("Photo received! AI food recognition is coming in a future update.")

    st.markdown("---")

    # AI feedback from previous log
    if st.session_state.get("meal_logged") and st.session_state.get("meal_feedback"):
        st.markdown(f"""
        <div class="ai-fb-card">
            <span class="ai-fb-tag">🤖 AI Coach</span>
            <p>{st.session_state.meal_feedback}</p>
        </div>
        """, unsafe_allow_html=True)
        st.session_state.meal_logged = False

    _, bcol = st.columns([1, 2])
    with bcol:
        if st.button("Log Meal ✓", type="primary", use_container_width=True):
            desc = meal_text.strip() or ("Photo upload" if photo else "")
            if desc:
                meal = {
                    "type": meal_type,
                    "description": desc,
                    "time": datetime.now().strftime("%H:%M"),
                    "has_photo": photo is not None,
                }
                save_meal_log(meal)

                ctx = {"name": st.session_state.user_name, "goal": st.session_state.study_goal}
                provider = st.session_state.get("llm_provider", "demo")
                st.session_state.meal_feedback = get_meal_feedback(desc, ctx, provider)
                st.session_state.meal_logged = True
                st.rerun()
            else:
                st.error("Please describe your meal or upload a photo.")
