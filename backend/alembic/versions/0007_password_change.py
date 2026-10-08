"""Require a personal password after administrative recovery."""
from alembic import op

revision = "0007_password_change"
down_revision = "0006_auth_rate_limits"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT FALSE")


def downgrade():
    op.drop_column("users", "must_change_password")
