import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { useAuth } from "../auth/AuthContext";
import { streamChat } from "../api/stream";
import type { ChatMessage, Citation } from "../api/types";
import { useToast } from "../ui/Toast";
import { SourceModal } from "./SourceModal";

const STORAGE_KEY = "akasha_chat";

function loadMessages(): ChatMessage[] {
  try {
    const s = localStorage.getItem(STORAGE_KEY);
    if (s) return (JSON.parse(s) as ChatMessage[]).map((m) => ({ ...m, streaming: false }));
  } catch {
    /* ignore */
  }
  return [];
}

export function Chat() {
  const { token } = useAuth();
  const toast = useToast();
  const [messages, setMessages] = useState<ChatMessage[]>(loadMessages);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<Citation | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Persist history so a refresh keeps the conversation.
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
  }, [messages]);

  const scroll = () =>
    requestAnimationFrame(() =>
      listRef.current?.scrollTo(0, listRef.current.scrollHeight),
    );

  const updateLast = (fn: (m: ChatMessage) => ChatMessage) =>
    setMessages((ms) => {
      const copy = [...ms];
      copy[copy.length - 1] = fn(copy[copy.length - 1]);
      return copy;
    });

  function newChat() {
    setMessages([]);
    localStorage.removeItem(STORAGE_KEY);
  }

  async function send() {
    const q = input.trim();
    if (!q || busy || !token) return;
    setInput("");
    setBusy(true);
    setMessages((ms) => [
      ...ms,
      { role: "user", text: q },
      { role: "assistant", text: "", streaming: true },
    ]);
    scroll();

    await streamChat(q, 4, token, {
      onDelta: (t) => {
        updateLast((a) => ({ ...a, text: a.text + t }));
        scroll();
      },
      onCitations: (cs) => updateLast((a) => ({ ...a, citations: cs })),
      onDone: (p) => {
        updateLast((a) => ({ ...a, streaming: false, insufficient: !!p?.insufficient_evidence }));
        setBusy(false);
      },
      onError: (e) => {
        updateLast((a) => ({ ...a, streaming: false, error: e?.title || "Error" }));
        toast(e?.title || "Something went wrong", "error");
        setBusy(false);
      },
    });
  }

  return (
    <div className="chat">
      {messages.length > 0 && (
        <div className="chat-toolbar">
          <button className="link" onClick={newChat}>
            New chat
          </button>
        </div>
      )}

      <div className="messages" ref={listRef}>
        {messages.length === 0 && (
          <div className="empty">
            Ask about remote sensing or GIS — e.g. <em>“What is NDVI?”</em>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <div className="bubble">
              {m.role === "assistant" ? (
                <ReactMarkdown>{m.text || (m.streaming ? "▍" : "")}</ReactMarkdown>
              ) : (
                m.text
              )}
              {m.error && <div className="error">{m.error}</div>}
              {m.insufficient && (
                <div className="badge-refusal">⚠ No supporting sources in the corpus</div>
              )}
              {!m.insufficient && m.citations && m.citations.length > 0 && (
                <div className="sources">
                  <div className="sources-label">Sources</div>
                  <div className="cites">
                    {m.citations.map((c) => (
                      <button
                        className="cite"
                        key={c.marker}
                        onClick={() => setSelected(c)}
                        title="View source excerpt"
                      >
                        [{c.marker}] {c.source_title ?? "source"}
                        {c.page_start ? ` · p.${c.page_start}` : ""}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="composer">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") send();
          }}
          placeholder="Ask a question…"
          disabled={busy}
        />
        <button onClick={send} disabled={busy || !input.trim()}>
          {busy ? "…" : "Send"}
        </button>
      </div>

      {selected && <SourceModal citation={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
