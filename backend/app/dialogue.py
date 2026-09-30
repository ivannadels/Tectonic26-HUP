"""Deterministic slot-filling. Asks only questions whose answers change the result.

Order: internship_type -> dates -> (result shown). manual_tasks is asked later,
from the risk-analysis card. LLM output may only ever set the one fact being asked.
"""
from datetime import date
from typing import Any, Optional

from . import llm

CHOICES = {
    "internship_type": [
        {"label": "Yes, through school", "value": "school"},
        {"label": "No, outside their studies", "value": "voluntary"},
        {"label": "Via VDAB / Actiris / Forem", "value": "ibo"},
    ],
    "manual_tasks": [
        {"label": "Desk-based", "value": False},
        {"label": "Some manual tasks", "value": True},
        {"label": "Not sure", "value": None},
    ],
}
QUESTIONS = {
    "internship_type": "Is this internship part of their studies, arranged through their school?",
    "dates": "When does it start and end?",
}


class DialogueError(ValueError):
    pass


def pending_fact(facts: dict) -> Optional[str]:
    if facts.get("internship_type") is None:
        return "internship_type"
    if facts.get("start_date") is None:
        return "dates"
    return None


def ask(fact: str, prefix: str = "") -> dict:
    msg = {"role": "assistant", "text": (prefix + " " if prefix else "") + QUESTIONS[fact],
           "ask": {"fact": fact, "kind": "dates" if fact == "dates" else "choices"}}
    if fact in CHOICES:
        msg["ask"]["options"] = CHOICES[fact]
    return msg


def validate(fact: str, value: Any) -> tuple[dict, str]:
    """Return ({fact: value}, label) for a whitelisted fact, or raise DialogueError."""
    if fact in CHOICES:
        for opt in CHOICES[fact]:
            if opt["value"] == value and type(opt["value"]) is type(value):
                return {fact: value}, opt["label"]
        raise DialogueError("Unknown option")
    if fact == "dates":
        if not isinstance(value, dict):
            raise DialogueError("Dates required")
        try:
            start = date.fromisoformat(str(value.get("start_date")))
            end = date.fromisoformat(str(value.get("end_date")))
        except ValueError as e:
            raise DialogueError("Invalid date") from e
        if end < start:
            raise DialogueError("End date is before start date")
        return ({"start_date": start.isoformat(), "end_date": end.isoformat()},
                f"{start.strftime('%d %b %Y')} to {end.strftime('%d %b %Y')}")
    raise DialogueError("Fact not allowed")


def _from_llm(fact: str, text: str) -> Optional[tuple[dict, str]]:
    data = llm.parse_fact(fact, text)
    if not data:
        return None
    try:
        if fact == "internship_type":
            if data.get("answer") not in ("school", "voluntary", "ibo"):
                return None
            return validate(fact, data["answer"])
        if fact == "dates":
            return validate(fact, {"start_date": data.get("start_date"), "end_date": data.get("end_date")})
    except DialogueError:
        return None
    return None


def result_message(result: dict) -> dict:
    text = "Here's what you need. Each item on the right shows why it's needed and what backs it."
    if any(i["status"] == "CONDITIONAL" for i in result["items"]):
        text += " One item depends on the role; you can answer it right on its card."
    return {"role": "assistant", "text": text, "show_result": True}


def step(facts: dict, messages: list, text: Optional[str], quick: Optional[dict],
         resolve_fn) -> tuple[dict, list]:
    """Advance the dialogue by one user turn. Returns (facts, new_messages)."""
    new: list = []
    fact = pending_fact(facts)

    if quick is not None:
        qfact = quick.get("fact")
        allowed = fact if fact else "manual_tasks"
        if qfact != allowed:
            raise DialogueError("That question isn't open right now")
        update, label = validate(qfact, quick.get("value"))
        new.append({"role": "user", "text": label})
    else:
        new.append({"role": "user", "text": text})
        if not messages:
            return facts, new + [ask("internship_type",
                                     "Happy to help. Two quick questions so I only show what applies.")]
        if fact is None:
            return facts, new + [{"role": "assistant", "text": (
                "Your answer is in the panel on the right. If something depends on a detail you "
                "don't know yet, the card tells you who to ask.")}]
        parsed = _from_llm(fact, text or "")
        if not parsed:
            return facts, new + [ask(fact, "Please pick one of the options.")]
        update, _ = parsed

    facts = {**facts, **update}
    nxt = pending_fact(facts)
    if nxt:
        new.append(ask(nxt))
    elif quick is not None and quick.get("fact") == "manual_tasks":
        new.append(fact_message(facts, "manual_tasks", resolve_fn(facts)))
    else:
        new.append(result_message(resolve_fn(facts)))
    return facts, new


def fact_message(facts: dict, fact: str, result: dict) -> dict:
    if fact == "manual_tasks":
        d = next((i for i in result["items"] if i["document"] == "D"), None)
        if facts.get("manual_tasks") is None:
            text = "No problem. The risk analysis stays open; the card shows who can confirm."
        elif d:
            text = f"Noted. {d['reason']}"
        else:
            text = "Noted."
        return {"role": "assistant", "text": text, "show_result": True}
    return {"role": "assistant", "text": "Updated.", "show_result": True}
