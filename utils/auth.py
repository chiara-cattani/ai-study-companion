"""
Simple username/password authentication for Study Companion AI.
Credentials stored in users.json (SHA-256 hashed, salted passwords).
"""
import json
import hashlib
import os
from pathlib import Path

USERS_FILE = Path(__file__).parent.parent / "users.json"


def _load_users() -> dict:
    if not USERS_FILE.exists():
        return {}
    try:
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return {}


def _save_users(users: dict) -> None:
    try:
        USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")
    except IOError:
        pass


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode()).hexdigest()


def user_exists(username: str) -> bool:
    return username.lower() in _load_users()


def register(username: str, password: str) -> tuple:
    """Register a new user. Returns (success: bool, error_msg: str)."""
    users = _load_users()
    key = username.lower()
    if key in users:
        return False, "Username already taken — please choose another."
    salt = os.urandom(16).hex()
    users[key] = {
        "password_hash": _hash_password(password, salt),
        "salt": salt,
    }
    _save_users(users)
    return True, ""


def verify(username: str, password: str) -> tuple:
    """Verify credentials. Returns (success: bool, error_msg: str)."""
    users = _load_users()
    key = username.lower()
    if key not in users:
        return False, "Username not found."
    user = users[key]
    if _hash_password(password, user["salt"]) != user["password_hash"]:
        return False, "Incorrect password."
    return True, ""
