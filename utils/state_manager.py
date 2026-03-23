"""
Session state initialisation and helper functions.
All study data lives in st.session_state for this prototype.
"""

import streamlit as st
from datetime import date, datetime, timedelta
from utils.persistence import save as _save


# ── Initialisation ─────────────────────────────────────────────────────────

def init_session_state():
    """Set default values for every key used across the app."""
    defaults = {
        # Auth
        "logged_in": False,
        "auth_username": "",

        # Onboarding
        "onboarded": False,
        "user_name": "",
        "study_goal": "",
        "baseline_symptoms": [],
        "study_start_date": None,
        "onboarding_step": 1,

        # Navigation
        "current_page": "onboarding",

        # Chat
        "chat_messages": [],

        # Diary & meals
        "diary_entries": {},
        "meal_logs": {},
        "diary_feedback": "",
        "diary_submitted": False,
        "edit_diary": False,
        "meal_feedback": "",
        "meal_logged": False,

        # tasks_today derived from real data below — not set here


        # Settings
        "demo_mode": True,
        "llm_provider": "demo",

        # Chat input state
        "chat_input_key": 0,
        "chat_pending": "",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Derive today's task completion from real data so it survives refresh
    if "tasks_today" not in st.session_state:
        today = date.today().isoformat()
        st.session_state.tasks_today = {
            "diary":    today in st.session_state.diary_entries,
            "meals":    bool(st.session_state.meal_logs.get(today)),
            "check_in": False,
        }

    # Generate demo historical data once
    if "demo_diary_data" not in st.session_state:
        st.session_state.demo_diary_data = _generate_demo_history()


def _generate_demo_history():
    """14 days of realistic digestion score history for the progress chart."""
    scores = [3, 3, 4, 3, 4, 4, 5, 4, 3, 4, 5, 4, 5, 4]
    today = date.today()
    data = []
    for i, score in enumerate(scores):
        day = today - timedelta(days=13 - i)
        data.append({
            "date": day.strftime("%b %d"),
            "date_obj": day,
            "digestion_score": score,
            "completed": True,
        })
    return data


# ── Task helpers ───────────────────────────────────────────────────────────

def get_task_completion_pct() -> int:
    tasks = st.session_state.tasks_today
    completed = sum(1 for v in tasks.values() if v)
    return int((completed / len(tasks)) * 100)


def get_streak() -> int:
    """Days in a row with a diary entry. Returns 1 for a brand-new participant."""
    entries = st.session_state.diary_entries
    if not entries:
        return 1  # day 1 of the study

    streak = 0
    check = date.today()
    while check.isoformat() in entries:
        streak += 1
        check -= timedelta(days=1)
    return max(streak, 1)


def get_days_in_study() -> int:
    start = st.session_state.get("study_start_date")
    if start:
        if isinstance(start, str):
            try:
                start = date.fromisoformat(start)
            except ValueError:
                return 1
        return (date.today() - start).days + 1
    return 1


# ── Data persistence ───────────────────────────────────────────────────────

def save_diary_entry(entry: dict):
    today = date.today().isoformat()
    st.session_state.diary_entries[today] = entry
    st.session_state.tasks_today["diary"] = True

    # Keep demo chart data in sync
    today_str = date.today().strftime("%b %d")
    for d in st.session_state.demo_diary_data:
        if d["date"] == today_str:
            d["digestion_score"] = entry["digestion_score"]
            _save(st.session_state)
            return
    st.session_state.demo_diary_data.append({
        "date": today_str,
        "date_obj": date.today(),
        "digestion_score": entry["digestion_score"],
        "completed": True,
    })
    _save(st.session_state)


def save_meal_log(meal: dict):
    today = date.today().isoformat()
    if today not in st.session_state.meal_logs:
        st.session_state.meal_logs[today] = []
    st.session_state.meal_logs[today].append(meal)
    st.session_state.tasks_today["meals"] = True
    _save(st.session_state)


def add_chat_message(role: str, content: str):
    st.session_state.chat_messages.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().strftime("%H:%M"),
    })
