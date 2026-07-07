import { API_BASE } from "./client";
import type { Citation } from "./types";

export interface StreamHandlers {
  onStart?: (p: any) => void;
  onDelta?: (text: string) => void;
  onCitations?: (cs: Citation[]) => void;
  onUsage?: (p: any) => void;
  onDone?: (p: any) => void;
  onError?: (p: any) => void;
}

/** POST /chat as SSE and dispatch start/delta/citations/usage/done/error. */
export async function streamChat(
  question: string,
  k: number,
  token: string,
  h: StreamHandlers,
): Promise<void> {
  let resp: Response;
  try {
    resp = await fetch(`${API_BASE}/api/v1/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ question, k }),
    });
  } catch {
    h.onError?.({ title: "Network error — is the API running?" });
    return;
  }

  if (!resp.ok || !resp.body) {
    let title = `HTTP ${resp.status}`;
    try {
      const p = await resp.json();
      title = p.detail || p.title || title;
    } catch {
      /* ignore */
    }
    h.onError?.({ title });
    return;
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) >= 0) {
      const frame = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      dispatch(frame, h);
    }
  }
}

function dispatch(frame: string, h: StreamHandlers): void {
  let event = "message";
  let data = "";
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data += line.slice(5).trim();
    // lines starting with ":" are heartbeat comments — ignored
  }
  if (!data) return;

  let payload: any;
  try {
    payload = JSON.parse(data);
  } catch {
    return;
  }

  switch (event) {
    case "start":
      h.onStart?.(payload);
      break;
    case "delta":
      h.onDelta?.(payload.text);
      break;
    case "citations":
      h.onCitations?.(payload.citations);
      break;
    case "usage":
      h.onUsage?.(payload);
      break;
    case "done":
      h.onDone?.(payload);
      break;
    case "error":
      h.onError?.(payload);
      break;
  }
}
