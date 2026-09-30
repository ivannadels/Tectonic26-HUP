from fastapi import APIRouter, Depends, HTTPException

from ..auth import User, require_hr
from ..corpus import load
from ..db import conn

router = APIRouter(prefix="/flags", tags=["flags"])


@router.get("")
def list_flags(_: User = Depends(require_hr)) -> list[dict]:
    titles = {s["id"]: s["title"] for s in load("sources")}
    people = {p["id"]: p["name"] for p in load("people")}
    with conn() as c:
        rows = c.execute(
            "SELECT f.*, u.display_name AS flagged_by_name FROM flags f "
            "JOIN users u ON u.username = f.flagged_by ORDER BY f.resolved, f.created_at DESC"
        ).fetchall()
    return [{**dict(r), "resolved": bool(r["resolved"]), "source_title": titles.get(r["source_id"]),
             "source_owner_name": people.get(r["source_owner"], r["source_owner"])} for r in rows]


@router.post("/{flag_id}/resolve")
def resolve_flag(flag_id: str, user: User = Depends(require_hr)) -> dict:
    with conn() as c:
        cur = c.execute("UPDATE flags SET resolved=1, resolved_by=? WHERE id=?", (user.username, flag_id))
    if cur.rowcount == 0:
        raise HTTPException(404, "Flag not found")
    return {"ok": True}
