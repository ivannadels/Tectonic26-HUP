import json
import uuid
from datetime import date, datetime
from typing import Any, Literal, Optional, Union

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .. import dialogue, email_draft
from ..auth import User, current_user
from ..corpus import corpus
from ..db import conn, row_to_case
from ..render import render_result
from ..resolver import Facts, resolve

router = APIRouter(prefix="/cases", tags=["cases"])


def run_resolver(facts: dict) -> dict:
    c = corpus()
    return resolve(Facts(**facts), c["claims"], c["sources"], c["documents"], date.today(), c["people"])


def load_case(case_id: str, user: User, owner_only: bool = False) -> dict:
    """Ownership check for every /cases/{id} route. Unknown or not-yours -> 404."""
    try:
        uuid.UUID(case_id, version=4)
    except ValueError:
        raise HTTPException(404, "Case not found")
    with conn() as c:
        row = c.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Case not found")
    case = row_to_case(row)
    is_owner = case["owner"] == user.username
    if not is_owner and (owner_only or user.role != "hr"):
        raise HTTPException(404, "Case not found")
    return case


def save_case(case: dict):
    with conn() as c:
        c.execute("UPDATE cases SET facts=?, messages=? WHERE id=?",
                  (json.dumps(case["facts"]), json.dumps(case["messages"]), case["id"]))


def has_result(facts: dict) -> bool:
    return dialogue.pending_fact(facts) is None


class CaseOut(BaseModel):
    id: str
    owner: str
    title: str
    created_at: str
    facts: dict
    messages: list
    has_result: bool


def case_out(case: dict) -> CaseOut:
    return CaseOut(**{k: case[k] for k in ("id", "owner", "title", "created_at", "facts", "messages")},
                   has_result=has_result(case["facts"]))


class CaseSummary(BaseModel):
    id: str
    owner: str
    title: str
    created_at: str


@router.post("", response_model=CaseOut)
def create_case(user: User = Depends(current_user)):
    case = {"id": str(uuid.uuid4()), "owner": user.username,
            "title": f"Intern onboarding, {datetime.now().strftime('%d %b %H:%M')}",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "facts": Facts().model_dump(mode="json"), "messages": []}
    with conn() as c:
        c.execute("INSERT INTO cases VALUES (?,?,?,?,?,?)",
                  (case["id"], case["owner"], case["title"], json.dumps(case["facts"]),
                   json.dumps(case["messages"]), case["created_at"]))
    return case_out(case)


@router.get("", response_model=list[CaseSummary])
def list_cases(user: User = Depends(current_user)):
    with conn() as c:
        if user.role == "hr":
            rows = c.execute("SELECT id, owner, title, created_at FROM cases ORDER BY created_at DESC")
        else:
            rows = c.execute("SELECT id, owner, title, created_at FROM cases WHERE owner=? "
                             "ORDER BY created_at DESC", (user.username,))
        return [CaseSummary(**dict(r)) for r in rows.fetchall()]


@router.get("/{case_id}", response_model=CaseOut)
def get_case(case_id: str, user: User = Depends(current_user)):
    return case_out(load_case(case_id, user))


class QuickReply(BaseModel):
    fact: Literal["internship_type", "dates", "manual_tasks"]
    value: Union[bool, str, dict, None] = None


class MessageIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: Optional[str] = Field(default=None, min_length=1, max_length=1000)
    quick_reply: Optional[QuickReply] = None

    @model_validator(mode="after")
    def exactly_one(self):
        if (self.text is None) == (self.quick_reply is None):
            raise ValueError("Send either text or quick_reply")
        return self


class TurnOut(BaseModel):
    case: CaseOut
    new_messages: list
    result: Optional[dict] = None


@router.post("/{case_id}/messages", response_model=TurnOut)
def post_message(case_id: str, body: MessageIn, user: User = Depends(current_user)):
    case = load_case(case_id, user, owner_only=True)
    try:
        facts, new = dialogue.step(case["facts"], case["messages"], body.text,
                                   body.quick_reply.model_dump() if body.quick_reply else None,
                                   run_resolver)
    except dialogue.DialogueError:
        raise HTTPException(400, "That answer isn't valid for the current question.")
    case["facts"], case["messages"] = facts, case["messages"] + new
    save_case(case)
    result = render_result(run_resolver(facts), user.role) if has_result(facts) else None
    return TurnOut(case=case_out(case), new_messages=new, result=result)


class FactPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fact: Literal["manual_tasks"]
    value: Optional[bool]


@router.patch("/{case_id}/facts", response_model=TurnOut)
def patch_fact(case_id: str, body: FactPatch, user: User = Depends(current_user)):
    case = load_case(case_id, user, owner_only=True)
    if not has_result(case["facts"]):
        raise HTTPException(400, "Answer the opening questions first.")
    _, label = dialogue.validate(body.fact, body.value)
    facts = {**case["facts"], body.fact: body.value}
    result = run_resolver(facts)
    new = [{"role": "user", "text": label}, dialogue.fact_message(facts, body.fact, result)]
    case["facts"], case["messages"] = facts, case["messages"] + new
    save_case(case)
    return TurnOut(case=case_out(case), new_messages=new, result=render_result(result, user.role))


@router.get("/{case_id}/result")
def get_result(case_id: str, user: User = Depends(current_user)) -> dict[str, Any]:
    case = load_case(case_id, user)
    if not has_result(case["facts"]):
        raise HTTPException(409, "Not enough information yet.")
    return render_result(run_resolver(case["facts"]), user.role)


class EmailOut(BaseModel):
    text: str
    polished: bool


@router.post("/{case_id}/email-draft", response_model=EmailOut)
def email(case_id: str, user: User = Depends(current_user)):
    case = load_case(case_id, user, owner_only=True)
    if not has_result(case["facts"]):
        raise HTTPException(409, "Not enough information yet.")
    return EmailOut(**email_draft.draft(run_resolver(case["facts"]), user.display_name))
