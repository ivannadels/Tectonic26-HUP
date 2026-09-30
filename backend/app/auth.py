"""Sessions, login rate limiting and the current_user dependency.

The role is ALWAYS read from the users table via the server-side session,
never from request bodies or headers.
"""
import hashlib
import hmac
import os
import secrets
import threading
import time
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, Response
from passlib.hash import bcrypt

from .db import conn

COOKIE = "tt_session"
SESSION_TTL = 8 * 3600
MAX_FAILURES, WINDOW = 5, 300
_SECRET = (os.getenv("SESSION_SECRET") or secrets.token_hex(32)).encode()
_DUMMY_HASH = bcrypt.hash(secrets.token_urlsafe(16))  # equalises timing for unknown users
_failures: dict[str, list[float]] = {}
_lock = threading.Lock()


@dataclass(frozen=True)
class User:
    username: str
    display_name: str
    role: str


def _token_hash(token: str) -> str:
    return hmac.new(_SECRET, token.encode(), hashlib.sha256).hexdigest()


def _recent_failures(username: str) -> list[float]:
    now = time.time()
    with _lock:
        _failures[username] = [t for t in _failures.get(username, []) if now - t < WINDOW]
        return _failures[username]


def rate_limited(username: str) -> bool:
    return len(_recent_failures(username)) >= MAX_FAILURES


def record_failure(username: str):
    with _lock:
        _failures.setdefault(username, []).append(time.time())


def clear_failures(username: str):
    with _lock:
        _failures.pop(username, None)


def verify_credentials(username: str, password: str) -> User | None:
    with conn() as c:
        row = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    ok = bcrypt.verify(password, row["password_hash"] if row else _DUMMY_HASH)
    if row and ok:
        return User(row["username"], row["display_name"], row["role"])
    return None


def create_session(response: Response, request: Request, username: str):
    token = secrets.token_urlsafe(32)
    with conn() as c:
        c.execute("DELETE FROM sessions WHERE expires_at < ?", (time.time(),))
        c.execute("INSERT INTO sessions VALUES (?,?,?)",
                  (_token_hash(token), username, time.time() + SESSION_TTL))
    secure = request.url.hostname not in ("localhost", "127.0.0.1")
    response.set_cookie(COOKIE, token, max_age=SESSION_TTL, httponly=True,
                        samesite="strict", secure=secure, path="/")


def destroy_session(request: Request, response: Response):
    token = request.cookies.get(COOKIE)
    if token:
        with conn() as c:
            c.execute("DELETE FROM sessions WHERE token_hash=?", (_token_hash(token),))
    response.delete_cookie(COOKIE, path="/")


def current_user(request: Request) -> User:
    token = request.cookies.get(COOKIE)
    if not token or len(token) > 128:
        raise HTTPException(401, "Not authenticated")
    with conn() as c:
        row = c.execute(
            "SELECT u.username, u.display_name, u.role FROM sessions s "
            "JOIN users u ON u.username = s.username WHERE s.token_hash=? AND s.expires_at > ?",
            (_token_hash(token), time.time()),
        ).fetchone()
    if not row:
        raise HTTPException(401, "Not authenticated")
    return User(row["username"], row["display_name"], row["role"])


def require_hr(user: User = Depends(current_user)) -> User:
    if user.role != "hr":
        raise HTTPException(403, "Not allowed")
    return user
