"""Create the SalesIA PostgreSQL schema."""
from pathlib import Path

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    location = Path(__file__).resolve()
    candidates = [location.parents[2] / "database" / "schema.sql", location.parents[3] / "database" / "schema.sql"]
    schema_path = next((path for path in candidates if path.is_file()), None)
    if schema_path is None:
        raise RuntimeError("No se encontró database/schema.sql en el proyecto o contenedor")
    pending: list[str] = []
    statements: list[str] = []
    for line in schema_path.read_text(encoding="utf-8-sig").splitlines():
        if line.lstrip().startswith("--"):
            continue
        pending.append(line)
        if line.rstrip().endswith(";"):
            statements.append("\n".join(pending).strip().rstrip(";"))
            pending.clear()
    if pending and "\n".join(pending).strip():
        raise RuntimeError("La definición SQL terminó con una instrucción incompleta")
    for statement in statements:
        if statement:
            op.execute(statement)


def downgrade() -> None:
    for table in (
        "audit_logs", "reports", "insights", "random_variables", "bayes_analyses",
        "statistical_results", "statistical_analyses", "observations", "dataset_variables",
        "datasets", "inventory_movements", "inventory", "payments", "sale_details", "sales",
        "employees", "products", "categories", "customers", "users", "roles", "companies",
    ):
        op.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')

