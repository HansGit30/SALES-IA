"""Add orders and order details without changing the initial migration."""
from pathlib import Path

from alembic import op

revision = "0002_orders"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    location = Path(__file__).resolve()
    candidates = [location.parents[2] / "database" / "orders.sql", location.parents[3] / "database" / "orders.sql"]
    path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if path is None:
        raise RuntimeError("No se encontró database/orders.sql en el proyecto o contenedor")
    source = path.read_text(encoding="utf-8-sig")
    source = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("--"))
    for statement in source.split(";"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    op.drop_table("order_details")
    op.drop_table("orders")
