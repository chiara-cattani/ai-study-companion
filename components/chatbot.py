"""
AI Chat Coach interface.
"""

import re
import streamlit as st
from utils.state_manager import add_chat_message
from utils.llm_client import generate_response


def _md(text: str) -> str:
    """Convert basic markdown to HTML for safe injection into chat bubbles."""
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    return text


QUICK_REPLIES = [
    "I completed my diary today ✅",
    "Give me a wellness tip 💡",
    "How's my progress? 📊",
    "I forgot to log meals 😅",
]


def render_chatbot():
    # Top bar
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("← Back"):
            st.session_state.current_page = "dashboard"
            st.rerun()
    with col2:
        st.markdown("""
        <div class="chat-topbar">
            <span class="chat-avatar">🌿</span>
            <div class="chat-info">
                <strong>Study Companion AI</strong>
                <span class="online-dot">● Online</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Seed welcome message if chat is empty
    if not st.session_state.chat_messages:
        name = st.session_state.user_name
        goal = st.session_state.study_goal
        add_chat_message(
            "assistant",
            f"Hi {name}! I'm your Study Companion AI. "
            f"I'm here to support your goal to **{goal.lower()}**. "
            "How are you feeling today?",
        )

    # Render messages
    _render_messages()

    # Quick replies
    st.markdown('<p class="qr-label">Quick replies:</p>', unsafe_allow_html=True)
    qcols = st.columns(2)
    for i, reply in enumerate(QUICK_REPLIES):
        with qcols[i % 2]:
            if st.button(reply, key=f"qr_{i}", use_container_width=True):
                _send(reply)

    # Input box — key counter clears the field after each send
    st.markdown("---")

    input_key = f"chat_msg_{st.session_state.chat_input_key}"

    def _on_enter():
        val = st.session_state.get(input_key, "").strip()
        if val:
            st.session_state.chat_pending = val
            st.session_state.chat_input_key += 1

    icol, bcol = st.columns([5, 1])
    with icol:
        st.text_input(
            "Message",
            placeholder="Type a message and press Enter...",
            label_visibility="collapsed",
            key=input_key,
            on_change=_on_enter,
        )
    with bcol:
        if st.button("Send", type="primary", use_container_width=True):
            val = st.session_state.get(input_key, "").strip()
            if val:
                st.session_state.chat_pending = val
                st.session_state.chat_input_key += 1
                st.rerun()

    # Process any pending message (from Enter or Send button)
    if st.session_state.get("chat_pending"):
        text = st.session_state.chat_pending
        st.session_state.chat_pending = ""
        _send(text)


def _render_messages():
    """Render the conversation bubble by bubble."""
    for msg in st.session_state.chat_messages:
        ts = msg.get("timestamp", "")
        content = _md(msg["content"])

        if msg["role"] == "user":
            st.markdown(f"""
            <div class="msg-row msg-user">
                <div class="bubble bubble-user">
                    {content}
                    <span class="msg-ts">{ts}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="msg-row msg-ai">
                <div class="bubble-avatar">🌿</div>
                <div class="bubble bubble-ai">
                    {content}
                    <span class="msg-ts">{ts}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)


def _send(text: str):
    add_chat_message("user", text)
    # Mark check-in done only when the user actually sends a message
    st.session_state.tasks_today["check_in"] = True

    context = {
        "name": st.session_state.user_name,
        "goal": st.session_state.study_goal,
        "history": list(st.session_state.chat_messages[:-1]),
    }
    provider = st.session_state.get("llm_provider", "demo")

    with st.spinner(""):
        response = generate_response(text, context, provider)

    add_chat_message("assistant", response)
    st.rerun()
