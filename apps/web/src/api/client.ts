import type { DocumentOut, DocumentSummary, IngestStatus, Me } from "./types";

export const API_BASE =
  (import.meta as any).env?.VITE_API_BASE ?? "http://127.0.0.1:8000";

async function problemMessage(r: Response): Promise<string> {
  try {
    const p = await r.json();
    return p.detail || p.title || `HTTP ${r.status}`;
  } catch {
    return `HTTP ${r.status}`;
  }
}

function authHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` };
}

// ---- Auth ----
export async function devLogin(
  email: string,
): Promise<{ access_token: string; email: string; is_admin: boolean }> {
  const r = await fetch(`${API_BASE}/api/v1/auth/dev-login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (!r.ok) throw new Error(await problemMessage(r));
  return r.json();
}

export async function getMe(token: string): Promise<Me> {
  const r = await fetch(`${API_BASE}/api/v1/me`, { headers: authHeaders(token) });
  if (!r.ok) throw new Error(await problemMessage(r));
  return r.json();
}

// ---- Documents (admin) ----
export async function listDocuments(token: string): Promise<DocumentSummary[]> {
  const r = await fetch(`${API_BASE}/api/v1/documents`, { headers: authHeaders(token) });
  if (!r.ok) throw new Error(await problemMessage(r));
  return r.json();
}

export async function uploadDocument(token: string, file: File): Promise<DocumentOut> {
  const form = new FormData();
  form.append("file", file);
  // NB: don't set Content-Type — the browser adds the multipart boundary.
  const r = await fetch(`${API_BASE}/api/v1/documents`, {
    method: "POST",
    headers: authHeaders(token),
    body: form,
  });
  if (!r.ok) throw new Error(await problemMessage(r));
  return r.json();
}

export async function triggerIngest(
  token: string,
  versionId: string,
  maxPages?: number,
): Promise<{ version_id: string; status: string }> {
  const q = maxPages ? `?max_pages=${maxPages}` : "";
  const r = await fetch(`${API_BASE}/api/v1/documents/${versionId}/ingest${q}`, {
    method: "POST",
    headers: authHeaders(token),
  });
  if (!r.ok) throw new Error(await problemMessage(r));
  return r.json();
}

export async function getIngestStatus(
  token: string,
  versionId: string,
): Promise<IngestStatus> {
  const r = await fetch(`${API_BASE}/api/v1/documents/${versionId}/ingest/status`, {
    headers: authHeaders(token),
  });
  if (!r.ok) throw new Error(await problemMessage(r));
  return r.json();
}
