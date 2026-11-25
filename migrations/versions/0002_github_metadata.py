"""Persist installation, PR, base commit, and safe delivery metadata."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade():
    op.create_table(
        "github_installations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("github_installation_id", sa.BigInteger, nullable=False, unique=True),
        sa.Column("account_login", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    with op.batch_alter_table("repositories") as batch:
        batch.add_column(sa.Column("github_repository_id", sa.BigInteger))
        batch.create_unique_constraint("uq_repository_github_id", ["github_repository_id"])
        batch.add_column(sa.Column("installation_record_id", sa.Integer))
        batch.create_foreign_key(
            "fk_repository_installation_record",
            "github_installations",
            ["installation_record_id"],
            ["id"],
        )
        batch.add_column(
            sa.Column("default_branch", sa.String(256), nullable=False, server_default="main")
        )
        batch.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            )
        )
        batch.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            )
        )
    op.create_table(
        "pull_requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("repository_id", sa.Integer, sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("number", sa.Integer, nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("html_url", sa.String(1024), nullable=False),
        sa.Column("head_sha", sa.String(40), nullable=False),
        sa.Column("base_sha", sa.String(40), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("repository_id", "number"),
    )
    op.create_index("ix_pull_requests_repository_id", "pull_requests", ["repository_id"])
    with op.batch_alter_table("review_runs") as batch:
        batch.add_column(sa.Column("base_sha", sa.String(40), nullable=False, server_default=""))
        batch.add_column(sa.Column("generation", sa.Integer, nullable=False, server_default="0"))
        batch.add_column(sa.Column("pull_request_id", sa.Integer))
        batch.create_foreign_key(
            "fk_run_pull_request", "pull_requests", ["pull_request_id"], ["id"]
        )
        batch.create_index("ix_review_runs_pull_request_id", ["pull_request_id"])
    with op.batch_alter_table("deliveries") as batch:
        batch.add_column(sa.Column("event_metadata", sa.JSON, nullable=False, server_default="{}"))


def downgrade():
    with op.batch_alter_table("deliveries") as batch:
        batch.drop_column("event_metadata")
    with op.batch_alter_table("review_runs") as batch:
        batch.drop_index("ix_review_runs_pull_request_id")
        batch.drop_constraint("fk_run_pull_request", type_="foreignkey")
        batch.drop_column("pull_request_id")
        batch.drop_column("generation")
        batch.drop_column("base_sha")
    op.drop_table("pull_requests")
    with op.batch_alter_table("repositories") as batch:
        batch.drop_constraint("fk_repository_installation_record", type_="foreignkey")
        batch.drop_constraint("uq_repository_github_id", type_="unique")
        for column in [
            "installation_record_id",
            "github_repository_id",
            "default_branch",
            "created_at",
            "updated_at",
        ]:
            batch.drop_column(column)
    op.drop_table("github_installations")
