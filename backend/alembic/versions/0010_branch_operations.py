"""Separate branch stock while preserving historical unassigned inventory."""
from alembic import op
revision="0010_branch_operations"
down_revision="0009_branches"
branch_labels=None
depends_on=None

def upgrade():
    for table in ("sales","orders","inventory_movements","employees"):
        op.execute(f"ALTER TABLE {table} ADD COLUMN branch_id BIGINT")
        op.execute(f"ALTER TABLE {table} ADD CONSTRAINT fk_{table}_branch FOREIGN KEY(company_id,branch_id) REFERENCES branches(company_id,id)")
        op.execute(f"CREATE INDEX ix_{table}_branch ON {table}(company_id,branch_id)")
    op.execute("""CREATE TABLE branch_inventory (
        company_id BIGINT NOT NULL, branch_id BIGINT NOT NULL, product_id BIGINT NOT NULL,
        quantity NUMERIC(14,3) NOT NULL DEFAULT 0 CHECK(quantity>=0),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY(company_id,branch_id,product_id),
        FOREIGN KEY(company_id,branch_id) REFERENCES branches(company_id,id),
        FOREIGN KEY(company_id,product_id) REFERENCES products(company_id,id))""")
    op.execute("ALTER TABLE branch_inventory ENABLE ROW LEVEL SECURITY")

def downgrade():
    op.drop_table("branch_inventory")
    for table in ("employees","inventory_movements","orders","sales"):
        op.drop_column(table,"branch_id")
