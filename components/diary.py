"""
Daily diary form and meal logger.
"""

import os
import streamlit as st
import streamlit.components.v1 as components
from datetime import date, datetime
from utils.state_manager import save_diary_entry, save_meal_log
from utils.llm_client import get_diary_feedback, get_meal_feedback
from utils.nutrition import build_food_item, recompute_nutrition
from utils.food_vision import recognize_food_from_bytes

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

UNIT_GRAMS = {
    "grams": 1,
    "cup": 240,
    "tbsp": 15,
    "tsp": 5,
    "slice": 30,
    "handful": 40,
    "bowl": 300,
    "plate": 400,
    "glass": 250,
    "oz": 28,
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

def _init_pending():
    """Initialise transient meal-log state keys once per session."""
    defaults = {
        "pending_food_items": [],
        "deleted_food_item": None,  # (index, item) for undo
        "add_input_counter": 0,     # bumped to clear add-food inputs
        "photo_key": 0,             # bumped to reset camera/uploader widgets
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _clear_meal_log_state():
    st.session_state.pending_food_items = []
    st.session_state.deleted_food_item = None
    st.session_state.add_input_counter = 0
    st.session_state.photo_key += 1  # resets camera & uploader


def _status_chip(status: str, confidence: float, nutrition_source: str = "openfoodfacts") -> str:
    low = confidence < 0.6 and status == "ai_detected"
    chips = {
        "ai_detected":    '<span class="ft-chip ft-chip-ai">AI detected</span>',
        "manually_added": '<span class="ft-chip ft-chip-manual">Manual</span>',
        "edited":         '<span class="ft-chip ft-chip-edited">Edited</span>',
    }
    html = chips.get(status, "")
    if low:
        html += '<span class="ft-chip ft-chip-low">Low confidence</span>'
    if nutrition_source == "fallback":
        html += '<span class="ft-chip ft-chip-fallback">Nutrition estimated</span>'
    return html


def render_meal_log():
    _init_pending()

    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("← Back"):
            st.session_state.current_page = "dashboard"
            _clear_meal_log_state()
            st.rerun()
    with col2:
        st.markdown("## 🍽️ Log a Meal")

    today = date.today().isoformat()
    today_meals = st.session_state.meal_logs.get(today, [])

    # ── AI feedback from previous save (show at top)
    if st.session_state.get("meal_logged") and st.session_state.get("meal_feedback"):
        st.markdown(f"""
        <div class="ai-fb-card">
            <span class="ai-fb-tag">🤖 AI Coach</span>
            <p>{st.session_state.meal_feedback}</p>
        </div>
        """, unsafe_allow_html=True)
        st.session_state.meal_logged = False

    # ── Previously logged meals for today
    if today_meals:
        st.markdown(f"**{len(today_meals)} meal(s) logged today:**")
        for meal in today_meals:
            _render_logged_meal_card(meal)
        st.markdown("---")

    # ── AI Settings (collapsed once a key is already set)
    key_set = bool(os.getenv("OPENAI_API_KEY", ""))
    with st.expander("⚙️ AI Settings for food recognition", expanded=not key_set):
        demo_on = st.toggle(
            "Demo Mode (no API key needed)",
            value=st.session_state.get("demo_mode", True),
            key="meal_demo_toggle",
        )
        st.session_state.demo_mode = demo_on
        if demo_on:
            st.session_state.llm_provider = "demo"
            st.caption("Demo mode on — you can still add foods manually and get nutrition data.")
        else:
            st.session_state.llm_provider = "openai"
            entered_key = st.text_input(
                "OpenAI API Key",
                type="password",
                value=os.getenv("OPENAI_API_KEY", ""),
                placeholder="sk-...",
                key="meal_openai_key",
            )
            if entered_key:
                os.environ["OPENAI_API_KEY"] = entered_key
            st.caption("Upload a meal photo below and tap **Analyze with AI** to auto-detect foods.")

    # ── Meal type
    st.markdown("#### What type of meal?")
    meal_type = st.radio(
        "Meal type",
        ["🌅 Breakfast", "☀️ Lunch", "🌙 Dinner", "🍎 Snack"],
        horizontal=True,
        label_visibility="collapsed",
    )

    # ── Photo: camera or upload (key resets both widgets after analysis)
    pk = st.session_state.photo_key
    st.markdown("#### Photo: *(optional)*")
    tab_cam, tab_upload = st.tabs(["📷 Take photo", "📤 Upload"])
    with tab_cam:
        photo_cam = st.camera_input(
            "Point your camera at the meal",
            key=f"cam_{pk}",
            label_visibility="collapsed",
        )
        components.html("""
<script>
(function() {
    if (!navigator.permissions) return;
    navigator.permissions.query({name: 'camera'}).then(function(result) {
        if (result.state !== 'denied') return;
        var attempts = 0;
        function tryInject() {
            try {
                var pd = window.parent.document;
                var camWidget = pd.querySelector('[data-testid="stCameraInput"]');
                if (!camWidget) {
                    if (attempts++ < 15) setTimeout(tryInject, 200);
                    return;
                }
                camWidget.style.visibility = 'hidden';
                camWidget.style.height = '0';
                camWidget.style.overflow = 'hidden';
                if (pd.getElementById('cam-perm-msg')) return;
                var div = pd.createElement('div');
                div.id = 'cam-perm-msg';
                div.style.cssText = 'background:#EFF6FF;border:1px solid #93C5FD;border-radius:8px;padding:14px 16px;color:#1E40AF;font-family:Inter,sans-serif;font-size:14px;margin:8px 0;line-height:1.5;';
                div.innerHTML = '📷 <strong>Camera access is blocked.</strong><br>Allow camera access in your browser settings, then refresh the page.';
                camWidget.parentNode.insertBefore(div, camWidget);
            } catch(e) {}
        }
        tryInject();
        result.onchange = function() {
            if (result.state === 'denied') tryInject();
        };
    }).catch(function() {});
})();
</script>
""", height=0)
    with tab_upload:
        photo_upload = st.file_uploader(
            "Choose a photo",
            type=["jpg", "jpeg", "png", "webp"],
            key=f"upl_{pk}",
            label_visibility="collapsed",
        )

    photo = photo_cam or photo_upload

    if photo:
        # Read bytes once — st.image() consumes the file pointer otherwise
        image_bytes = photo.read()

        # Small centered preview
        _, img_col, _ = st.columns([1, 2, 1])
        with img_col:
            st.image(image_bytes, use_container_width=True)

        provider = st.session_state.get("llm_provider", "demo")
        api_key  = os.getenv("OPENAI_API_KEY", "")

        if provider == "openai" and api_key:
            if st.button("🔍 Analyze with AI", type="primary", use_container_width=True):
                with st.spinner("Identifying foods in your photo…"):
                    foods = recognize_food_from_bytes(image_bytes, api_key)
                if foods:
                    for food in foods:
                        item = build_food_item(
                            food["name"],
                            float(food.get("estimated_grams", 100)),
                            status="ai_detected",
                            confidence=float(food.get("confidence", 1.0)),
                        )
                        st.session_state.pending_food_items.append(item)
                    st.session_state.photo_key += 1  # clears the photo immediately
                    st.rerun()
                else:
                    st.warning("No foods detected. Add them manually below.")
        else:
            st.info("Enable **OpenAI** in ⚙️ AI Settings above to use photo recognition.")

    st.markdown("---")

    # ── Food items editor
    if st.session_state.pending_food_items:
        st.markdown("#### Foods in this meal:")
        _render_food_items_editor()
    else:
        st.markdown("#### Foods in this meal:")
        st.markdown(
            '<p style="color:#8896A7;font-size:0.88rem;margin:0.25rem 0 0.75rem;">No items yet — add them below.</p>',
            unsafe_allow_html=True,
        )

    # ── Manual food add
    st.markdown("#### Add a food:")
    _render_manual_add()

    # ── Nutrition summary
    if st.session_state.pending_food_items:
        _render_nutrition_summary()

    # ── Notes
    st.markdown("#### Notes: *(optional)*")
    meal_desc = st.text_area(
        "Notes",
        placeholder="e.g. Grilled salmon, mixed salad, glass of water…",
        label_visibility="collapsed",
        height=75,
        key="meal_desc_input",
    )

    st.markdown("---")

    _, bcol = st.columns([1, 2])
    with bcol:
        if st.button("Log Meal ✓", type="primary", use_container_width=True):
            food_items = list(st.session_state.pending_food_items)
            desc = meal_desc.strip()

            if not food_items and not desc:
                st.error("Please add at least one food item or describe your meal.")
            else:
                if not desc and food_items:
                    desc = ", ".join(item["food_name"].title() for item in food_items)

                total_cals  = round(sum(i["calories"] for i in food_items), 1)
                total_prot  = round(sum(i["protein"]  for i in food_items), 1)
                total_fat   = round(sum(i["fat"]      for i in food_items), 1)
                total_carbs = round(sum(i["carbs"]    for i in food_items), 1)

                meal = {
                    "type": meal_type,
                    "description": desc,
                    "time": datetime.now().strftime("%H:%M"),
                    "has_photo": photo is not None,
                    "food_items": food_items,
                    "total_calories": total_cals,
                    "total_protein":  total_prot,
                    "total_fat":      total_fat,
                    "total_carbs":    total_carbs,
                }
                save_meal_log(meal)

                ctx      = {"name": st.session_state.user_name, "goal": st.session_state.study_goal}
                provider = st.session_state.get("llm_provider", "demo")
                st.session_state.meal_feedback = get_meal_feedback(desc, ctx, provider)
                st.session_state.meal_logged   = True
                _clear_meal_log_state()
                st.rerun()


# ── Sub-renderers ───────────────────────────────────────────────────────────

def _render_logged_meal_card(meal: dict):
    """Saved meal card with inline nutrition row when available."""
    food_items = meal.get("food_items", [])
    st.markdown(f"""
    <div class="meal-card">
        <span class="meal-type">{meal.get('type', '')}</span>
        <span class="meal-desc">{meal.get('description', '')}</span>
        <span class="meal-time">{meal.get('time', '')}</span>
    </div>
    """, unsafe_allow_html=True)

    if food_items:
        st.markdown(f"""
        <div class="nutrition-summary-card" style="margin-top:0.25rem;margin-bottom:0.6rem;">
            <div class="nutrition-summary-row">
                <div class="nutrition-chip chip-cal">🔥 {meal.get('total_calories',0):.0f} kcal</div>
                <div class="nutrition-chip chip-pro">P {meal.get('total_protein',0):.0f}g</div>
                <div class="nutrition-chip chip-fat">F {meal.get('total_fat',0):.0f}g</div>
                <div class="nutrition-chip chip-car">C {meal.get('total_carbs',0):.0f}g</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def _render_food_items_editor():
    """Inline-editable food item list: name + grams inputs, quick ±g buttons, delete."""
    items = st.session_state.pending_food_items
    to_delete = None
    changed   = False

    # Undo banner
    if st.session_state.deleted_food_item is not None:
        d_idx, d_item = st.session_state.deleted_food_item
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(
                f'<div class="banner banner-info">↩️ <em>{d_item["food_name"].title()}</em> removed.</div>',
                unsafe_allow_html=True,
            )
        with c2:
            if st.button("Undo", key="undo_del", use_container_width=True):
                items.insert(min(d_idx, len(items)), d_item)
                st.session_state.deleted_food_item = None
                st.rerun()

    for i, item in enumerate(items):
        chip_html = _status_chip(
            item.get("status", "manually_added"),
            item.get("confidence", 1.0),
            item.get("nutrition_source", "openfoodfacts"),
        )

        # Info card
        st.markdown(f"""
        <div class="food-item-card">
            <div class="food-item-header">
                <span class="food-item-name">{item['food_name'].title()}</span>
                {chip_html}
            </div>
            <div class="food-item-macros">
                🔥 <strong>{item['calories']:.0f}</strong> kcal
                &nbsp;·&nbsp; P <strong>{item['protein']:.1f}</strong>g
                &nbsp;·&nbsp; F <strong>{item['fat']:.1f}</strong>g
                &nbsp;·&nbsp; C <strong>{item['carbs']:.1f}</strong>g
                &nbsp;·&nbsp; <span style="color:#8896A7">{item['grams']:.0f}g</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Edit row: name | grams | 🔄 update | ❌ delete
        cn, cg, cu, cd = st.columns([3, 1.5, 1, 1])
        with cn:
            new_name = st.text_input(
                "Name", value=item["food_name"],
                key=f"iname_{i}", label_visibility="collapsed",
            )
        with cg:
            new_grams = st.number_input(
                "g", value=float(item["grams"]),
                min_value=1.0, step=10.0,
                key=f"igrams_{i}", label_visibility="collapsed",
            )
        with cu:
            if st.button("🔄", key=f"iupd_{i}", help="Update nutrition", use_container_width=True):
                item["food_name"] = new_name.strip() or item["food_name"]
                item["grams"]     = new_grams
                item["status"]    = "edited"
                recompute_nutrition(item)
                changed = True
        with cd:
            if st.button("❌", key=f"idel_{i}", help="Remove", use_container_width=True):
                to_delete = i

        # Quick gram buttons
        qa1, qa2, qa3, qa4 = st.columns(4)
        for col, delta in [(qa1, -50), (qa2, -10), (qa3, 10), (qa4, 50)]:
            with col:
                if st.button(f"{delta:+d}g", key=f"iqk_{i}_{delta}", use_container_width=True):
                    item["grams"] = max(1.0, item["grams"] + delta)
                    recompute_nutrition(item)
                    changed = True

        st.markdown("<div style='margin-bottom:0.5rem'></div>", unsafe_allow_html=True)

    if to_delete is not None:
        st.session_state.deleted_food_item = (to_delete, items.pop(to_delete))
        st.rerun()
    if changed:
        st.rerun()


def _render_manual_add():
    """Inline food-add row (no st.form — avoids the black form background)."""
    n = st.session_state.add_input_counter  # bumping this clears the inputs

    c1, c2, c3 = st.columns([3, 1.2, 1.2])
    with c1:
        food_name = st.text_input(
            "Food name",
            placeholder="e.g. grilled chicken",
            label_visibility="collapsed",
            key=f"add_name_{n}",
        )
    with c2:
        quantity = st.number_input(
            "Qty", min_value=1, value=100, step=10,
            label_visibility="collapsed",
            key=f"add_qty_{n}",
        )
    with c3:
        unit = st.selectbox(
            "Unit", list(UNIT_GRAMS.keys()),
            label_visibility="collapsed",
            key=f"add_unit_{n}",
        )

    if st.button("➕ Add food", use_container_width=True):
        name = food_name.strip()
        if name:
            grams = float(quantity * UNIT_GRAMS.get(unit, 1))
            with st.spinner(f"Looking up {name}…"):
                item = build_food_item(name, grams, status="manually_added")
            st.session_state.pending_food_items.append(item)
            st.session_state.add_input_counter += 1  # clears inputs on next render
            st.rerun()
        else:
            st.warning("Please enter a food name.")


def _render_nutrition_summary():
    """Live nutrition totals card for all pending items."""
    items       = st.session_state.pending_food_items
    total_cals  = sum(i["calories"] for i in items)
    total_prot  = sum(i["protein"]  for i in items)
    total_fat   = sum(i["fat"]      for i in items)
    total_carbs = sum(i["carbs"]    for i in items)

    st.markdown(f"""
    <div class="nutrition-summary-card">
        <div class="nutrition-summary-title">Meal Total · {len(items)} item{"s" if len(items) != 1 else ""}</div>
        <div class="nutrition-summary-row">
            <div class="nutrition-chip chip-cal">🔥 {total_cals:.0f} kcal</div>
            <div class="nutrition-chip chip-pro">P {total_prot:.1f}g</div>
            <div class="nutrition-chip chip-fat">F {total_fat:.1f}g</div>
            <div class="nutrition-chip chip-car">C {total_carbs:.1f}g</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
