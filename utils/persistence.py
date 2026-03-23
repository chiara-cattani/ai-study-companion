"""
Simple JSON file persistence for Study Companion AI.

Saves user profile, diary entries, and meal logs to a local file so data
survives page refreshes and browser tab restores.
"""
import json
from pathlib import Path
from datetime import date, datetime

DATA_FILE = Path(__file__).parent.parent / ".study_data.json"

# Keys that are saved to disk
_PERSIST_KEYS = [
    "onboarded",
    "user_name",
    "study_goal",
    "baseline_symptoms",
    "study_start_date",
    "diary_entries",
    "meal_logs",
    "current_page",
    "llm_provider",
    "demo_mode",
]


def _default(obj):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Not serializable: {type(obj)}")


def save(ss) -> None:
    """Write relevant session state keys to the data file."""
    start = ss.get("study_start_date")
    data = {k: ss.get(k) for k in _PERSIST_KEYS}
    data["study_start_date"] = start.isoformat() if isinstance(start, date) else (start or "")
    try:
        DATA_FILE.write_text(
            json.dumps(data, indent=2, default=_default),
            encoding="utf-8",
        )
    except IOError:
        pass


def load(ss) -> None:
    """Read the data file and populate session state. No-op if file missing."""
    if not DATA_FILE.exists():
        return
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return

    for k in _PERSIST_KEYS:
        if k in data and k not in ss and k != "study_start_date":
            ss[k] = data[k]

    # Always deserialise study_start_date as a proper date object
    start_str = data.get("study_start_date", "")
    if start_str and "study_start_date" not in ss:
        try:
            ss["study_start_date"] = date.fromisoformat(start_str)
        except ValueError:
            pass


def delete() -> None:
    """Remove the data file (used on session reset)."""
    try:
        DATA_FILE.unlink(missing_ok=True)
    except IOError:
        pass
