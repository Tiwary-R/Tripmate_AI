"""Simple, dependency-free user authentication backed by a local SQLite file.

Passwords are stored as salted PBKDF2-HMAC-SHA256 hashes, never in plain text.
Accounts persist across restarts regardless of whether PostgreSQL is configured.
"""

import hmac
import os
import re
import sqlite3
from datetime import datetime, timezone
from hashlib import pbkdf2_hmac
from pathlib import Path

DB_PATH = Path(os.getenv("USERS_DB_PATH", Path(__file__).resolve().parent.parent / "users.db"))
_PBKDF2_ROUNDS = 200_000
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,30}$")


class AuthError(Exception):
    """Raised for any expected login/registration problem; message is safe to show the user."""


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    dk = pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ROUNDS)
    return f"{salt.hex()}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split("$", 1)
        dk = pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), _PBKDF2_ROUNDS)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(dk.hex(), dk_hex)


class UserStore:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS users (
                    username      TEXT PRIMARY KEY,
                    full_name     TEXT,
                    password_hash TEXT NOT NULL,
                    created_at    TEXT NOT NULL
                )"""
            )

    def register(self, username: str, password: str, full_name: str = "") -> None:
        username = (username or "").strip()
        if not _USERNAME_RE.match(username):
            raise AuthError("Username must be 3-30 characters: letters, numbers, dot, dash or underscore.")
        if len(password or "") < 6:
            raise AuthError("Password must be at least 6 characters.")
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO users (username, full_name, password_hash, created_at) VALUES (?, ?, ?, ?)",
                    (username, full_name.strip(), _hash_password(password), datetime.now(timezone.utc).isoformat()),
                )
        except sqlite3.IntegrityError:
            raise AuthError(f"Username '{username}' is already taken.")

    def authenticate(self, username: str, password: str) -> dict:
        username = (username or "").strip()
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if row is None or not _verify_password(password, row["password_hash"]):
            raise AuthError("Invalid username or password.")
        return {"username": row["username"], "full_name": row["full_name"]}

    def user_count(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
