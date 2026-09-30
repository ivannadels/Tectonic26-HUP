import { useEffect, useState } from "react";
import { CheckCircle2, Flag as FlagIcon } from "lucide-react";
import { api } from "./api";
import type { Flag } from "./types";

export default function HrInbox() {
  const [flags, setFlags] = useState<Flag[] | null>(null);
  const load = () => api<Flag[]>("/flags").then(setFlags).catch(() => setFlags([]));
  useEffect(() => { load(); }, []);

  const resolve = async (id: string) => { await api(`/flags/${id}/resolve`, "POST"); load(); };

  return (
    <div className="inbox">
      <h2>Flagged sources</h2>
      <p className="muted">Colleagues told us these sources look out of date. Update or retire the source, then mark it resolved.</p>
      {flags === null ? <p className="muted">Loading…</p> : flags.length === 0 ? (
        <div className="empty">No flags. Everything looks current.</div>
      ) : flags.map((f) => (
        <div key={f.id} className={`card flag ${f.resolved ? "resolved" : ""}`}>
          <div className="flag-head">
            <FlagIcon size={16} />
            <strong>{f.source_title}</strong>
            <span className="muted">· owner: {f.source_owner_name ?? "none"}</span>
          </div>
          <p className="flag-note">“{f.note}”</p>
          <div className="flag-foot">
            <span className="muted">Flagged by {f.flagged_by_name} · {new Date(f.created_at).toLocaleString("en-GB")}</span>
            {f.resolved
              ? <span className="resolved-tag"><CheckCircle2 size={14} /> Resolved</span>
              : <button className="btn primary sm" onClick={() => resolve(f.id)}>Mark resolved</button>}
          </div>
        </div>
      ))}
    </div>
  );
}
