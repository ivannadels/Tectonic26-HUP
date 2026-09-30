"""TrustTrail resolver: the deterministic core.

Pure functions, no I/O. Given the known facts about a case and the structured
claims/sources/documents, decide which documents are needed, why, on what
authority, whether older guidance is outdated and what the deadlines are.
The LLM never touches this logic.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Literal, Optional

from pydantic import BaseModel

AUTHORITY_RANK = {"law": 4, "policy": 3, "hr_email": 2, "chat": 1}
AUTHORITY_LABEL = {"law": "Law", "policy": "Policy", "hr_email": "HR email", "chat": "Teams chat"}
COUNTRY_NAMES = {"BE": "Belgium", "NL": "Netherlands"}
CONTRACT_PLURAL = {"employee": "employees", "internship": "internships"}
SOURCE_KIND = {"hr_email": "email", "chat": "chat message", "policy": "policy"}
SHORT_NAMES = {
    "A": "IT & confidentiality acknowledgement",
    "B": "tripartite agreement",
    "C": "learning-objectives annex",
    "D": "workplace risk analysis",
}
# Human wording for a known condition outcome, keyed by fact then value.
CONDITION_OUTCOME = {
    "manual_tasks": {
        False: "Desk-based role, so no risk analysis is needed.",
        True: "The intern performs manual tasks, so the risk analysis is required.",
    }
}

REQUIRED_STATUSES = {"REQUIRED_LEGAL", "NEW_SINCE", "REQUIRED_PRACTICE"}


class Facts(BaseModel):
    country: str = "BE"
    contract_type: str = "internship"
    internship_type: Optional[Literal["school", "voluntary", "ibo"]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    manual_tasks: Optional[bool] = None
    paid: Optional[bool] = None


def _d(value: Any) -> Optional[date]:
    if value is None or isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _pretty(d: date) -> str:
    return f"{d.day} {d.strftime('%b %Y')}"


def scope_check(scope: dict, facts: Facts) -> Optional[str]:
    """Return None if in scope, otherwise a human reason for exclusion."""
    if scope.get("country") and scope["country"] != facts.country:
        return f"Applies to {COUNTRY_NAMES.get(scope['country'], scope['country'])}"
    if scope.get("contract_type") and scope["contract_type"] != facts.contract_type:
        other = CONTRACT_PLURAL.get(scope["contract_type"], scope["contract_type"])
        mine = CONTRACT_PLURAL.get(facts.contract_type, facts.contract_type)
        return f"Applies to {other}, not {mine}"
    types = scope.get("internship_type")
    if types and facts.internship_type and facts.internship_type not in types:
        return f"Applies only to {' / '.join(types)} internships"
    return None


def _source_ref(src: dict, people: dict) -> dict:
    owner = src.get("owner")
    return {
        "id": src["id"],
        "title": src["title"],
        "type": src["type"],
        "authority_label": AUTHORITY_LABEL[src["type"]],
        "date": src["date"],
        "owner": people.get(owner, {}).get("name", owner) if owner else None,
    }


def _deadline(doc: dict, facts: Facts, today: date) -> Optional[dict]:
    rule = doc.get("deadline_rule")
    if not rule or facts.start_date is None:
        return None
    due = facts.start_date + timedelta(days=rule["offset_days"])
    if due < today:
        flag = "overdue"
    elif (due - today).days <= 3:
        flag = "at_risk"
    else:
        flag = "ok"
    return {"date": due.isoformat(), "label": rule["label"], "flag": flag}


def resolve(facts: Facts, claims: list, sources: list, documents: list,
            today: date, people: Optional[list] = None) -> dict:
    people_by_id = {p["id"]: p for p in (people or [])}
    src_by_id = {s["id"]: s for s in sources}

    # 1 + 2. Scope filtering and unowned sources.
    usable: dict[str, dict] = {}
    excluded = []
    for s in sources:
        reason = scope_check(s["scope"], facts)
        if reason is None and s.get("owner") is None:
            reason = "No owner, cannot verify who maintains this."
        if reason:
            excluded.append({"source_id": s["id"], "title": s["title"], "type": s["type"],
                             "reason": reason, "mentions_documents": s.get("lists_documents", [])})
        else:
            usable[s["id"]] = s

    # Claims are evidence only when both the claim and its source are usable.
    live_claims = [c for c in claims
                   if c["source"] in usable and scope_check(c["applies_if"], facts) is None]

    items = []
    status_by_doc: dict[str, str] = {}
    for doc in documents:
        doc_claims = [c for c in live_claims if c["document"] == doc["id"]]
        if not doc_claims:
            continue  # NOT_APPLICABLE: omitted

        qualifying, pending, unmet = [], [], []
        for c in doc_claims:
            cond = c.get("condition")
            if not cond:
                qualifying.append(c)
                continue
            value = getattr(facts, cond["fact"], None)
            if value is None:
                pending.append(c)
            elif value == cond["equals"]:
                qualifying.append(c)
            else:
                unmet.append(c)

        law_q = [c for c in qualifying if c["authority"] == "law"]
        status, label, condition = None, None, None
        if law_q:
            status, label = "REQUIRED_LEGAL", "Legal requirement"
            for c in law_q:
                eff = _d(c.get("effective_from"))
                if eff and any(
                    s["id"] != c["source"] and _d(s["date"]) < eff
                    and doc["id"] not in s.get("lists_documents", [])
                    for s in usable.values()
                ):
                    status, label = "NEW_SINCE", f"New since {eff.isoformat()}"
                    break
        elif qualifying:
            status, label = "REQUIRED_PRACTICE", "Established practice, not written policy"
        elif pending:
            c = pending[0]
            cond = c["condition"]
            asker = people_by_id.get(cond.get("ask_person"), {})
            status, label = "CONDITIONAL", "Depends on the role"
            condition = {
                "fact": cond["fact"],
                "question": cond["question"],
                "if_yes": "Required",
                "if_no": "Not needed",
                "ask_person": {"id": cond.get("ask_person"), "name": asker.get("name"),
                               "role": asker.get("role")},
            }
        else:
            status, label = "NOT_NEEDED", "Not needed"

        evidence = qualifying or pending or unmet
        evidence_sources = sorted(
            {c["source"] for c in evidence},
            key=lambda sid: (AUTHORITY_RANK[src_by_id[sid]["type"]], src_by_id[sid]["date"]),
            reverse=True,
        )
        headline_id = evidence_sources[0]
        headline_claim = next(c for c in evidence if c["source"] == headline_id)

        if status == "NOT_NEEDED":
            cond = headline_claim["condition"]
            value = getattr(facts, cond["fact"])
            reason = CONDITION_OUTCOME.get(cond["fact"], {}).get(value, "Condition not met, so not needed.")
        elif status == "REQUIRED_LEGAL" and headline_claim.get("condition"):
            cond = headline_claim["condition"]
            reason = CONDITION_OUTCOME.get(cond["fact"], {}).get(True, headline_claim["reason"])
        else:
            reason = headline_claim["reason"]

        status_by_doc[doc["id"]] = status
        items.append({
            "document": doc["id"],
            "name": doc["name"],
            "provided_by": doc["provided_by"],
            "status": status,
            "status_label": label,
            "reason": reason,
            "headline_source": _source_ref(src_by_id[headline_id], people_by_id),
            "supporting_sources": [_source_ref(src_by_id[s], people_by_id) for s in evidence_sources[1:]],
            "condition": condition,
            "deadline": None if status == "NOT_NEEDED" else _deadline(doc, facts, today),
        })

    # 5. Stale-guidance detection.
    stale_warnings = []
    for s in usable.values():
        if s["type"] not in ("hr_email", "chat", "policy"):
            continue
        s_date = _d(s["date"])
        missing, rule_dates = [], []
        for c in live_claims:
            eff = _d(c.get("effective_from"))
            if (c["authority"] == "law" and eff and eff > s_date
                    and status_by_doc.get(c["document"]) in REQUIRED_STATUSES
                    and c["document"] not in s.get("lists_documents", [])
                    and c["document"] not in missing):
                missing.append(c["document"])
                rule_dates.append(eff)
        if missing:
            listed = " and ".join(SHORT_NAMES.get(d, d) for d in s.get("lists_documents", [])) or "nothing"
            added = " and ".join(SHORT_NAMES.get(d, d) for d in missing)
            kind = SOURCE_KIND[s["type"]]
            stale_warnings.append({
                "source_id": s["id"],
                "title": s["title"],
                "type": s["type"],
                "date": s["date"],
                "owner": people_by_id.get(s["owner"], {}).get("name", s["owner"]),
                "missing_documents": missing,
                "explanation": (
                    f"This {kind} ({_pretty(s_date)}) says the {listed} is all that's needed. "
                    f"A rule effective {_pretty(min(rule_dates))} added the {added}, "
                    f"so this guidance is outdated."
                ),
            })

    # 7. Trust summary.
    count = lambda *st: sum(1 for i in items if i["status"] in st)
    plural = lambda n, one, many: f"{n} {one if n == 1 else many}"
    legal, new = count("REQUIRED_LEGAL", "NEW_SINCE"), count("NEW_SINCE")
    parts = []
    if legal:
        new_years = sorted({i["status_label"][-10:-6] for i in items if i["status"] == "NEW_SINCE"})
        extra = f" ({new} new since {new_years[0]})" if new else ""
        parts.append(plural(legal, "legal requirement", "legal requirements") + extra)
    if count("REQUIRED_PRACTICE"):
        parts.append(plural(count("REQUIRED_PRACTICE"), "established practice", "established practices"))
    if count("CONDITIONAL"):
        parts.append(f"{count('CONDITIONAL')} depends on the role" if count("CONDITIONAL") == 1
                     else f"{count('CONDITIONAL')} depend on the role")
    if count("NOT_NEEDED"):
        parts.append(f"{count('NOT_NEEDED')} not needed")
    if items:
        summary = f"{plural(len(items), 'document', 'documents')}: {', '.join(parts)}."
    else:
        summary = "No documents in the knowledge base apply to this situation. Check with HR."
    if stale_warnings:
        summary += f" {len(stale_warnings)} outdated guidance found."
    summary += f" {plural(len(excluded), 'source', 'sources')} excluded."

    return {
        "facts": facts.model_dump(mode="json"),
        "items": items,
        "stale_warnings": stale_warnings,
        "excluded": excluded,
        "counts": {
            "legal": legal, "new_since": new, "practice": count("REQUIRED_PRACTICE"),
            "conditional": count("CONDITIONAL"), "not_needed": count("NOT_NEEDED"),
            "stale": len(stale_warnings), "excluded": len(excluded),
        },
        "summary": summary,
    }
