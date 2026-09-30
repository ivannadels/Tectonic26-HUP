"""The ONE place that decides what source text a role may see.

Managers only ever get `redacted_summary`. `raw_text` is added for HR only.
"""
from .corpus import load


def render_source(source: dict, role: str) -> dict:
    out = {k: source.get(k) for k in
           ("id", "title", "type", "date", "owner", "scope", "lists_documents", "contains_personal_data")}
    out["redacted_summary"] = source["redacted_summary"]
    if role == "hr":
        out["raw_text"] = source["raw_text"]
    return out


def render_result(result: dict, role: str) -> dict:
    """Attach role-appropriate source text to every source reference in a resolver result."""
    by_id = {s["id"]: s for s in load("sources")}

    def attach(ref: dict) -> dict:
        src = render_source(by_id[ref["id"] if "id" in ref else ref["source_id"]], role)
        extra = {"summary": src["redacted_summary"]}
        if "raw_text" in src:
            extra["raw_text"] = src["raw_text"]
        return {**ref, **extra}

    out = dict(result)
    out["items"] = [{**i, "headline_source": attach(i["headline_source"]),
                     "supporting_sources": [attach(s) for s in i["supporting_sources"]]}
                    for i in result["items"]]
    out["stale_warnings"] = [attach(w) for w in result["stale_warnings"]]
    out["excluded"] = [attach(e) for e in result["excluded"]]
    return out
