"""Seeds demo users. Passwords come from DEMO_PASSWORD, never from code."""
import os
import secrets

from passlib.hash import bcrypt

from .db import conn

USERS = [
    ("tom", "Tom Verbeke", "manager"),
    ("lina", "Lina Claes", "manager"),
    ("katrien", "Katrien De Smet", "hr"),
]


def seed_users():
    password = os.getenv("DEMO_PASSWORD")
    if not password:
        password = secrets.token_urlsafe(12)
        print(f"\n[TrustTrail] DEMO_PASSWORD not set. Generated password for all demo users: {password}\n",
              flush=True)
    hashed = bcrypt.hash(password)
    with conn() as c:
        for username, name, role in USERS:
            c.execute(
                "INSERT INTO users(username, display_name, role, password_hash) VALUES (?,?,?,?) "
                "ON CONFLICT(username) DO UPDATE SET display_name=excluded.display_name, "
                "role=excluded.role, password_hash=excluded.password_hash",
                (username, name, role, hashed),
            )
