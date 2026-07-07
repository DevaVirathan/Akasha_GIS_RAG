import { useState } from "react";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { Login } from "./auth/Login";
import { Chat } from "./chat/Chat";
import { DocumentsAdmin } from "./documents/DocumentsAdmin";
import { ToastProvider } from "./ui/Toast";

type View = "chat" | "documents";

function AppShell() {
  const { email, isAdmin, logout } = useAuth();
  const [view, setView] = useState<View>("chat");

  return (
    <div className="app">
      <header className="topbar">
        <strong>Akasha</strong>
        <nav className="nav">
          <button
            className={view === "chat" ? "tab active" : "tab"}
            onClick={() => setView("chat")}
          >
            Chat
          </button>
          {isAdmin && (
            <button
              className={view === "documents" ? "tab active" : "tab"}
              onClick={() => setView("documents")}
            >
              Documents
            </button>
          )}
        </nav>
        <span className="spacer" />
        <span className="muted">{email}</span>
        {isAdmin && <span className="badge-admin">admin</span>}
        <button className="link" onClick={logout}>
          Sign out
        </button>
      </header>
      <div className="content">
        {view === "chat" ? <Chat /> : <DocumentsAdmin />}
      </div>
    </div>
  );
}

function Shell() {
  const { token } = useAuth();
  return token ? <AppShell /> : <Login />;
}

export function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <Shell />
      </AuthProvider>
    </ToastProvider>
  );
}
