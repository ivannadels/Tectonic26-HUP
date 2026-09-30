import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from ..auth import User, current_user
from ..corpus import load
from ..db import conn
from ..render import render_source

router = APIRouter(prefix="/sources", tags=["sources"])


def get_source(source_id: str) -> dict:
    src = next((s for s in load("sources") if s["id"] == source_id), None)
    if not src:
        raise HTTPException(404, "Source not found")
    return src


@router.get("/{source_id}")
def read_source(source_id: str, user: User = Depends(current_user)) -> dict:
    return render_source(get_source(source_id), user.role)


class FlagIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note: str = Field(min_length=1, max_length=500)


@router.post("/{source_id}/flag")
def flag_source(source_id: str, body: FlagIn, user: User = Depends(current_user)) -> dict:
    src = get_source(source_id)
    flag_id = str(uuid.uuid4())
    with conn() as c:
        c.execute("INSERT INTO flags(id, source_id, source_owner, flagged_by, note, created_at) "
                  "VALUES (?,?,?,?,?,?)",
                  (flag_id, src["id"], src.get("owner"), user.username, body.note.strip(),
                   datetime.now().isoformat(timespec="seconds")))
    return {"id": flag_id, "ok": True}
