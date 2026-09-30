import { useEffect, useRef, useState, type FormEvent } from "react";
import { Send } from "lucide-react";
import { api } from "./api";
import type { Case, Me, Message, Option, Result, Turn } from "./types";
import TrustPanel from "./TrustPanel";

interface Props { me: Me; caseId: string | null; onCreated: (id: string) => void }

export default function Workspace({ me, caseId, onCreated }: Props) {
  const [kase, setKase] = useState<Case | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!caseId || kase?.id === caseId) return; // just created here: state is already current
    api<Case>(`/cases/${caseId}`).then((c) => {
      setKase(c);
      if (c.has_result) api<Result>(`/cases/${caseId}/result`).then(setResult);
    }).catch((e) => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseId]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [kase?.messages.length]);

  const isOwner = !kase || kase.owner === me.username;

  const apply = (t: Turn) => { setKase(t.case); if (t.result) setResult(t.result); };

  const send = async (body: object) => {
    setBusy(true); setError("");
    try {
      let id = kase?.id;
      if (!id) {
        const c = await api<Case>("/cases", "POST");
        id = c.id; setKase(c); onCreated(id);
      }
      apply(await api<Turn>(`/cases/${id}/messages`, "POST", body));
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const t = text.trim();
    if (!t) return;
    setText("");
    send({ text: t.slice(0, 1000) });
  };

  const answerFact = async (value: boolean | null) => {
    if (!kase) return;
    setError("");
    try { apply(await api<Turn>(`/cases/${kase.id}/facts`, "PATCH", { fact: "manual_tasks", value })); }
    catch (e) { setError((e as Error).message); }
  };

  const messages = kase?.messages ?? [];
  const last = messages[messages.length - 1];

  return (
    <div className="workspace">
      <section className="chat">
        <div className="messages">
          {messages.length === 0 && (
            <div className="chat-empty">
              <h2>Onboarding an intern?</h2>
              <p className="muted">Ask in your own words, for example “What documents do I need from my new intern, and by when?”</p>
            </div>
          )}
          {messages.map((m, i) => <Bubble key={i} m={m} />)}
          {isOwner && last?.ask && !busy && (
            <AskControls ask={last.ask} onPick={(fact, value) => send({ quick_reply: { fact, value } })} />
          )}
          <div ref={endRef} />
        </div>
        {error && <div className="error">{error}</div>}
        {isOwner ? (
          <form className="composer" onSubmit={submit}>
            <input value={text} maxLength={1000} onChange={(e) => setText(e.target.value)}
              placeholder="Ask about your new intern…" disabled={busy} />
            <button className="btn primary icon" disabled={busy || !text.trim()} aria-label="Send"><Send size={16} /></button>
          </form>
        ) : <div className="readonly-note">Viewing {kase?.owner}'s case (read-only).</div>}
      </section>
      <section className="panel">
        <TrustPanel result={result} me={me} caseId={kase?.id ?? null} canAct={isOwner} onAnswer={answerFact} />
      </section>
    </div>
  );
}

function Bubble({ m }: { m: Message }) {
  return <div className={`bubble ${m.role}`}>{m.text}</div>;
}

function AskControls({ ask, onPick }: { ask: NonNullable<Message["ask"]>; onPick: (f: string, v: unknown) => void }) {
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  if (ask.kind === "dates") {
    const valid = start && end && end >= start;
    return (
      <div className="ask dates">
        <label>Start<input type="date" value={start} onChange={(e) => setStart(e.target.value)} /></label>
        <label>End<input type="date" value={end} min={start} onChange={(e) => setEnd(e.target.value)} /></label>
        <button className="btn primary sm" disabled={!valid}
          onClick={() => onPick("dates", { start_date: start, end_date: end })}>Confirm</button>
      </div>
    );
  }
  return (
    <div className="ask chips">
      {(ask.options ?? []).map((o: Option) => (
        <button key={String(o.value)} className="chip" onClick={() => onPick(ask.fact, o.value)}>{o.label}</button>
      ))}
    </div>
  );
}
