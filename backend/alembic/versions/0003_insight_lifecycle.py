"""Track insight evaluation and enforce one result per company, rule and period."""
from alembic import op

revision = "0003_insight_lifecycle"
down_revision = "0002_orders"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE insights ADD COLUMN dedupe_key VARCHAR(160)")
    op.execute("ALTER TABLE insights ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','resolved'))")
    op.execute("ALTER TABLE insights ADD COLUMN evaluated_at TIMESTAMPTZ NOT NULL DEFAULT now()")
    op.execute("UPDATE insights SET evaluated_at=created_at")
    op.execute("ALTER TABLE insights ADD COLUMN resolved_at TIMESTAMPTZ")
    op.execute("CREATE UNIQUE INDEX ux_insights_company_dedupe ON insights(company_id,dedupe_key)")


def downgrade():
    op.drop_index("ux_insights_company_dedupe", table_name="insights")
    for column in ("resolved_at", "evaluated_at", "status", "dedupe_key"):
        op.drop_column("insights", column)
