import os
import tempfile

import pytest

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
PW = os.environ["DEMO_PASSWORD"]

from fastapi.testclient import TestClient  # noqa: E402

from app import auth as auth_mod  # noqa: E402
from app.main import app  # noqa: E402


def client(username=None):
    c = TestClient(app, base_url="http://localhost")
    c.__enter__()
    if username:
        r = c.post("/api/auth/login", json={"username": username, "password": PW})
        assert r.status_code == 200, r.text
    return c


def demo_case(c):
    cid = c.post("/api/cases").json()["id"]
    c.post(f"/api/cases/{cid}/messages", json={"text": "What do I need from the intern?"})
    c.post(f"/api/cases/{cid}/messages", json={"quick_reply": {"fact": "internship_type", "value": "school"}})
    r = c.post(f"/api/cases/{cid}/messages", json={"quick_reply": {"fact": "dates", "value": {
        "start_date": "2026-10-15", "end_date": "2027-01-15"}}})
    assert r.json()["result"] is not None
    return cid


def test_login_generic_error_and_rate_limit():
    c = client()
    bad = c.post("/api/auth/login", json={"username": "nobody", "password": "x"})
    wrong = c.post("/api/auth/login", json={"username": "lina", "password": "x"})
    assert bad.status_code == wrong.status_code == 401
    assert bad.json() == wrong.json()
    for _ in range(4):
        c.post("/api/auth/login", json={"username": "lina", "password": "x"})
    assert c.post("/api/auth/login", json={"username": "lina", "password": PW}).status_code == 429
    auth_mod.clear_failures("lina")


def test_session_cookie_flags():
    c = client()
    r = c.post("/api/auth/login", json={"username": "tom", "password": PW})
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie


def test_unauthenticated_rejected():
    c = client()
    assert c.get("/api/cases").status_code == 401
    assert c.get("/api/sources/src-01").status_code == 401


def test_idor_other_managers_case_is_404():
    lina, tom = client("lina"), client("tom")
    cid = demo_case(lina)
    for method, path, kw in [("get", "", {}), ("get", "/result", {}),
                             ("post", "/messages", {"json": {"text": "hi"}}),
                             ("patch", "/facts", {"json": {"fact": "manual_tasks", "value": False}}),
                             ("post", "/email-draft", {})]:
        assert getattr(tom, method)(f"/api/cases/{cid}{path}", **kw).status_code == 404
    assert cid not in [x["id"] for x in tom.get("/api/cases").json()]


def test_role_comes_from_session_only():
    c = client()
    c.post("/api/auth/login", json={"username": "tom", "password": PW, "role": "hr"})
    assert c.get("/api/auth/me").json()["role"] == "manager"
    assert c.get("/api/flags", headers={"X-Role": "hr"}).status_code == 403


def test_flags_hr_only():
    tom, katrien = client("tom"), client("katrien")
    fid = tom.post("/api/sources/src-02/flag", json={"note": "Outdated since 2026"}).json()["id"]
    assert tom.get("/api/flags").status_code == 403
    assert tom.post(f"/api/flags/{fid}/resolve").status_code == 403
    assert any(f["id"] == fid for f in katrien.get("/api/flags").json())
    assert katrien.post(f"/api/flags/{fid}/resolve").status_code == 200


def test_manager_never_gets_raw_text():
    tom, katrien = client("tom"), client("katrien")
    cid = demo_case(tom)
    raw = "Priya Nair"
    for path in [f"/api/cases/{cid}/result", "/api/sources/src-01"]:
        assert raw not in tom.get(path).text
    assert raw not in tom.post(f"/api/cases/{cid}/email-draft").text
    assert raw not in tom.patch(f"/api/cases/{cid}/facts", json={"fact": "manual_tasks", "value": False}).text
    assert raw in katrien.get("/api/sources/src-01").text
    assert raw in katrien.get(f"/api/cases/{cid}/result").text  # HR may view any case


@pytest.mark.parametrize("body", [
    {"fact": "internship_type", "value": "voluntary"},
    {"fact": "owner", "value": "lina"},
    {"fact": "manual_tasks", "value": "yes please"},
    {"fact": "manual_tasks", "value": False, "role": "hr"},
])
def test_patch_facts_whitelist(body):
    tom = client("tom")
    cid = demo_case(tom)
    assert tom.patch(f"/api/cases/{cid}/facts", json=body).status_code == 422


def test_patch_facts_resolves_d():
    tom = client("tom")
    cid = demo_case(tom)
    r = tom.patch(f"/api/cases/{cid}/facts", json={"fact": "manual_tasks", "value": False}).json()
    d = next(i for i in r["result"]["items"] if i["document"] == "D")
    assert d["status"] == "NOT_NEEDED"


def test_quick_reply_cannot_set_other_facts():
    tom = client("tom")
    cid = tom.post("/api/cases").json()["id"]
    tom.post(f"/api/cases/{cid}/messages", json={"text": "hi"})
    r = tom.post(f"/api/cases/{cid}/messages", json={"quick_reply": {"fact": "manual_tasks", "value": True}})
    assert r.status_code == 400


def test_input_limits():
    tom = client("tom")
    cid = tom.post("/api/cases").json()["id"]
    assert tom.post(f"/api/cases/{cid}/messages", json={"text": "x" * 1001}).status_code == 422
    assert tom.post("/api/sources/src-02/flag", json={"note": "x" * 501}).status_code == 422


def test_logout_kills_session():
    tom = client("tom")
    tom.post("/api/auth/logout")
    assert tom.get("/api/auth/me").status_code == 401
