import { useState } from "react";
import { useAuth } from "./AuthContext";

export function Login() {
  const { login, loading, error } = useAuth();
  const [email, setEmail] = useState("devavirathan@thaarei.com");

  return (
    <div className="center">
      <form
        className="card"
        onSubmit={(e) => {
          e.preventDefault();
          login(email);
        }}
      >
        <h1>Akasha</h1>
        <p className="muted">GIS / Remote Sensing assistant</p>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@thaarei.com"
          autoFocus
        />
        <button disabled={loading || !email.trim()}>
          {loading ? "Signing in…" : "Sign in"}
        </button>
        {error && <p className="error">{error}</p>}
        <p className="hint">Dev login — any active @thaarei.com email.</p>
      </form>
    </div>
  );
}
