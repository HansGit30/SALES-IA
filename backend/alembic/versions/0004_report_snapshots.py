"""Persist the content used to generate each report."""
from alembic import op

revision = "0004_report_snapshots"
down_revision = "0003_insight_lifecycle"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE reports ADD COLUMN snapshot JSONB")


def downgrade():
    op.drop_column("reports", "snapshot")
