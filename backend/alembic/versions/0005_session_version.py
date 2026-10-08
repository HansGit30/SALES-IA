"""Allow revoking all previously issued sessions for a user."""
from alembic import op

revision = "0005_session_version"
down_revision = "0004_report_snapshots"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE users ADD COLUMN session_version INTEGER NOT NULL DEFAULT 0 CHECK (session_version >= 0)")


def downgrade():
    op.drop_column("users", "session_version")
