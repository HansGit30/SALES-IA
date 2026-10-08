"""Block direct data API access; application access goes through FastAPI."""
from alembic import op

revision = "0008_backend_only_access"
down_revision = "0007_password_change"
branch_labels = None
depends_on = None

TABLES = (
    "companies", "roles", "users", "customers", "categories", "products",
    "employees", "sales", "sale_details", "payments", "inventory",
    "inventory_movements", "datasets", "dataset_variables", "observations",
    "statistical_analyses", "statistical_results", "bayes_analyses",
    "random_variables", "insights", "reports", "audit_logs", "orders",
    "order_details", "auth_rate_limits",
)


def upgrade():
    # No client policies: Supabase anon/authenticated roles cannot access rows.
    # The trusted backend connects as table owner; tenant checks remain in API.
    for table in TABLES:
        op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')


def downgrade():
    for table in reversed(TABLES):
        op.execute(f'ALTER TABLE public."{table}" DISABLE ROW LEVEL SECURITY')
