from datetime import date

from app.corpus import corpus
from app.resolver import Facts, resolve

C = corpus()
TODAY = date(2026, 9, 30)


def run(today=TODAY, **kw):
    f = Facts(internship_type=kw.pop("internship_type", "school"),
              start_date=date(2026, 10, 15), end_date=date(2027, 1, 15), **kw)
    return resolve(f, C["claims"], C["sources"], C["documents"], today, C["people"])


def status(r):
    return {i["document"]: i["status"] for i in r["items"]}


def test_demo_case():
    r = run()
    assert status(r) == {"A": "REQUIRED_PRACTICE", "B": "REQUIRED_LEGAL",
                         "C": "NEW_SINCE", "D": "CONDITIONAL"}
    assert len(r["stale_warnings"]) == 1
    w = r["stale_warnings"][0]
    assert w["source_id"] == "src-02" and w["missing_documents"] == ["C"]
    exc = {e["source_id"]: e["reason"] for e in r["excluded"]}
    assert exc == {"src-06": "Applies to Netherlands",
                   "src-07": "Applies to employees, not internships",
                   "src-08": "No owner, cannot verify who maintains this."}
    d = next(i for i in r["items"] if i["document"] == "D")
    assert d["condition"]["ask_person"]["name"] == "Marc Peeters"
    assert r["summary"] == ("4 documents: 2 legal requirements (1 new since 2026), 1 established "
                            "practice, 1 depends on the role. 1 outdated guidance found. 3 sources excluded.")


def test_desk_based_not_needed():
    d = next(i for i in run(manual_tasks=False)["items"] if i["document"] == "D")
    assert d["status"] == "NOT_NEEDED" and "Desk-based" in d["reason"] and d["deadline"] is None


def test_manual_tasks_required():
    assert status(run(manual_tasks=True))["D"] == "REQUIRED_LEGAL"


def test_voluntary_internship():
    s = status(run(internship_type="voluntary"))
    assert s == {"A": "REQUIRED_PRACTICE", "D": "CONDITIONAL"}


def test_unowned_source_never_evidence():
    for it in run()["items"]:
        ids = [it["headline_source"]["id"]] + [s["id"] for s in it["supporting_sources"]]
        assert "src-08" not in ids


def test_overdue_flag():
    r = run(today=date(2026, 10, 14))
    flags = {i["document"]: i["deadline"]["flag"] for i in r["items"]}
    assert flags["C"] == "overdue" and flags["D"] == "overdue"
    assert flags["A"] == "at_risk"
