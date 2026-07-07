import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import {
  getIngestStatus,
  listDocuments,
  triggerIngest,
  uploadDocument,
} from "../api/client";
import type { DocumentSummary } from "../api/types";
import { useToast } from "../ui/Toast";

const TERMINAL = ["published", "quarantined", "retired"];

export function DocumentsAdmin() {
  const { token } = useAuth();
  const toast = useToast();
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [maxPages, setMaxPages] = useState("12");
  const [busy, setBusy] = useState(false);
  const [log, setLog] = useState("");

  async function refresh() {
    if (!token) return;
    try {
      setDocs(await listDocuments(token));
    } catch (e: any) {
      setLog(`Error: ${e.message}`);
      toast(e.message, "error");
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function pollStatus(versionId: string) {
    for (let i = 0; i < 120; i++) {
      const st = await getIngestStatus(token!, versionId);
      setLog(`Status: ${st.status} — ${st.chunks} chunks`);
      if (TERMINAL.includes(st.status)) return;
      await new Promise((r) => setTimeout(r, 1500));
    }
    setLog("Timed out waiting for the worker (is scripts/run_worker.py running?).");
  }

  async function uploadAndIngest() {
    if (!token || !file || busy) return;
    setBusy(true);
    try {
      setLog(`Uploading ${file.name}…`);
      const doc = await uploadDocument(token, file);
      const mp = maxPages.trim() ? parseInt(maxPages, 10) : undefined;
      setLog("Uploaded. Queuing ingestion…");
      await triggerIngest(token, doc.version_id, mp);
      setLog("Queued. Waiting for the worker…");
      await pollStatus(doc.version_id);
    } catch (e: any) {
      setLog(`Error: ${e.message}`);
      toast(e.message, "error");
    } finally {
      setBusy(false);
      setFile(null);
      refresh();
    }
  }

  return (
    <div className="docs">
      <h2>Documents</h2>

      <div className="card upload">
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <label>
          Max pages
          <input
            className="num"
            value={maxPages}
            onChange={(e) => setMaxPages(e.target.value)}
            placeholder="all"
          />
        </label>
        <button onClick={uploadAndIngest} disabled={!file || busy}>
          {busy ? "Working…" : "Upload & ingest"}
        </button>
      </div>

      {log && <div className="log">{log}</div>}

      <div className="doc-list">
        <div className="doc-list-head">
          <span>Title</span>
          <span>Status</span>
        </div>
        {docs.map((d) => (
          <div className="doc-row" key={d.id}>
            <span>{d.title}</span>
            <span className={`status ${d.status ?? ""}`}>{d.status ?? "—"}</span>
          </div>
        ))}
        {docs.length === 0 && <div className="doc-row muted">No documents yet.</div>}
      </div>

      <button className="link" onClick={refresh} disabled={busy}>
        Refresh
      </button>
    </div>
  );
}
