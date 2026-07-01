import { useEffect } from "react";
import type { Citation } from "../api/types";

export function SourceModal({
  citation,
  onClose,
}: {
  citation: Citation;
  onClose: () => void;
}) {
  // Close on Escape.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const meta = [
    citation.page_start ? `page ${citation.page_start}` : null,
    citation.section || null,
    `similarity ${citation.score}`,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <div className="modal-title">
              [{citation.marker}] {citation.source_title ?? "Source"}
            </div>
            <div className="muted">{meta}</div>
          </div>
          <button className="link" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="modal-body">{citation.text}</div>
      </div>
    </div>
  );
}
