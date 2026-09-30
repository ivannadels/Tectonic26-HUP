# TrustTrail: Build Specification

> **For the AI agent building this.** This file is the complete spec. Build exactly what is described here, in the order given in §12. Do not add features that aren't listed. The corpus in §6 is deliberately designed for the demo story, so do not rewrite it, shorten it or "improve" it. Where something is unspecified, pick the simplest option and note the choice in the README.
>
> *"TrustTrail" is a working name. Rename freely.*

---

## 1. Context

**Event:** Tectonic Hackathon, 30 Sep 2026, SD Worx challenge.

**Challenge title:** *Unlock the Knowledge Within: Find it. Understand it. Trust it.*
"How might we turn fragmented organisational knowledge into a trusted shared resource?"

The brief's key points:
- Knowledge at SD Worx is scattered across policies, manuals, emails, Teams chats and people's heads.
- Finding information is not the problem. A search returns ten answers and an AI assistant can summarise them. **The hard problem is whether an answer is reliable, current and relevant to this situation.**
- Build one focused proof of concept (one role, one workflow, one trust signal) that moves a person from *"I found something"* to *"I understand why I can rely on it."*
- The strongest ideas make trust visible and explainable, not a black box.
- Inspiration areas: **Trust**, **Capture**, **Detect**, **Connect**.

**Judging:** Creativity 30% · Technical ability 30% · Fit to challenge 30% · Security 10% (Aikido AI Code Audit: business logic flaws, IDOR, authentication, authorization).

**Hard rules:** public GitHub repo; no passwords, API keys or confidential data in the repo; README explaining the project, how to run it and what's unfinished; demo video under 3 minutes; no changes after submission.

---

## 2. The product in one paragraph

An SD Worx hiring manager needs to onboard an intern, and HR is busy. He asks an internal assistant: *"What documents do I need from the intern, and by when?"* The assistant asks a few simple questions to classify the internship, then gives the answer. **TrustTrail is the layer that explains that answer.** Every document in it is labelled with *why* it's required, *what kind of authority* backs it (law, policy, HR email, Teams chat), whether older guidance is now **outdated**, and, for items that depend on an unknown fact, **which fact decides it and who to ask**. Sources containing other people's personal data are shown to managers only as redacted summaries.

### The demo story (the corpus must produce exactly this)

For a school internship starting 15 Oct 2026, the answer lists four documents:

| Doc | What | Why it's needed | Trust label |
|---|---|---|---|
| **A** | IT & confidentiality acknowledgement | Found only in an HR **Teams conversation** two months ago, while onboarding another intern. Interns may see client payroll data. | **Required: established practice** (not written policy) |
| **B** | Tripartite internship agreement | **Legal** requirement for school internships | **Required: legal** |
| **C** | Learning-objectives annex | **Legal** requirement **new since 1 Jan 2026**. An HR email from March 2025 asked interns for B only; that email is now **outdated**. | **New since 2026-01-01** + stale-guidance warning |
| **D** | Workplace risk analysis (sent by the host to the school) | **Only if** the intern does manual tasks | **Conditional**: deciding fact, both outcomes, who to ask |

Plus an **Excluded** section showing sources that were deliberately ignored: a Dutch policy (wrong country), the employee onboarding checklist (wrong contract type), and an **unowned** checklist.

**The live demo moment:** D starts as *Conditional*. The manager answers "desk-based, no manual tasks", and D flips to *Not needed*, with the reason shown.

---

## 3. Users and roles

| Role | Sees | Can do |
|---|---|---|
| `manager` | Own cases only. Sources as **redacted summaries**. | Create cases, chat, view results, draft the email, flag a source as outdated |
| `hr` | All cases. Full raw source text. | Everything a manager can, plus view the outdated-guidance inbox and resolve flags |

Seed users:

| Username | Display name | Role |
|---|---|---|
| `tom` | Tom Verbeke | manager |
| `lina` | Lina Claes | manager (exists to test that Tom cannot see Lina's cases) |
| `katrien` | Katrien De Smet | hr |

**Passwords:** never hardcoded. Read from env var `DEMO_PASSWORD`. If it's unset, generate a random password at startup and print it once to the server console.

---

## 4. Tech stack

Keep it boring and reliable.

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLite via SQLAlchemy (or `sqlite3`), `passlib[bcrypt]` for password hashing, `pytest`
- **Frontend:** React + Vite + TypeScript, plain CSS or Tailwind. No heavy UI kit.
- **LLM:** Gemini on Google Cloud Vertex AI via the `google-genai` Python SDK (`genai.Client(vertexai=True, project=..., location=...)`). Put the model name in an env var (`GEMINI_MODEL`), set to a current Gemini Flash model available in the project. **Verify the model ID in the Vertex AI Model Garden; don't guess it.**
- **Optional:** ElevenLabs text-to-speech (§11, stretch goal only)

### The design principle, and why it matters

**Code decides; the LLM only phrases.**

- Which documents are required, their status, staleness and deadlines are computed by a **deterministic resolver** (§7) from structured claims. This is what makes the explanations exact and the demo repeatable.
- The LLM is used for only two things: (1) parsing a free-text reply into a fact, and (2) polishing the email draft.
- **Everything must work with `USE_LLM=false`.** Quick-reply buttons handle the questions and a template handles the email. That is the fallback if GCP credentials fail during the demo.

---

## 5. Repository structure

```
/
├── README.md
├── BUILD_SPEC.md              ← this file
├── .gitignore                 ← must include .env, *.db, node_modules, __pycache__, service-account*.json
├── .env.example               ← variable names only, no values
├── backend/
│   ├── app/
│   │   ├── main.py            ← FastAPI app, routers, CORS
│   │   ├── auth.py            ← login, sessions, current_user dependency, role checks
│   │   ├── db.py              ← models + session
│   │   ├── seed.py            ← users, people, sources
│   │   ├── resolver.py        ← THE CORE (§7), pure functions, no I/O
│   │   ├── dialogue.py        ← slot-filling state machine (§8)
│   │   ├── llm.py             ← Gemini wrapper with fallbacks
│   │   ├── email_draft.py
│   │   └── routes/            ← auth.py, cases.py, sources.py, flags.py
│   ├── data/
│   │   ├── sources.json       ← §6.2
│   │   ├── claims.json        ← §6.3
│   │   ├── documents.json     ← §6.1
│   │   └── people.json        ← §6.4
│   ├── scripts/
│   │   └── extract_claims.py  ← shows how claims would be LLM-extracted at scale (not run live)
│   ├── tests/
│   │   ├── test_resolver.py
│   │   └── test_security.py
│   └── requirements.txt
└── frontend/
    ├── src/ …
    └── package.json
```

---

## 6. The synthetic knowledge corpus

> ⚠️ **All data is synthetic.** Put a banner in the README and a footer in the UI: *"Demo corpus. Synthetic data. Source C describes a fictional regulation."*
> B and D are loosely based on public Belgian guidance (school internships use a tripartite agreement; a risk analysis goes to the school when the intern does manual work). **C is fictional**, so never present it as real law.

### 6.1 `documents.json`: the document catalogue

```json
[
  { "id": "A", "name": "IT & confidentiality acknowledgement", "provided_by": "intern",  "deadline_rule": { "anchor": "start_date", "offset_days": -1, "label": "before day one" } },
  { "id": "B", "name": "Tripartite internship agreement (school, intern, SD Worx)", "provided_by": "school", "deadline_rule": { "anchor": "start_date", "offset_days": -1, "label": "signed before the first day" } },
  { "id": "C", "name": "Learning-objectives annex, signed by the school supervisor", "provided_by": "school", "deadline_rule": { "anchor": "start_date", "offset_days": -3, "label": "3 days before start" } },
  { "id": "D", "name": "Workplace risk analysis, sent to the school", "provided_by": "manager", "deadline_rule": { "anchor": "start_date", "offset_days": -10, "label": "10 days before start (internal guideline)" } }
]
```

`provided_by` drives the UI grouping: **"From the intern" / "From the school" / "On you"**.
Deadline = `start_date + offset_days`. If the deadline is already in the past relative to today, mark it **overdue** (red). If it falls within 3 days, mark it **at risk** (amber).

### 6.2 `sources.json`: the raw sources

Every source has `id, title, type, date, owner (nullable), scope, lists_documents, raw_text, redacted_summary, contains_personal_data`.

`type` ∈ `law | policy | hr_email | chat`. `scope` holds `country`, `contract_type` and optionally `internship_type`.

```json
[
  {
    "id": "src-01",
    "title": "HR Onboarding channel (Teams)",
    "type": "chat",
    "date": "2026-07-28",
    "owner": "katrien",
    "scope": { "country": "BE", "contract_type": "internship", "internship_type": ["school", "voluntary"] },
    "lists_documents": ["A"],
    "contains_personal_data": true,
    "raw_text": "Katrien De Smet: @Jonas for Priya Nair's start on Monday, don't forget the IT & confidentiality acknowledgement. She'll be working in client payroll files. Last year an intern got system access before signing it and we had to report it. From now on every intern signs it before day one.\nJonas Wouters: Noted, I'll add it to my list.",
    "redacted_summary": "HR practice since July 2026: every intern signs the IT & confidentiality acknowledgement before their first day, because interns may access client payroll data. Stated by HR in a Teams onboarding conversation."
  },
  {
    "id": "src-02",
    "title": "Email: 'Intern onboarding, what we need'",
    "type": "hr_email",
    "date": "2025-03-10",
    "owner": "katrien",
    "scope": { "country": "BE", "contract_type": "internship", "internship_type": ["school"] },
    "lists_documents": ["B"],
    "contains_personal_data": false,
    "raw_text": "Hi all, for school interns please make sure we receive the signed tripartite internship agreement before the start date. That's all we need from them. Thanks! HR Shared Services",
    "redacted_summary": "HR email (March 2025): for school interns, only the signed tripartite agreement is needed."
  },
  {
    "id": "src-03",
    "title": "Legal note: School internships",
    "type": "law",
    "date": "2019-09-01",
    "owner": "legal-team",
    "scope": { "country": "BE", "contract_type": "internship", "internship_type": ["school"] },
    "lists_documents": ["B"],
    "contains_personal_data": false,
    "raw_text": "A school internship is governed by a written tripartite agreement between the student, the educational institution and the host organisation, signed before the internship starts.",
    "redacted_summary": "School internships require a tripartite agreement (student, school, host) signed before the start."
  },
  {
    "id": "src-04",
    "title": "Circular 2026/03: Learning-objectives annex (FICTIONAL)",
    "type": "law",
    "date": "2025-11-12",
    "effective_from": "2026-01-01",
    "owner": "legal-team",
    "scope": { "country": "BE", "contract_type": "internship", "internship_type": ["school"] },
    "lists_documents": ["C"],
    "contains_personal_data": false,
    "raw_text": "[FICTIONAL, demo corpus] From 1 January 2026, host organisations must hold a learning-objectives annex, signed by the school supervisor, for every school internship before it starts.",
    "redacted_summary": "[Fictional] Since 1 Jan 2026, a learning-objectives annex signed by the school supervisor is required for school internships."
  },
  {
    "id": "src-05",
    "title": "Prevention note: Interns performing manual tasks",
    "type": "law",
    "date": "2021-02-15",
    "owner": "prevention",
    "scope": { "country": "BE", "contract_type": "internship", "internship_type": ["school", "voluntary"] },
    "lists_documents": ["D"],
    "contains_personal_data": false,
    "raw_text": "If an intern will perform manual tasks, the host must carry out a workplace risk analysis and send it to the educational institution before the internship starts. Desk-based roles do not require it.",
    "redacted_summary": "A workplace risk analysis is required, and must be sent to the school, only if the intern performs manual tasks."
  },
  {
    "id": "src-06",
    "title": "Stagiairs Nederland: onboarding",
    "type": "policy",
    "date": "2024-05-02",
    "owner": "hr-nl",
    "scope": { "country": "NL", "contract_type": "internship" },
    "lists_documents": [],
    "contains_personal_data": false,
    "raw_text": "Voor stagiairs in Nederland: stageovereenkomst en een VOG (Verklaring Omtrent het Gedrag) vóór de startdatum.",
    "redacted_summary": "Netherlands intern onboarding: internship agreement and a certificate of conduct (VOG)."
  },
  {
    "id": "src-07",
    "title": "Employee onboarding checklist",
    "type": "policy",
    "date": "2025-09-01",
    "owner": "katrien",
    "scope": { "country": "BE", "contract_type": "employee" },
    "lists_documents": [],
    "contains_personal_data": false,
    "raw_text": "New employees: signed employment contract, bank account details for payroll, Dimona declaration before the first working hour.",
    "redacted_summary": "Employee onboarding: employment contract, bank details, Dimona declaration."
  },
  {
    "id": "src-08",
    "title": "Onboarding checklist v3 (shared drive)",
    "type": "policy",
    "date": "2023-01-20",
    "owner": null,
    "scope": { "country": "BE", "contract_type": "internship", "internship_type": ["school"] },
    "lists_documents": ["B"],
    "contains_personal_data": false,
    "raw_text": "Interns: tripartite agreement, bank details, copy of ID.",
    "redacted_summary": "Undated-looking checklist on the shared drive: tripartite agreement, bank details, ID copy. No owner."
  }
]
```

### 6.3 `claims.json`: structured claims (what the resolver consumes)

These are hand-authored for the demo. `scripts/extract_claims.py` shows how an LLM would produce them from `sources.json` at scale, but it is **not** run live. Committed claims make the demo deterministic.

```json
[
  { "id": "c-A1", "document": "A", "source": "src-01", "authority": "chat",
    "applies_if": { "country": "BE", "contract_type": "internship", "internship_type": ["school", "voluntary"] },
    "condition": null,
    "reason": "Interns may access client payroll data, so HR requires the acknowledgement before any system access." },

  { "id": "c-B1", "document": "B", "source": "src-03", "authority": "law",
    "applies_if": { "country": "BE", "contract_type": "internship", "internship_type": ["school"] },
    "condition": null,
    "reason": "School internships are governed by a tripartite agreement signed before the start." },

  { "id": "c-C1", "document": "C", "source": "src-04", "authority": "law", "effective_from": "2026-01-01",
    "applies_if": { "country": "BE", "contract_type": "internship", "internship_type": ["school"] },
    "condition": null,
    "reason": "[Fictional regulation] Required for school internships since 1 Jan 2026." },

  { "id": "c-D1", "document": "D", "source": "src-05", "authority": "law",
    "applies_if": { "country": "BE", "contract_type": "internship", "internship_type": ["school", "voluntary"] },
    "condition": { "fact": "manual_tasks", "equals": true,
                   "question": "Will the intern perform any manual tasks, or is the role desk-based?",
                   "ask_person": "prevention" },
    "reason": "A risk analysis is only required when the intern performs manual tasks." }
]
```

### 6.4 `people.json`

```json
[
  { "id": "katrien",    "name": "Katrien De Smet", "role": "HR Business Partner, Brussels" },
  { "id": "legal-team", "name": "Legal Knowledge Team", "role": "Maintains legal notes" },
  { "id": "prevention", "name": "Marc Peeters", "role": "Prevention Advisor" },
  { "id": "hr-nl",      "name": "HR Netherlands", "role": "NL HR team" }
]
```

---

## 7. The resolver (the core; make this excellent)

`resolver.py` exposes a pure function:

```python
def resolve(facts: Facts, claims, sources, documents, today: date) -> Result
```

### Facts

```python
class Facts(BaseModel):
    country: str = "BE"                 # fixed for the demo
    contract_type: str = "internship"   # fixed for the demo
    internship_type: Literal["school", "voluntary", "ibo"] | None
    start_date: date | None
    end_date: date | None
    manual_tasks: bool | None           # None = unknown
    paid: bool | None
```

### Algorithm

1. **Scope filtering.** A source or claim is *in scope* if the facts match `country`, `contract_type` and `internship_type` (if the scope specifies it). Every out-of-scope source goes to `excluded` with a human reason: *"Applies to Netherlands"*, *"Applies to employees, not internships"*.
2. **Unowned sources.** A source with `owner == null` is **never used as evidence**. Add it to `excluded` with reason *"No owner, cannot verify who maintains this."* Still show which documents it mentions.
3. **Per document.** Collect in-scope claims for that document, then assign a status:
   - `REQUIRED_LEGAL`: at least one `law` claim applies and its condition (if any) is met.
   - `REQUIRED_PRACTICE`: only `chat` or `hr_email` claims support it. Label it *"Established practice, not written policy"* and show the source owner.
   - `NEW_SINCE`: a qualifying `law` claim has `effective_from`, and `effective_from` is later than the date of at least one in-scope, owned source that covers the same case scope but does **not** list this document. The badge reads *"New since 2026-01-01"*. This takes precedence over `REQUIRED_LEGAL` for display, and still counts as required.
   - `CONDITIONAL`: the claim has a `condition` whose `fact` is `None` in `facts`. Output the question, both outcomes (*"If yes: required. If no: not needed."*) and the person to ask.
   - `NOT_NEEDED`: the condition's fact is known and does not match. Keep the reason visible ("Desk-based role, so no risk analysis needed").
   - `NOT_APPLICABLE`: there are no in-scope claims. Omit it.
4. **Authority ranking**, used when showing the multiple sources for one document and deciding the headline source: `law (4) > policy (3) > hr_email (2) > chat (1)`. Within the same tier, newer wins.
5. **Stale-guidance detection.** For each in-scope, owned source `S` with `type` in `hr_email | chat | policy`: if a law claim with `effective_from > S.date` requires a document that `S.lists_documents` does not include, emit a `stale_warning`:
   - `source_id`, `title`, `date`, `owner`
   - `missing_documents: ["C"]`
   - `explanation`: *"This email (10 Mar 2025) says the tripartite agreement is all that's needed. A rule effective 1 Jan 2026 added the learning-objectives annex, so this guidance is outdated."*
6. **Deadlines.** For each required or conditional document with a known `start_date`: compute the deadline and a flag of `ok | at_risk | overdue` relative to `today`.
7. **Trust summary.** Count the items by status, and produce a single sentence: *"4 documents: 2 legal requirements (1 new since 2026), 1 established practice, 1 depends on the role. 1 outdated guidance found. 3 sources excluded."*

### Output schema

```json
{
  "facts": { },
  "items": [
    {
      "document": "C",
      "name": "Learning-objectives annex, signed by the school supervisor",
      "provided_by": "school",
      "status": "NEW_SINCE",
      "status_label": "New since 2026-01-01",
      "reason": "…",
      "headline_source": { "id": "src-04", "type": "law", "date": "2025-11-12", "owner": "Legal Knowledge Team" },
      "supporting_sources": [ ],
      "condition": null,
      "deadline": { "date": "2026-10-12", "label": "3 days before start", "flag": "ok" }
    }
  ],
  "stale_warnings": [ ],
  "excluded": [ { "source_id": "src-06", "title": "…", "reason": "Applies to Netherlands" } ],
  "summary": "…"
}
```

### Required tests (`tests/test_resolver.py`)

1. **The demo case.** School internship, start 2026-10-15, `manual_tasks=None` → A `REQUIRED_PRACTICE`, B `REQUIRED_LEGAL`, C `NEW_SINCE`, D `CONDITIONAL`; one stale warning on `src-02` missing `["C"]`; src-06, src-07 and src-08 excluded with the correct reasons.
2. Same case with `manual_tasks=False` → D `NOT_NEEDED` with its reason.
3. Same case with `manual_tasks=True` → D `REQUIRED_LEGAL`.
4. A voluntary internship → B and C are not applicable (they are school-only), A applies, D is conditional.
5. The unowned source (src-08) never appears as evidence for B.
6. With `today` after a deadline → that item's `flag == "overdue"`.

---

## 8. The conversation (slot filling)

A deterministic state machine in `dialogue.py`. It asks only the questions whose answers change the result, in this order, and skips any already known.

| # | Fact | Question shown | Quick replies |
|---|---|---|---|
| 1 | `internship_type` | "Is this internship part of their studies, arranged through their school?" | `Yes, through school` · `No, outside their studies` · `Via VDAB / Actiris / Forem` |
| 2 | `start_date`, `end_date` | "When does it start and end?" | Two date pickers |
| 3 | `manual_tasks` | *Asked only after the first result is shown*, via the D card's "Answer this" button | `Desk-based` · `Some manual tasks` · `Not sure` |

- After questions 1 and 2, **show the result immediately**, with D as `CONDITIONAL`. Don't ask question 3 up front. The demo moment is answering it from the card and watching D resolve.
- "Not sure" leaves the fact as `None`, and the card keeps showing who to ask (Marc Peeters, Prevention Advisor).
- Free-text replies: if `USE_LLM=true`, call Gemini to parse the text into the fact with a strict JSON schema. On any failure, reply *"Please pick one of the options"* and show the buttons again. **Never let LLM output set anything except the one fact currently being asked.**
- The opening message is whatever the user types (e.g. *"HR is busy, what documents do I need from the intern and by when?"*). The assistant replies with a one-line acknowledgement plus question 1.

---

## 9. Backend API

All routes live under `/api`. All except login require a valid session. Use Pydantic models for every request and response body.

| Method | Path | Who | Notes |
|---|---|---|---|
| POST | `/auth/login` | anyone | Username and password → sets the session cookie. Rate limit: 5 failures per username per 5 minutes. |
| POST | `/auth/logout` | user | Deletes the server-side session |
| GET | `/auth/me` | user | `{ username, display_name, role }` |
| POST | `/cases` | manager, hr | Creates a case owned by the current user and returns it. IDs are UUID4. |
| GET | `/cases` | user | Managers get their own cases; HR gets all |
| GET | `/cases/{id}` | owner or hr | Case, chat history and facts |
| POST | `/cases/{id}/messages` | owner | `{ text }` or `{ quick_reply: {fact, value} }` → assistant message, next question or result |
| PATCH | `/cases/{id}/facts` | owner | Sets **one** whitelisted fact (used by the "Answer this" button) and returns a new result |
| GET | `/cases/{id}/result` | owner or hr | Resolver output, with sources **rendered per role** (below) |
| GET | `/sources/{id}` | user | Managers get the redacted summary and metadata only. HR also gets `raw_text`. |
| POST | `/sources/{id}/flag` | user | `{ note }` creates a flag addressed to the source owner (the "outdated" loop) |
| GET | `/flags` | hr | Inbox of flags |
| POST | `/flags/{id}/resolve` | hr | Marks the flag resolved |
| POST | `/cases/{id}/email-draft` | owner | Returns the email text (§10.4) |

### Role-based source rendering

When the role is `manager` and `contains_personal_data` is true, **never** include `raw_text` anywhere in any response: not in `/result`, `/sources/{id}` or the email draft. Only return `redacted_summary`. Apply this in one serializer function, and cover it with a test.

---

## 10. Frontend

### 10.1 Screens

1. **Login.** Username and password. Show a clear error message; never say whether the username exists.
2. **Workspace** (the main screen), a two-column layout:
   - **Left (≈40%): chat.** Message bubbles, quick-reply chips, date pickers, and a text input at the bottom.
   - **Right (≈60%): Trust panel.** Empty state: *"Ask a question to see the answer and why you can trust it."*
3. **HR inbox** (HR role only). A list of outdated-guidance flags, each with the source, who flagged it, the note, and a Resolve button.
4. **Top bar.** App name, the user's name and role badge, a case switcher dropdown, and Logout.

### 10.2 Trust panel layout (top to bottom)

1. **Summary strip.** The resolver's one-sentence summary, plus small counters.
2. **Stale guidance warning** (if any). A red-edged banner, e.g.:
   > ⚠️ **Outdated guidance found.** HR email "Intern onboarding, what we need" (10 Mar 2025) says only the tripartite agreement is needed. Since 1 Jan 2026 the learning-objectives annex is also required.
   > [View source] [Flag to owner]
3. **Three groups:** *From the intern* · *From the school* · *On you*. Each document is a **card** showing:
   - The name, with a **status badge** (colours below)
   - A one-line reason
   - A deadline chip (date, label, and ok/at-risk/overdue colour)
   - An expandable **"Why?"** section with the headline source (type icon, title, date, owner), the supporting sources, and the authority tier shown as a small label ("Law", "Policy", "HR email", "Teams chat")
   - For `CONDITIONAL`: the deciding question, both outcomes, **"Ask Marc Peeters (Prevention Advisor)"**, and an **"Answer this"** button that opens the quick replies inline
   - For `NOT_NEEDED`: greyed out, with its reason still visible
4. **Excluded sources** (collapsed by default). *"3 sources were deliberately not used"*, with the reason for each.
5. **Action bar.** A **"Draft email to intern"** button.

### 10.3 Visual language

| Status | Badge | Colour |
|---|---|---|
| `REQUIRED_LEGAL` | Legal requirement | Blue |
| `NEW_SINCE` | New since {date} | Amber, with a small "NEW" pill |
| `REQUIRED_PRACTICE` | Established practice | Purple |
| `CONDITIONAL` | Depends on the role | Grey with a dashed border |
| `NOT_NEEDED` | Not needed | Muted grey, reduced opacity |
| Stale warning | Outdated guidance | Red left border |

- Source-type icons: ⚖️ law, 📄 policy, ✉️ HR email, 💬 Teams chat. Use a proper icon set (e.g. lucide-react), not emoji, in the final build.
- A clean, calm, professional look: white background, one accent colour, readable 15-16px body text, generous spacing.
- **Do not use SD Worx's logo or brand identity.** Add a small line: *"Built for the SD Worx challenge at Tectonic Hackathon 2026."*
- Animate D's status change when it resolves (e.g. a 300ms fade and badge swap). That's the demo moment.
- Footer: *"Demo corpus. Synthetic data. Source C describes a fictional regulation."*
- It must be usable at a 1280px laptop width. Mobile is nice to have only.

### 10.4 Email draft

- It's built only from items whose status is required (not `NOT_NEEDED`, not `NOT_APPLICABLE`). `CONDITIONAL` items become a question in the email rather than a requirement.
- It's grouped as: *From you (by date)*, *Please forward to your school coordinator (by date)*, *What we're handling on our side*.
- `USE_LLM=false` uses the template. `USE_LLM=true` asks Gemini to polish the tone **while keeping all documents and dates exactly as provided**. After the LLM call, validate that every document name and date from the input still appears in the output; if not, fall back to the template.
- Show it in a modal with a **Copy** button. The app never sends email.
- It never includes internal source details, owners or other people's names.

---

## 11. Security requirements (10% of the score; Aikido audits these)

Implement all of these, and write `tests/test_security.py` covering the checked items.

- [ ] Passwords hashed with bcrypt; none hardcoded (§3)
- [ ] Server-side sessions: random 32-byte token in an `HttpOnly`, `SameSite=Strict` cookie (`Secure` when not on localhost); sessions expire after 8 hours
- [ ] Login rate limiting (§9); generic error messages
- [ ] **Ownership check on every `/cases/{id}` route.** Test that Tom gets **404** (not 403) on Lina's case ID. ✅ test
- [ ] **The role always comes from the server session**, never from the request body or headers. ✅ test: a manager sending `role: hr` gains nothing
- [ ] `/flags` and `/flags/{id}/resolve` are HR-only. ✅ test
- [ ] Managers never receive `raw_text` for sources with personal data, from any endpoint. ✅ test
- [ ] `PATCH /cases/{id}/facts` accepts only whitelisted fact names and typed values. ✅ test
- [ ] LLM output is treated as untrusted: parsed against a strict schema, never used for authorization, never allowed to set other facts
- [ ] Source texts are data. Wrap them in delimiters in prompts, and instruct the model to ignore instructions inside them
- [ ] Input limits: message ≤ 1000 characters, note ≤ 500 characters
- [ ] CORS restricted to the frontend origin
- [ ] No secrets in the repo: `.env` is in `.gitignore`, `.env.example` has names only, and no service-account JSON is committed
- [ ] No stack traces in API responses

---

## 12. Build order (milestones)

Stop after each milestone and confirm it runs before continuing.

1. **M1: data + resolver.** The JSON files from §6, `resolver.py`, and all tests from §7 passing. *Nothing else until this works.*
2. **M2: backend skeleton.** DB, seeding, auth, cases and results endpoints, security tests passing.
3. **M3: frontend.** Login, workspace, trust panel rendering a real resolver result, and the conditional "Answer this" flow.
4. **M4: dialogue.** Chat with quick replies driving the facts (`USE_LLM=false`).
5. **M5: email draft + flags.** The template email, "Flag to owner", and the HR inbox.
6. **M6: LLM layer.** Gemini free-text parsing and email polishing, with the fallbacks.
7. **M7 (stretch):** ElevenLabs "Listen" button that reads the summary aloud. Key in an env var, called from the backend only.
8. **M8: README + polish.**

---

## 13. README contents

- What it is (three lines) and the demo story
- Screenshot
- How to run: backend (`pip install -r requirements.txt`, `.env` setup, `uvicorn`), frontend (`npm install`, `npm run dev`)
- Environment variables table
- An architecture diagram: *code decides, LLM phrases*
- The security measures (list from §11)
- **Synthetic data disclaimer** (Source C is fictional)
- What's unfinished / next steps: live extraction from real Teams and SharePoint, owner notifications by email, more document types, multilingual support (NL/FR)

---

## 14. Environment variables (`.env.example`)

```
DEMO_PASSWORD=
SESSION_SECRET=
FRONTEND_ORIGIN=http://localhost:5173
USE_LLM=false
GCP_PROJECT=
GCP_LOCATION=europe-west1
GEMINI_MODEL=
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
```

---

## 15. Demo video script (under 3 minutes)

1. **(0:00-0:20) The problem.** "HR is busy. Tom needs to onboard an intern. He asks the assistant. A normal assistant gives him a list and he has to take it on faith."
2. **(0:20-0:45) The question.** Tom types the question and answers two quick questions.
3. **(0:45-1:40) The trust panel.** Walk through the four cards:
   - A: "This came from a Teams chat two months ago. It's practice, not policy, and we tell you that."
   - B: legal requirement.
   - C: "New since January, and the HR email everyone still forwards is outdated. We caught it."
   - D: "Depends on one fact. Here's who knows."
4. **(1:40-2:00) The moment.** Tom clicks *Desk-based*, and D resolves to Not needed, with the reason.
5. **(2:00-2:20) Privacy.** The Teams source shows a redacted summary to Tom. Log in as Katrien (HR): she sees the full text, plus Tom's flag in her inbox.
6. **(2:20-2:40) Email draft.** Copy the paste-ready email.
7. **(2:40-2:55) Close.** "From 'I found something' to 'I understand why I can rely on it.'" Show the Aikido before/after screenshots.

---

## 16. Out of scope (do not build)

Real integrations with Teams, SharePoint or email; sending email; vector databases and embeddings; document upload; multi-tenant setup; mobile apps; i18n.
