import importlib.util
from pathlib import Path

import pytest


@pytest.mark.parametrize("filename,sql_file,expected", [
    ("0001_initial_schema.py", "schema.sql", "CREATE TABLE companies"),
    ("0002_orders.py", "orders.sql", "CREATE TABLE orders"),
])
def test_migrations_find_sql_in_container_layout(tmp_path, monkeypatch, filename, sql_file, expected):
    project = Path(__file__).parents[2]
    migration = project / "backend" / "alembic" / "versions" / filename
    spec = importlib.util.spec_from_file_location("migration_layout_check", migration)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    container = tmp_path / "app"
    (container / "alembic" / "versions").mkdir(parents=True)
    (container / "database").mkdir()
    (container / "database" / sql_file).write_text((project / "database" / sql_file).read_text(encoding="utf-8-sig"), encoding="utf-8")
    monkeypatch.setattr(module, "__file__", str(container / "alembic" / "versions" / filename))
    statements = []
    monkeypatch.setattr(module.op, "execute", statements.append)
    module.upgrade()
    assert any(expected in statement for statement in statements)
