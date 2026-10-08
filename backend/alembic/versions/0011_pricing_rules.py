"""Persist company pricing defaults and override policy."""
from alembic import op
revision="0011_pricing_rules"
down_revision="0010_branch_operations"
branch_labels=None
depends_on=None

def upgrade():
    op.execute("ALTER TABLE companies ADD COLUMN default_tax_percent NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK(default_tax_percent BETWEEN 0 AND 100)")
    op.execute("ALTER TABLE companies ADD COLUMN default_discount_percent NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK(default_discount_percent BETWEEN 0 AND 100)")
    op.execute("ALTER TABLE companies ADD COLUMN allow_pricing_override BOOLEAN NOT NULL DEFAULT TRUE")

    op.execute("ALTER TABLE order_details ADD COLUMN discount_percent NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK(discount_percent BETWEEN 0 AND 100)")
    op.execute("ALTER TABLE order_details ADD COLUMN tax_percent NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK(tax_percent BETWEEN 0 AND 100)")

def downgrade():
    op.execute("ALTER TABLE order_details DROP COLUMN discount_percent,DROP COLUMN tax_percent")
    op.execute("ALTER TABLE companies DROP COLUMN allow_pricing_override,DROP COLUMN default_discount_percent,DROP COLUMN default_tax_percent")
