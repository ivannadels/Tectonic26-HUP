import { useEffect, useState } from "react";
import {
  AlertTriangle, CalendarClock, Check, ChevronDown, Copy, EyeOff, FileText, Flag,
  HelpCircle, Mail, MessageSquare, Scale, User, X,
} from "lucide-react";
import { api, fmtDate } from "./api";
import type { Excluded, Item, Me, Result, SourceRef, SourceType } from "./types";

const TYPE_ICON: Record<SourceType, typeof Scale> = { law: Scale, policy: FileText, hr_email: Mail, chat: MessageSquare };
const GROUPS: { key: Item["provided_by"]; title: string }[] = [
  { key: "intern", title: "From the intern" },
  { key: "school", title: "From the school" },
  { key: "manager", title: "On you" },
];
const BADGE: Record<Item["status"], string> = {
  REQUIRED_LEGAL: "Legal requirement", NEW_SINCE: "", REQUIRED_PRACTICE: "Established practice",
  CONDITIONAL: "Depends on the role", NOT_NEEDED: "Not needed",
};

interface Props {
  result: Result | null; me: Me; caseId: string | null; canAct: boolean;
  onAnswer: (v: boolean | null) => void;
}

type Modal = { kind: "source"; id: string } | { kind: "flag"; id: string; title: string } | { kind: "email" } | null;

export default function TrustPanel({ result, me, caseId, canAct, onAnswer }: Props) {
  const [modal, setModal] = useState<Modal>(null);
  const [showExcluded, setShowExcluded] = useState(false);

  if (!result) {
    return <div className="panel-empty"><Scale size={28} /><p>Ask a question to see the answer and why you can trust it.</p></div>;
  }

  return (
    <div className="trust">
      <div className="summary card">
        <p>{result.summary}</p>
        <div className="counters">
          <Counter n={result.counts.legal} label="legal" cls="legal" />
          <Counter n={result.counts.practice} label="practice" cls="practice" />
          <Counter n={result.counts.conditional} label="depends" cls="conditional" />
          <Counter n={result.counts.stale} label="outdated" cls="stale" />
          <Counter n={result.counts.excluded} label="excluded" cls="muted" />
        </div>
      </div>

      {result.stale_warnings.map((w) => (
        <div key={w.source_id} className="stale card">
          <AlertTriangle size={18} className="stale-icon" />
          <div>
            <strong>Outdated guidance found.</strong> {w.title} ({fmtDate(w.date)}, owner: {w.owner}).
            <p>{w.explanation}</p>
            <div className="row">
              <button className="btn ghost sm" onClick={() => setModal({ kind: "source", id: w.source_id })}>View source</button>
              <button className="btn ghost sm" onClick={() => setModal({ kind: "flag", id: w.source_id, title: w.title })}><Flag size={14} /> Flag to owner</button>
            </div>
          </div>
        </div>
      ))}

      {GROUPS.map((g) => {
        const items = result.items.filter((i) => i.provided_by === g.key);
        if (!items.length) return null;
        return (
          <div key={g.key} className="group">
            <h3>{g.title}</h3>
            {items.map((it) => (
              <DocCard key={it.document + it.status} it={it} canAct={canAct} onAnswer={onAnswer}
                onView={(id) => setModal({ kind: "source", id })} />
            ))}
          </div>
        );
      })}

      {result.excluded.length > 0 && (
        <div className="excluded card">
          <button className="collapse" onClick={() => setShowExcluded(!showExcluded)}>
            <EyeOff size={16} /> {result.excluded.length} sources were deliberately not used
            <ChevronDown size={16} className={showExcluded ? "rot" : ""} />
          </button>
          {showExcluded && <ul>{result.excluded.map((e) => <ExcludedRow key={e.source_id} e={e} />)}</ul>}
        </div>
      )}

      {canAct && caseId && (
        <div className="actionbar">
          <button className="btn primary" onClick={() => setModal({ kind: "email" })}><Mail size={16} /> Draft email to intern</button>
        </div>
      )}

      {modal?.kind === "source" && <SourceModal id={modal.id} me={me} onClose={() => setModal(null)} />}
      {modal?.kind === "flag" && <FlagModal id={modal.id} title={modal.title} onClose={() => setModal(null)} />}
      {modal?.kind === "email" && caseId && <EmailModal caseId={caseId} onClose={() => setModal(null)} />}
    </div>
  );
}

function Counter({ n, label, cls }: { n: number; label: string; cls: string }) {
  return <span className={`counter c-${cls}`}><b>{n}</b> {label}</span>;
}

function DocCard({ it, canAct, onAnswer, onView }: {
  it: Item; canAct: boolean; onAnswer: (v: boolean | null) => void; onView: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [answering, setAnswering] = useState(false);
  const cls = it.status.toLowerCase();
  return (
    <div className={`doc card status-${cls}`}>
      <div className="doc-head">
        <div className="doc-name">{it.name}</div>
        <span className={`badge ${cls}`}>
          {it.status === "NEW_SINCE" ? <><span className="new-pill">NEW</span>{it.status_label}</> : BADGE[it.status]}
        </span>
      </div>
      <p className="doc-reason">{it.reason}</p>
      {it.status === "REQUIRED_PRACTICE" && (
        <p className="tiny muted">Established practice, not written policy · stated by {it.headline_source.owner}</p>
      )}
      {it.deadline && (
        <div><span className={`deadline ${it.deadline.flag}`}>
          <CalendarClock size={14} /> {fmtDate(it.deadline.date)} · {it.deadline.label}
          {it.deadline.flag === "overdue" ? " · overdue" : it.deadline.flag === "at_risk" ? " · at risk" : ""}
        </span></div>
      )}

      {it.condition && (
        <div className="condition">
          <div className="cq"><HelpCircle size={16} /> {it.condition.question}</div>
          <div className="outcomes">
            <span><b>If yes:</b> {it.condition.if_yes}</span>
            <span><b>If no:</b> {it.condition.if_no}</span>
          </div>
          <div className="ask-person"><User size={14} /> Ask {it.condition.ask_person.name} ({it.condition.ask_person.role})</div>
          {canAct && (answering ? (
            <div className="chips">
              <button className="chip" onClick={() => onAnswer(false)}>Desk-based</button>
              <button className="chip" onClick={() => onAnswer(true)}>Some manual tasks</button>
              <button className="chip" onClick={() => { onAnswer(null); setAnswering(false); }}>Not sure</button>
            </div>
          ) : <button className="btn primary sm" onClick={() => setAnswering(true)}>Answer this</button>)}
        </div>
      )}

      <button className="why" onClick={() => setOpen(!open)}>Why? <ChevronDown size={14} className={open ? "rot" : ""} /></button>
      {open && (
        <div className="why-body">
          <SourceLine s={it.headline_source} headline onView={onView} />
          {it.supporting_sources.map((s) => <SourceLine key={s.id} s={s} onView={onView} />)}
        </div>
      )}
    </div>
  );
}

function SourceLine({ s, headline, onView }: { s: SourceRef; headline?: boolean; onView: (id: string) => void }) {
  const Icon = TYPE_ICON[s.type];
  return (
    <div className="src">
      <Icon size={16} className="src-icon" />
      <div>
        <div className="src-title">
          {s.title} <span className={`tier tier-${s.type}`}>{s.authority_label}</span>
          {headline && <span className="tiny muted"> · headline source</span>}
        </div>
        <div className="tiny muted">{fmtDate(s.date)} · owner: {s.owner ?? "none"}</div>
        <p className="src-summary">{s.summary}</p>
        <button className="link" onClick={() => onView(s.id)}>View source</button>
      </div>
    </div>
  );
}

function ExcludedRow({ e }: { e: Excluded }) {
  const Icon = TYPE_ICON[e.type];
  return (
    <li>
      <Icon size={14} /> <b>{e.title}</b>: {e.reason}
      {e.mentions_documents.length > 0 && <span className="muted"> (mentions {e.mentions_documents.join(", ")})</span>}
    </li>
  );
}

function ModalShell({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head"><h3>{title}</h3><button className="btn ghost icon" onClick={onClose} aria-label="Close"><X size={16} /></button></div>
        {children}
      </div>
    </div>
  );
}

interface SourceFull {
  id: string; title: string; type: SourceType; date: string; owner: string | null;
  contains_personal_data: boolean; redacted_summary: string; raw_text?: string;
}

function SourceModal({ id, me, onClose }: { id: string; me: Me; onClose: () => void }) {
  const [s, setS] = useState<SourceFull | null>(null);
  useEffect(() => { api<SourceFull>(`/sources/${id}`).then(setS); }, [id]);
  return (
    <ModalShell title={s?.title ?? "Source"} onClose={onClose}>
      {!s ? <p className="muted">Loading…</p> : (
        <>
          <p className="tiny muted">{fmtDate(s.date)} · {s.type.replace("_", " ")}</p>
          <h4>Summary</h4>
          <p>{s.redacted_summary}</p>
          {s.raw_text ? (<><h4>Original text <span className="tiny muted">(visible to HR)</span></h4><pre className="raw">{s.raw_text}</pre></>)
            : me.role === "manager" && s.contains_personal_data && (
              <p className="privacy"><EyeOff size={14} /> This source contains other people's personal data, so you see a redacted summary. HR can see the original.</p>
            )}
        </>
      )}
    </ModalShell>
  );
}

function FlagModal({ id, title, onClose }: { id: string; title: string; onClose: () => void }) {
  const [note, setNote] = useState("This guidance is missing the learning-objectives annex required since 1 Jan 2026.");
  const [done, setDone] = useState(false);
  const [err, setErr] = useState("");
  const submit = async () => {
    try { await api(`/sources/${id}/flag`, "POST", { note: note.slice(0, 500) }); setDone(true); }
    catch (e) { setErr((e as Error).message); }
  };
  return (
    <ModalShell title="Flag as outdated" onClose={onClose}>
      {done ? <p className="ok-msg"><Check size={16} /> Sent to the source owner's inbox.</p> : (
        <>
          <p className="muted">{title}</p>
          <textarea value={note} maxLength={500} rows={4} onChange={(e) => setNote(e.target.value)} />
          <div className="tiny muted">{note.length}/500</div>
          {err && <div className="error">{err}</div>}
          <button className="btn primary" disabled={!note.trim()} onClick={submit}><Flag size={14} /> Send flag</button>
        </>
      )}
    </ModalShell>
  );
}

function EmailModal({ caseId, onClose }: { caseId: string; onClose: () => void }) {
  const [text, setText] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  useEffect(() => { api<{ text: string }>(`/cases/${caseId}/email-draft`, "POST").then((r) => setText(r.text)); }, [caseId]);
  const copy = async () => { if (text) { await navigator.clipboard.writeText(text); setCopied(true); } };
  return (
    <ModalShell title="Email to intern" onClose={onClose}>
      {text === null ? <p className="muted">Drafting…</p> : (
        <>
          <pre className="email">{text}</pre>
          <div className="row">
            <button className="btn primary" onClick={copy}>{copied ? <><Check size={16} /> Copied</> : <><Copy size={16} /> Copy</>}</button>
            <span className="tiny muted">TrustTrail never sends email. Paste it into your mail client.</span>
          </div>
        </>
      )}
    </ModalShell>
  );
}
