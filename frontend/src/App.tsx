import { useCallback, useEffect, useState } from "react";
import { Inbox, LogOut, Plus, ShieldCheck } from "lucide-react";
import { api } from "./api";
import type { CaseSummary, Me } from "./types";
import Login from "./Login";
import Workspace from "./Workspace";
import HrInbox from "./HrInbox";

export default function App() {
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [view, setView] = useState<"workspace" | "inbox">("workspace");
  // Remount the workspace only on an explicit case switch, not when a new case gets its id.
  const [wsKey, setWsKey] = useState(0);
  const openCase = (id: string | null) => { setCaseId(id); setWsKey((k) => k + 1); setView("workspace"); };

  useEffect(() => { api<Me>("/auth/me").then(setMe).catch(() => setMe(null)); }, []);

  const refreshCases = useCallback(async () => {
    const list = await api<CaseSummary[]>("/cases");
    setCases(list);
    return list;
  }, []);

  useEffect(() => {
    if (me) refreshCases().then((l) => setCaseId((cur) => cur ?? l.find((c) => c.owner === me.username)?.id ?? null));
  }, [me, refreshCases]);

  const logout = async () => {
    await api("/auth/logout", "POST").catch(() => undefined);
    setMe(null); setCases([]); setCaseId(null); setView("workspace");
  };

  if (me === undefined) return null;
  if (!me) return <Login onLogin={setMe} />;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand"><ShieldCheck size={20} /> TrustTrail</div>
        <div className="topbar-mid">
          <select value={caseId ?? ""} onChange={(e) => openCase(e.target.value || null)}>
            <option value="">Start a new request</option>
            {cases.map((c) => (
              <option key={c.id} value={c.id}>{c.title}{c.owner !== me.username ? ` (${c.owner})` : ""}</option>
            ))}
          </select>
          <button className="btn ghost" onClick={() => openCase(null)}><Plus size={16} /> New request</button>
          {me.role === "hr" && (
            <button className={`btn ghost ${view === "inbox" ? "active" : ""}`} onClick={() => setView(view === "inbox" ? "workspace" : "inbox")}>
              <Inbox size={16} /> Flagged sources
            </button>
          )}
        </div>
        <div className="user">
          <span>{me.display_name}</span>
          <span className={`role-badge ${me.role}`}>{me.role === "hr" ? "HR" : "Manager"}</span>
          <button className="btn ghost icon" onClick={logout} title="Log out"><LogOut size={16} /></button>
        </div>
      </header>
      <main className="main">
        {view === "inbox" && me.role === "hr"
          ? <HrInbox />
          : <Workspace key={wsKey} me={me} caseId={caseId}
              onCreated={(id) => { setCaseId(id); refreshCases(); }} />}
      </main>
      <footer className="footer">
        Demo corpus. Synthetic data. Source C describes a fictional regulation. · Built for the SD Worx challenge at Tectonic Hackathon 2026.
      </footer>
    </div>
  );
}
