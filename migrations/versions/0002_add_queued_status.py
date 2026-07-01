"""add 'queued' to document_versions.status

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-02

The API enqueues an ingest job and marks the version 'queued' before the worker
picks it up; add that state to the CHECK constraint.
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

_NEW = "('pending','queued','ingesting','qa','published','retired','quarantined')"
_OLD = "('pending','ingesting','qa','published','retired','quarantined')"


def upgrade() -> None:
    op.execute("ALTER TABLE document_versions DROP CONSTRAINT document_versions_status_check")
    op.execute(
        "ALTER TABLE document_versions ADD CONSTRAINT document_versions_status_check "
        f"CHECK (status IN {_NEW})"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE document_versions DROP CONSTRAINT document_versions_status_check")
    op.execute(
        "ALTER TABLE document_versions ADD CONSTRAINT document_versions_status_check "
        f"CHECK (status IN {_OLD})"
    )
