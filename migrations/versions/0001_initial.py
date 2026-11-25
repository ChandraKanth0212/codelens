"""Initial persisted review queue and reports."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None


def upgrade():
    op.create_table(
        "repositories",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("full_name", sa.String(256), nullable=False, unique=True),
        sa.Column("installation_id", sa.Integer, nullable=False),
        sa.Column("config", sa.JSON, nullable=False),
    )
    op.create_table(
        "review_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("repository_id", sa.Integer, sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("number", sa.Integer, nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("head_sha", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("is_demo", sa.Boolean, nullable=False),
        sa.Column("attempts", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("report", sa.JSON, nullable=False),
        sa.UniqueConstraint("repository_id", "number", "head_sha"),
    )
    op.create_index("ix_review_runs_repository_id", "review_runs", ["repository_id"])
    op.create_index("ix_review_runs_status", "review_runs", ["status"])
    op.create_table(
        "deliveries",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("run_id", sa.Integer, sa.ForeignKey("review_runs.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "findings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("run_id", sa.Integer, sa.ForeignKey("review_runs.id"), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("data", sa.JSON, nullable=False),
        sa.Column("feedback", sa.String(20), nullable=False),
        sa.UniqueConstraint("run_id", "fingerprint"),
    )
    op.create_index("ix_findings_run_id", "findings", ["run_id"])


def downgrade():
    for table in ["findings", "deliveries", "review_runs", "repositories"]:
        op.drop_table(table)
