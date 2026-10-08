"""Shared authentication attempt windows across API workers."""
from alembic import op

revision = "0006_auth_rate_limits"
down_revision = "0005_session_version"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE auth_rate_limits (
        bucket_key VARCHAR(64) PRIMARY KEY,
        attempts INTEGER NOT NULL CHECK (attempts > 0),
        expires_at TIMESTAMPTZ NOT NULL
    )""")
    op.execute("CREATE INDEX ix_auth_rate_limits_expiry ON auth_rate_limits(expires_at)")


def downgrade():
    op.drop_table("auth_rate_limits")
