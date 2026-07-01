"""Document admin + ingestion endpoints (is_admin only).

Upload → MinIO + register; ingest → enqueue Redis job (202); status → poll.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Response, UploadFile

from ... import documents, objectstore, queue
from ..errors import ProblemException
from ..schemas import DocumentOut, DocumentSummary, IngestAccepted, IngestStatusOut
from ..security import Principal, require_admin

router = APIRouter(tags=["documents"])

_NOT_FOUND = "https://api.akasha/errors/not-found"


@router.post("/documents", status_code=201, response_model=DocumentOut)
def upload_document(
    file: UploadFile = File(...),
    principal: Principal = Depends(require_admin),
) -> DocumentOut:
    data = file.file.read()
    if not data:
        raise ProblemException(400, "Empty file", "No file content.", "https://api.akasha/errors/bad-request")
    checksum = hashlib.sha256(data).hexdigest()
    key = f"pdfs/{checksum}.pdf"
    objectstore.ensure_bucket()
    objectstore.put_bytes(key, data)
    title = Path(file.filename or "upload.pdf").stem
    doc_id, ver_id, ver_no = documents.register_document(title, checksum, key, principal.user_id)
    return DocumentOut(
        document_id=str(doc_id), version_id=str(ver_id), version_no=ver_no, title=title, status="pending"
    )


@router.post("/documents/{version_id}/ingest", status_code=202, response_model=IngestAccepted)
def trigger_ingest(
    version_id: UUID,
    response: Response,
    max_pages: int | None = None,
    principal: Principal = Depends(require_admin),
) -> IngestAccepted:
    if documents.get_version(version_id) is None:
        raise ProblemException(404, "Not found", "Unknown document version.", _NOT_FOUND)
    documents.set_version_status(version_id, "queued")
    queue.enqueue({"version_id": str(version_id), "max_pages": max_pages})
    response.headers["Location"] = f"/api/v1/documents/{version_id}/ingest/status"
    return IngestAccepted(version_id=str(version_id), status="queued")


@router.get("/documents/{version_id}/ingest/status", response_model=IngestStatusOut)
def get_ingest_status(
    version_id: UUID,
    principal: Principal = Depends(require_admin),
) -> IngestStatusOut:
    st = documents.ingest_status(version_id)
    if st is None:
        raise ProblemException(404, "Not found", "Unknown document version.", _NOT_FOUND)
    return IngestStatusOut(version_id=str(version_id), status=st["status"], chunks=st["chunks"])


@router.get("/documents", response_model=list[DocumentSummary])
def list_documents(principal: Principal = Depends(require_admin)) -> list[DocumentSummary]:
    return [DocumentSummary(**d) for d in documents.list_documents()]
