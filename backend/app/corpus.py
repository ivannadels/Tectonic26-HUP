"""Loads the committed demo corpus (read-only)."""
import json
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


@lru_cache
def load(name: str) -> list:
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


def corpus() -> dict:
    return {n: load(n) for n in ("documents", "sources", "claims", "people")}
