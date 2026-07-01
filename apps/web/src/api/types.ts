export interface Citation {
  marker: string;
  chunk_id: string | null;
  source_title: string | null;
  page_start: number | null;
  section: string | null;
  score: number;
  text: string;
}

export interface Me {
  user_id: string;
  email: string;
  is_admin: boolean;
}

export interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  citations?: Citation[];
  streaming?: boolean;
  insufficient?: boolean;
  error?: string;
}

export interface DocumentOut {
  document_id: string;
  version_id: string;
  version_no: number;
  title: string;
  status: string;
}

export interface DocumentSummary {
  id: string;
  title: string;
  is_active: boolean;
  allowed_for_rag: boolean;
  status: string | null;
}

export interface IngestStatus {
  version_id: string;
  status: string;
  chunks: number;
}
