# Study Companion AI

An AI-powered participant engagement assistant for clinical nutrition studies.

Demonstrates how AI can improve participant compliance, reduce missing data, and increase engagement in clinical trials.

---

## Features

- **Onboarding** — personalised setup in under 1 minute
- **AI Chat Coach** — empathetic, context-aware conversation (OpenAI / Claude / Demo)
- **Daily Diary** — structured digestion & symptom logging
- **Meal Logger** — text or photo meal entry
- **Progress Dashboard** — streak tracking, digestion score chart
- **Smart Reminders** — in-app banners for incomplete tasks

---

## Quick Start (Local)

```bash
# 1. Clone / download the project
cd study_companion_ai

# 2. Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
.venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Set API keys
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY or ANTHROPIC_API_KEY

# 5. Run the app
streamlit run app.py
```

The app opens at **http://localhost:8501**

> **No API key?** Enable **Demo Mode** in the sidebar — the app works fully with simulated AI responses.

---

## Environment Variables

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key (GPT-4o-mini) |
| `ANTHROPIC_API_KEY` | Anthropic API key (Claude Haiku) |

Set via `.env` file or directly in the sidebar at runtime.

---

## Deploy to Streamlit Cloud

1. Push this folder to a **GitHub repository**
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in
3. Click **New app** → select your repo → set main file to `app.py`
4. Under **Advanced settings → Secrets**, add:
   ```toml
   OPENAI_API_KEY = "sk-..."
   # or
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
5. Click **Deploy** — your app gets a public URL instantly

---

## Project Structure

```
study_companion_ai/
├── app.py                  # Entry point & routing
├── requirements.txt
├── README.md
├── .env.example
│
├── components/
│   ├── onboarding.py       # Welcome & setup flow
│   ├── dashboard.py        # Main dashboard + progress screen
│   ├── chatbot.py          # AI chat interface
│   └── diary.py            # Daily diary + meal logger
│
├── utils/
│   ├── llm_client.py       # LLM wrapper (OpenAI / Claude / Demo)
│   └── state_manager.py    # Session state helpers
│
└── assets/
    └── styles.css          # Mobile-first stylesheet
```

---

## Demo Mode

Toggle **Demo Mode** in the sidebar (on by default). The app uses carefully crafted simulated responses that mirror real LLM behaviour — perfect for demos and presentations without needing an API key.

---

## Research Context

This prototype demonstrates:
- **Compliance improvement** — daily task tracking with visual progress
- **Missing data reduction** — gentle reminders and AI-guided completion
- **Engagement** — conversational AI coach with empathetic responses
- **Data collection** — structured diary entries and meal logs stored in session

*For research demonstration only. Not a medical device.*
