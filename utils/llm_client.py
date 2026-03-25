"""
LLM client wrapper.

Supports three providers:
  - "demo"      : rule-based simulated responses (no API key needed)
  - "openai"    : GPT-4o-mini via OPENAI_API_KEY
  - "anthropic" : Claude Haiku via ANTHROPIC_API_KEY

Falls back to demo automatically on any API error.
"""

import os
import random

# ── System prompt ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a friendly, supportive AI study companion for a clinical nutrition research trial.

Your responsibilities:
1. Help participants stay engaged and complete their daily study tasks.
2. Guide them through diary entry and meal logging.
3. Provide gentle, timely reminders (diary, meals, nutrition plan).
4. Offer empathetic encouragement — celebrate effort, not just results.
5. Share light wellness coaching (hydration, fibre, sleep).

Rules you must always follow:
- NEVER give medical diagnoses or prescribe treatments.
- If a participant raises a medical concern, acknowledge it warmly and advise them to speak with their healthcare provider.
- Keep every reply to 2–4 sentences maximum.
- Use a warm, conversational tone.
- Use one relevant emoji per message.
- Address the participant by name when natural.
- Reference their study goal ("{goal}") when it adds value.
- Stay focused on the study: diary, meals, symptoms, wellbeing, and nutrition. If the conversation drifts to unrelated topics, gently steer it back.{redirect_instruction}

Participant name: {name}
Study goal: {goal}
"""

_REDIRECT_INSTRUCTION = """

IMPORTANT for this response: The participant has sent {n} messages in a row that are unrelated to the study. Acknowledge what they said very briefly (one short clause), then warmly redirect them back to the study — ask about how they're feeling, whether they've logged their diary or meals today, or how their nutrition goal is going. Keep it friendly, not preachy."""

# ── Demo response bank ─────────────────────────────────────────────────────

_DEMO = {
    "identity": [
        "I'm your Study Companion AI — a friendly assistant built to support you through the nutrition study. I can help you log meals, complete your diary, track your progress, and keep you motivated. 🌿",
        "Great question! I'm Study Companion AI, your personal guide for this research trial. Think of me as a supportive coach who's always here to help you stay on track. 😊",
        "I'm an AI coach designed specifically for this clinical nutrition study. My job is to make the study as easy and engaging as possible for you, {name}! 🤖",
    ],
    "how_are_you": [
        "I'm doing great, thank you for asking, {name}! Ready to support you today. How are *you* feeling? 😊",
        "Always here and ready to help! More importantly — how are you feeling today, {name}? Any symptoms worth noting? 🌿",
        "I'm fully charged and here for you! How about you, {name} — how has your day been so far? ✨",
    ],
    "greeting": [
        "Hi {name}! Great to see you today — how are you feeling? 😊",
        "Hello {name}! Ready to check in? Let's make today count. 🌿",
        "Hey {name}! Hope you're having a lovely day. How can I help? ✨",
        "Good to see you, {name}! How's everything going with the study so far? 💙",
    ],
    "task_reminder": [
        "Just a friendly nudge — your daily diary is still open. It only takes 2 minutes! 📝",
        "Don't forget to log your meals today, {name} — every entry helps the study. 🍽️",
        "Staying consistent with your logs makes a real difference to the research. You've got this! 💪",
        "A quick reminder: completing today's tasks keeps your streak alive and your data clean. 🔥",
        "The research team really does rely on your logs — even a quick entry goes a long way! 📊",
    ],
    "digestion": [
        "Thanks for sharing — digestion patterns tell us so much. Did any specific foods seem to help or bother you today? 🥗",
        "That's really useful data! How was your energy level alongside your digestion? ⚡",
        "Interesting — were there any meals that seemed to influence how you felt? 🤔",
        "Digestion is central to your study goal. The more detail you log, the clearer the picture becomes. 🔬",
        "That's worth noting in your diary! Head over to the Daily Diary to log this — it really helps. 📝",
    ],
    "empathy": [
        "No worries at all — life happens! Log what you remember and I'll help fill in the gaps. 🙌",
        "That's completely fine, {name}. What matters is you're here now. Want to catch up together? 💙",
        "Don't be hard on yourself — even partial data is valuable to the study. Let's do it now! 🌟",
        "Missing a log isn't the end of the world. The important thing is getting back on track — and you already have by being here. 💪",
        "Everyone misses a day occasionally! Just log what you can remember and keep going. Consistency over perfection. 😊",
    ],
    "coaching": [
        "Wellness tip: try drinking a glass of water 20 minutes before each meal — it can really help with digestion and satiety. 💧",
        "Aim for a colourful plate at each meal. A variety of vegetables feeds your gut microbiome with different fibres it loves. 🥦",
        "Did you know that eating slowly and chewing well can reduce bloating significantly? Try it at your next meal! 🍽️",
        "For better sleep through nutrition, try avoiding heavy meals within 2–3 hours of bedtime. A light snack like yoghurt or a banana is perfect. 🌙",
        "Prebiotic foods like oats, garlic, and bananas are excellent for gut health — great for your study goal! 🌾",
        "Consistent meal timing helps regulate your digestive system. Try eating at roughly the same times each day. ⏰",
    ],
    "diary_feedback": [
        "Diary logged — thank you, {name}! Every entry strengthens our research dataset. 🌟",
        "Amazing work! Your commitment to the study is truly making a difference. ✅",
        "Entry saved! This data will help us understand your progress much better. 🙏",
        "That's another valuable entry in the books, {name}. The research team will be pleased! 📊",
        "Wonderful — keeping a daily diary is one of the most powerful things you can do for this study. 💙",
    ],
    "progress": [
        "Your progress this past week has been really consistent, {name} — that's exactly what the study needs! 📈",
        "You're on a great streak — keep that momentum going! 🔥",
        "The data you're providing is high quality. The research team will be pleased with your consistency! 🎯",
        "Head to the Progress screen to see your digestion score chart — I think you'll like what you see! 📊",
        "Participants who log consistently like you do show measurably better outcomes in the study. Keep it up! 🏆",
    ],
    "general": [
        "That's interesting — tell me more about how you've been feeling. 💬",
        "Thanks for sharing! How has your energy been alongside this? ⚡",
        "You're doing a great job staying engaged with the study, {name}! 🌟",
        "I appreciate you opening up — is there anything specific you'd like guidance on today? 🤝",
        "Happy to help with anything study-related! You can ask me about meals, symptoms, tips, or just chat. 😊",
        "That's a great point to raise. Is there anything in particular you'd like to log or track today? 📋",
    ],
    "redirect": [
        "Fun topic! I'm really here to support your study though, {name} — have you logged your meals or diary today? 📋",
        "I appreciate the chat! To make the most of our time together, how about we check in on the study — how are you feeling symptom-wise? 🌿",
        "Ha, I'd love to help with that, but my expertise is your nutrition study! How has your energy and digestion been today, {name}? 🥗",
        "I'm best at the study stuff — let me nudge us back there! How's your goal to {goal} going this week? 🎯",
        "Good topic for another time! For now — have you completed today's diary entry, {name}? It only takes two minutes. 📝",
    ],
}


# Keywords that indicate a study-related message (broad — includes greetings)
_STUDY_KEYWORDS = (
    "diary", "meal", "food", "log", "symptom", "progress", "study",
    "nutrition", "health", "feel", "digest", "energy", "sleep", "goal",
    "gut", "stomach", "bloat", "tip", "wellness", "advice", "remind",
    "task", "score", "chart", "week", "streak", "stat", "data", "entry",
    "logged", "drink", "water", "eat", "ate", "forgot", "miss", "sorry",
    "hi", "hello", "hey", "how are you", "who are you", "what are you",
    "good morning", "good afternoon", "good evening",
)


def is_study_related(text: str) -> bool:
    """Return True if the message is related to the study or is a greeting."""
    lower = text.lower()
    return any(kw in lower for kw in _STUDY_KEYWORDS)


def _pick(category: str, name: str, goal: str = "") -> str:
    return random.choice(_DEMO[category]).format(name=name, goal=goal)


def get_demo_response(user_input: str, context: dict) -> str:
    """Route user input to the most relevant demo response category."""
    text = user_input.lower()
    name = context.get("name", "there")
    goal = context.get("goal", "")
    streak = context.get("off_topic_streak", 0)

    # If the user has been off-topic for 2+ messages in a row, redirect
    if streak >= 2 and not is_study_related(user_input):
        return _pick("redirect", name, goal)

    # Identity questions
    if any(w in text for w in ["your name", "who are you", "what are you", "tell me about yourself"]):
        return _pick("identity", name, goal)
    # How are you
    if any(w in text for w in ["how are you", "how r u", "you doing", "you okay", "you good"]):
        return _pick("how_are_you", name, goal)
    # Greetings
    if any(w in text for w in ["hello", "hi!", "hey!", "good morning", "good afternoon", "good evening"]) or text.strip() in ["hi", "hey", "hello"]:
        return _pick("greeting", name, goal)
    # Digestion / symptoms
    if any(w in text for w in ["digestion", "stomach", "bloat", "gut", "bowel", "cramp", "constip", "nausea", "symptom"]):
        return _pick("digestion", name, goal)
    # Missed tasks
    if any(w in text for w in ["forgot", "missed", "didn't", "couldn't", "skip", "sorry", "apologise", "apologi"]):
        return _pick("empathy", name, goal)
    # Wellness coaching
    if any(w in text for w in ["tip", "wellness", "advice", "suggest", "coach", "what should", "help me", "recommend"]):
        return _pick("coaching", name, goal)
    # Diary / logging
    if any(w in text for w in ["diary", "entry", "logged", "completed", "done", "submitted", "filled"]):
        return _pick("diary_feedback", name, goal)
    # Progress / stats
    if any(w in text for w in ["progress", "streak", "week", "chart", "how am i", "stats", "data", "score"]):
        return _pick("progress", name, goal)
    # Reminders / tasks
    if any(w in text for w in ["remind", "task", "meal", "log", "forget", "today"]):
        return _pick("task_reminder", name, goal)
    return _pick("general", name, goal)


# ── Public API ─────────────────────────────────────────────────────────────

def generate_response(user_input: str, context: dict, provider: str = "demo") -> str:
    """
    Generate a conversational AI response.

    Args:
        user_input : The participant's message.
        context    : Dict with keys: name, goal, history (list of {role, content}).
        provider   : "demo" | "openai" | "anthropic"

    Returns:
        Response string.
    """
    if provider == "demo":
        return get_demo_response(user_input, context)
    if provider == "openai":
        return _openai(user_input, context)
    if provider == "anthropic":
        return _anthropic(user_input, context)
    return get_demo_response(user_input, context)


def get_diary_feedback(entry: dict, context: dict, provider: str = "demo") -> str:
    """Short AI feedback message shown after diary submission."""
    if provider == "demo":
        name = context.get("name", "there")
        score = entry.get("digestion_score", 3)
        if score >= 4:
            return (
                f"Excellent entry, {name}! A digestion score of {score}/5 is great news. "
                "Keep up whatever you've been doing — it's clearly working! 🌟"
            )
        if score == 3:
            return (
                f"Thanks for logging, {name}! A score of {score}/5 is solid. "
                "Stay hydrated and we'll track your progress together. 💧"
            )
        return (
            f"Thank you for being honest, {name}. A score of {score}/5 — "
            "let's keep monitoring together. Our research team will review your data. 💙"
        )

    prompt = (
        f"The participant just submitted their daily diary. "
        f"Digestion score: {entry.get('digestion_score')}/5, "
        f"symptoms: {entry.get('symptoms', [])}, mood: {entry.get('mood', 'okay')}. "
        "Give a brief, encouraging response (2–3 sentences)."
    )
    return generate_response(prompt, context, provider)


def get_meal_feedback(meal_description: str, context: dict, provider: str = "demo") -> str:
    """Short AI feedback after a meal is logged."""
    if provider == "demo":
        name = context.get("name", "there")
        options = [
            f"Meal logged! Great job staying on track, {name}. Consistent logging really helps us understand your patterns. 🍽️",
            f"Got it! Thanks for logging that, {name}. Every entry adds value to the study. 📊",
            f"Logged successfully! You're building great data, {name}. The research team will love this consistency! ✅",
        ]
        return random.choice(options)

    prompt = (
        f"The participant just logged a meal: '{meal_description}'. "
        "Give brief, positive feedback (1–2 sentences). Do not give medical advice."
    )
    return generate_response(prompt, context, provider)


# ── Provider implementations ───────────────────────────────────────────────

def _build_messages(user_input: str, context: dict):
    messages = []
    for msg in context.get("history", [])[-8:]:
        if msg["role"] in ("user", "assistant"):
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_input})
    return messages


def _system(context: dict) -> str:
    streak = context.get("off_topic_streak", 0)
    redirect = (
        _REDIRECT_INSTRUCTION.format(n=streak)
        if streak >= 2 and not is_study_related(context.get("last_user_message", ""))
        else ""
    )
    return SYSTEM_PROMPT.format(
        name=context.get("name", "Participant"),
        goal=context.get("goal", "improve health"),
        redirect_instruction=redirect,
    )


def _openai(user_input: str, context: dict) -> str:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        msgs = [{"role": "system", "content": _system(context)}] + _build_messages(user_input, context)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=msgs,
            max_tokens=200,
            temperature=0.75,
        )
        return resp.choices[0].message.content
    except Exception:
        return get_demo_response(user_input, context)


def _anthropic(user_input: str, context: dict) -> str:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        msgs = _build_messages(user_input, context)
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            system=_system(context),
            messages=msgs,
        )
        return resp.content[0].text
    except Exception:
        return get_demo_response(user_input, context)
