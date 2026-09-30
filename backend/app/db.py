"""SQLite storage (stdlib sqlite3). One short-lived connection per operation."""
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = os.getenv("DB_PATH", str(Path(__file__).resolve().parent.parent / "trusttrail.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  username TEXT PRIMARY KEY, display_name TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('manager','hr')), password_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY, username TEXT NOT NULL REFERENCES users(username),
  expires_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS cases (
  id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES users(username),
  title TEXT NOT NULL, facts TEXT NOT NULL, messages TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS flags (
  id TEXT PRIMARY KEY, source_id TEXT NOT NULL, source_owner TEXT,
  flagged_by TEXT NOT NULL REFERENCES users(username), note TEXT NOT NULL,
  created_at TEXT NOT NULL, resolved INTEGER NOT NULL DEFAULT 0, resolved_by TEXT);
"""


@contextmanager
def conn():
    c = sqlite3.connect(os.getenv("DB_PATH", DB_PATH))
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db():
    with conn() as c:
        c.executescript(SCHEMA)


def row_to_case(r: sqlite3.Row) -> dict:
    d = dict(r)
    d["facts"] = json.loads(d["facts"])
    d["messages"] = json.loads(d["messages"])
    return d
