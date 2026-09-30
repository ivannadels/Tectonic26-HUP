import { useState, type FormEvent } from "react";
import { ShieldCheck } from "lucide-react";
import { api } from "./api";
import type { Me } from "./types";

export default function Login({ onLogin }: { onLogin: (m: Me) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true); setError("");
    try { onLogin(await api<Me>("/auth/login", "POST", { username, password })); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  };

  return (
    <div className="login-wrap">
      <form className="login card" onSubmit={submit}>
        <div className="brand big"><ShieldCheck size={26} /> TrustTrail</div>
        <p className="muted">Find it. Understand it. Trust it.</p>
        <label>Username<input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required /></label>
        <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required /></label>
        {error && <div className="error">{error}</div>}
        <button className="btn primary" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
        <p className="tiny muted">Demo corpus. Synthetic data. Built for the SD Worx challenge at Tectonic Hackathon 2026.</p>
      </form>
    </div>
  );
}
