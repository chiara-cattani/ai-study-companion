"""
Simple JSON file persistence for Study Companion AI.

Each user's data is stored in its own file:
    .study_data_<username>.json
"""
import json
from pathlib import Path
from datetime import date, datetime

_DATA_DIR = Path(__file__).parent.parent

# Keys that are saved to disk (also imported by login.py to clear stale defaults)
PERSIST_KEYS = _PERSIST_KEYS = [
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


def _data_file(ss) -> Path:
    username = ss.get("auth_username", "default") if ss else "default"
    # Sanitise to safe filename characters
    safe = "".join(c for c in username if c.isalnum() or c in "_-") or "default"
    return _DATA_DIR / f".study_data_{safe}.json"


def _default(obj):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Not serializable: {type(obj)}")


def save(ss) -> None:
    """Write relevant session state keys to this user's data file."""
    start = ss.get("study_start_date")
    data = {k: ss.get(k) for k in _PERSIST_KEYS}
    data["study_start_date"] = (
        start.isoformat() if isinstance(start, date) else (start or "")
    )
    try:
        _data_file(ss).write_text(
            json.dumps(data, indent=2, default=_default),
            encoding="utf-8",
        )
    except IOError:
        pass


def load(ss) -> None:
    """Read this user's data file and populate session state. No-op if missing."""
    path = _data_file(ss)
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
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


def delete(ss) -> None:
    """Remove this user's data file (used on session reset)."""
    try:
        _data_file(ss).unlink(missing_ok=True)
    except IOError:
        pass
