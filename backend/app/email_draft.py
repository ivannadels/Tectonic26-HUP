"""Builds the paste-ready email to the intern from resolver output.

Contains no source details, owners or other people's names.
"""
from datetime import date

from . import llm

INTERN_QUESTIONS = {
    "manual_tasks": "- Do you expect any manual tasks in this internship, or will it be fully "
                    "desk-based? If there are manual tasks, we'll send a workplace risk analysis "
                    "to your school before you start.",
}
REQUIRED = {"REQUIRED_LEGAL", "NEW_SINCE", "REQUIRED_PRACTICE"}


def _fmt(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%b %Y')}"


def build(result: dict, sender_name: str) -> tuple[str, list[str]]:
    groups = {"intern": [], "school": [], "manager": []}
    must_keep: list[str] = []
    questions = []
    for it in result["items"]:
        if it["status"] in REQUIRED:
            due = it.get("deadline")
            line = f"- {it['name']}" + (f", by {_fmt(due['date'])}" if due else "")
            groups[it["provided_by"]].append((due["date"] if due else "9999", line))
            must_keep.append(it["name"])
            if due:
                must_keep.append(_fmt(due["date"]))
        elif it["status"] == "CONDITIONAL" and it.get("condition"):
            questions.append(INTERN_QUESTIONS.get(it["condition"]["fact"],
                                                  f"- {it['condition']['question']}"))

    start = result["facts"].get("start_date")
    parts = ["Hi,", "",
             "We're looking forward to welcoming you" + (f" on {_fmt(start)}" if start else "") + ". "
             "To get everything ready in time, here is what we need."]
    sections = [
        ("From you", groups["intern"]),
        ("Please forward to your school coordinator", groups["school"]),
        ("What we're handling on our side", groups["manager"]),
    ]
    for title, lines in sections:
        if lines:
            parts += ["", f"{title}:"] + [l for _, l in sorted(lines)]
    if questions:
        parts += ["", "One question for you:"] + questions
    parts += ["", "If anything is unclear, just reply to this email.", "", "Best regards,", sender_name]
    return "\n".join(parts), must_keep


def draft(result: dict, sender_name: str) -> dict:
    text, must_keep = build(result, sender_name)
    polished = llm.polish_email(text, must_keep)
    return {"text": polished or text, "polished": polished is not None}
