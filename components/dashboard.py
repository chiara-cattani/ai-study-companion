"""
Dashboard (home screen) and Progress screen.
"""

import streamlit as st
from datetime import date
import plotly.graph_objects as go

from utils.state_manager import get_task_completion_pct, get_streak, get_days_in_study


# ── Dashboard ──────────────────────────────────────────────────────────────

def _time_greeting() -> str:
    from datetime import datetime
    h = datetime.now().hour
    if h < 12:
        return "Good morning,"
    if h < 18:
        return "Good afternoon,"
    return "Good evening,"


def render_dashboard():
    name = st.session_state.user_name
    today_str = date.today().strftime("%A, %B %d")
    tasks = st.session_state.tasks_today
    pct = get_task_completion_pct()
    streak = get_streak()
    greeting = _time_greeting()

    # Header — fully white via a dedicated CSS class that beats the global rule
    st.markdown(f"""
    <div class="dash-header">
        <div class="dash-left">
            <p class="dash-greeting">{greeting}</p>
            <h2 class="dash-name">{name}</h2>
            <p class="dash-date">{today_str}</p>
        </div>
        <div class="streak-pill">🔥 {streak} day streak</div>
    </div>
    """, unsafe_allow_html=True)

    # Reminder banners
    _reminders(tasks)

    # Progress bar
    st.markdown("### Today's Progress")
    st.progress(pct / 100)
    _task_cards(tasks)
    st.markdown(
        f'<p class="progress-label">{sum(v for v in tasks.values())}/{len(tasks)} tasks completed</p>',
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # Navigation grid
    st.markdown("### What would you like to do?")
    _action_grid(tasks)

    # Motivational footer
    _motivation(pct, name)


def _reminders(tasks):
    if not tasks["diary"]:
        st.markdown("""
        <div class="banner banner-warn">
            📝&nbsp; <strong>Daily diary not completed yet</strong> — it only takes 2 minutes!
        </div>
        """, unsafe_allow_html=True)
    if not tasks["meals"]:
        st.markdown("""
        <div class="banner banner-info">
            🍽️&nbsp; Don't forget to <strong>log your meals</strong> today.
        </div>
        """, unsafe_allow_html=True)
    if not tasks["check_in"]:
        st.markdown("""
        <div class="banner banner-info">
            💬&nbsp; Your <strong>AI Coach</strong> is waiting for your daily check-in.
        </div>
        """, unsafe_allow_html=True)
    if all(tasks.values()):
        st.markdown("""
        <div class="banner banner-ok">
            ✅&nbsp; <strong>All tasks done!</strong> Outstanding work today.
        </div>
        """, unsafe_allow_html=True)


def _task_cards(tasks):
    page_map = {"diary": "diary", "meals": "meal_log", "check_in": "chat"}
    items = [
        ("📝", "Diary", "diary"),
        ("🍽️", "Meals", "meals"),
        ("💬", "Check-in", "check_in"),
    ]
    cols = st.columns(3)
    for col, (icon, label, key) in zip(cols, items):
        done = tasks[key]
        status = "✅" if done else "⏳"
        border_color = "#4CAF82" if done else "#CBD5E1"
        with col:
            st.markdown(f'<div class="tc-wrap" style="border-top:3px solid {border_color}">', unsafe_allow_html=True)
            if st.button(f"{icon}\n{label}\n{status}", key=f"tc_{key}", use_container_width=True):
                st.session_state.current_page = page_map[key]
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


def _action_grid(tasks):
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💬  Chat with AI Coach", use_container_width=True, type="primary"):
            st.session_state.current_page = "chat"
            st.rerun()

        diary_lbl = "📝  Daily Diary ✓" if tasks["diary"] else "📝  Daily Diary"
        if st.button(diary_lbl, use_container_width=True):
            st.session_state.current_page = "diary"
            st.rerun()

    with col2:
        meal_lbl = "🍽️  Log a Meal +" if tasks["meals"] else "🍽️  Log a Meal"
        if st.button(meal_lbl, use_container_width=True):
            st.session_state.current_page = "meal_log"
            st.rerun()

        if st.button("📊  My Progress", use_container_width=True):
            st.session_state.current_page = "progress"
            st.rerun()


def _motivation(pct, name):
    st.markdown("---")
    if pct == 100:
        msg = f"Outstanding, {name}! You've completed everything today. Your dedication is what makes this research valuable."
    elif pct >= 66:
        msg = f"Almost there, {name}! Just one more task and you've nailed today."
    elif pct >= 33:
        msg = f"Good start, {name}! Keep going — consistent data makes all the difference."
    else:
        msg = f"Ready to start, {name}? Your AI Coach is here to guide you through today's tasks."

    st.markdown(f"""
    <div class="motivation-box">
        <p>{msg}</p>
    </div>
    """, unsafe_allow_html=True)


# ── Progress screen ────────────────────────────────────────────────────────

def render_progress():
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("← Back"):
            st.session_state.current_page = "dashboard"
            st.rerun()
    with col2:
        st.markdown("## 📊 My Progress")

    streak = get_streak()
    days = get_days_in_study()
    diary_count = len(st.session_state.diary_entries)
    meal_count = sum(len(v) for v in st.session_state.meal_logs.values())

    # KPI row
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Day in Study", days)
    with k2:
        st.metric("Streak", f"{streak} days")
    with k3:
        st.metric("Diary Entries", diary_count if diary_count else "14*")
    with k4:
        st.metric("Meals Logged", meal_count if meal_count else "38*")

    if not diary_count:
        st.caption("*Demo data shown — complete your first diary entry to see real data.")

    st.markdown("---")

    # Digestion score chart
    st.markdown("### Digestion Score — Last 14 Days")
    data = st.session_state.demo_diary_data[-14:]
    labels = [d["date"] for d in data]
    scores = [d["digestion_score"] for d in data]

    _TICK  = dict(color="#374151", size=11)
    _LABEL = dict(color="#374151", size=12)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=labels,
        y=scores,
        mode="lines+markers",
        line=dict(color="#4CAF82", width=3),
        marker=dict(size=9, color="#4CAF82", line=dict(color="white", width=2)),
        fill="tozeroy",
        fillcolor="rgba(76,175,130,0.12)",
        hovertemplate="%{x}<br>Score: %{y}/5<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#374151", family="Inter, sans-serif"),
        xaxis=dict(
            showgrid=False,
            tickfont=_TICK,
            linecolor="#E2E8F0",
            tickcolor="#E2E8F0",
        ),
        yaxis=dict(
            range=[0, 5.5],
            showgrid=True,
            gridcolor="#E2E8F0",
            tickfont=_TICK,
            linecolor="#E2E8F0",
            tickcolor="#E2E8F0",
        ),
        margin=dict(l=0, r=0, t=10, b=0),
        height=280,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Task completion
    st.markdown("---")
    st.markdown("### Task Completion Rate")
    completion_data = {
        "Week 1": 71,
        "Week 2": 85,
        "Week 3": 90,
        "This week": 95,
    }
    fig2 = go.Figure(go.Bar(
        x=list(completion_data.keys()),
        y=list(completion_data.values()),
        marker_color=["#B2DFDB", "#80CBC4", "#4DB6AC", "#4CAF82"],
        text=[f"{v}%" for v in completion_data.values()],
        textposition="outside",
        textfont=dict(color="#374151", size=13, family="Inter, sans-serif"),
    ))
    fig2.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#374151", family="Inter, sans-serif"),
        xaxis=dict(
            showgrid=False,
            tickfont=_LABEL,
            linecolor="#E2E8F0",
            tickcolor="#E2E8F0",
        ),
        yaxis=dict(range=[0, 115], showgrid=False, visible=False),
        margin=dict(l=0, r=0, t=20, b=0),
        height=220,
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Study insight
    st.markdown("---")
    st.markdown("### AI Insight")
    avg = sum(scores) / len(scores)
    trend = scores[-1] - scores[0]
    trend_str = "improving" if trend > 0 else ("stable" if trend == 0 else "fluctuating")

    st.markdown(f"""
    <div class="insight-card">
        <p>
            Your average digestion score over the last 14 days is
            <strong>{avg:.1f}/5</strong>.<br>
            Your trend is <strong>{trend_str}</strong> —
            {'great progress toward your goal!' if trend > 0 else 'keep logging consistently for clearer patterns.'}<br>
            Your compliance rate this week is <strong>95%</strong> — above the study average of 72%.
        </p>
    </div>
    """, unsafe_allow_html=True)
