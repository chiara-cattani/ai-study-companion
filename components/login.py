"""
Login and sign-up screen.
"""

import streamlit as st
from utils.auth import register, verify


def render_login():
    st.markdown("""
    <div class="hero">
        <div class="hero-logo">🌿</div>
        <h1 class="hero-title">Study Companion AI</h1>
        <p class="hero-sub">Your personal AI guide for the nutrition study</p>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

    with tab_login:
        _render_login_form()

    with tab_signup:
        _render_signup_form()


def _render_login_form():
    st.markdown("#### Welcome back")
    st.markdown(
        '<p style="color:#4B5563;font-size:0.92rem;margin-top:-0.4rem">'
        "Log in to continue your study.</p>",
        unsafe_allow_html=True,
    )

    username = st.text_input(
        "Username", placeholder="your username", key="login_username"
    )
    password = st.text_input(
        "Password", type="password", placeholder="••••••••", key="login_password"
    )

    if st.button("Log in", type="primary", use_container_width=True, key="btn_login"):
        if not username.strip() or not password:
            st.error("Please fill in both fields.")
            return
        ok, err = verify(username.strip(), password)
        if not ok:
            st.error(err)
            return
        _complete_login(username.strip().lower())


def _render_signup_form():
    st.markdown("#### Create your account")
    st.markdown(
        '<p style="color:#4B5563;font-size:0.92rem;margin-top:-0.4rem">'
        "Sign up to start the study — it only takes a moment.</p>",
        unsafe_allow_html=True,
    )

    username = st.text_input(
        "Choose a username", placeholder="e.g. sarah92", key="signup_username"
    )
    password = st.text_input(
        "Password",
        type="password",
        placeholder="at least 6 characters",
        key="signup_password",
    )
    confirm = st.text_input(
        "Confirm password", type="password", placeholder="••••••••", key="signup_confirm"
    )

    if st.button(
        "Create account", type="primary", use_container_width=True, key="btn_signup"
    ):
        uname = username.strip()
        if not uname:
            st.error("Please choose a username.")
            return
        if len(password) < 6:
            st.error("Password must be at least 6 characters.")
            return
        if password != confirm:
            st.error("Passwords don't match.")
            return
        ok, err = register(uname, password)
        if not ok:
            st.error(err)
            return
        # New account → go through onboarding
        st.session_state.auth_username = uname.lower()
        st.session_state.logged_in = True
        st.session_state.onboarded = False
        st.session_state.current_page = "onboarding"
        st.rerun()


def _complete_login(username: str):
    """Load persisted data for this user and go to dashboard."""
    from utils.persistence import load as _load, PERSIST_KEYS

    st.session_state.auth_username = username
    st.session_state.logged_in = True

    # Remove any session-defaulted values (set by init_session_state before auth)
    # so that _load() can populate them from the user's data file.
    for key in list(PERSIST_KEYS) + ["tasks_today", "_data_loaded"]:
        st.session_state.pop(key, None)

    _load(st.session_state)
    st.rerun()
