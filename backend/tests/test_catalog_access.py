import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.common import CustomerUpdate, ProductUpdate
from app.api.routes.categories import CategoryCreate, CategoryUpdate
from app.api.routes.employees import EmployeeCreate, EmployeeUpdate


@pytest.mark.parametrize("schema,payload", [
    (CustomerUpdate, {"name": "   ", "is_active": True}),
    (ProductUpdate, {"name": "Producto", "sku": "   ", "unit_price": "10.00", "is_active": True}),
    (CategoryCreate, {"name": "   "}),
    (CategoryUpdate, {"name": "   ", "is_active": False}),
    (EmployeeCreate, {"full_name": "   "}),
    (EmployeeUpdate, {"full_name": "   ", "is_active": True}),
])
def test_catalog_rejects_names_or_codes_containing_only_spaces(schema, payload):
    with pytest.raises(ValidationError):
        schema(**payload)


@pytest.mark.parametrize("role,endpoint,payload", [
    ("manager", "/customers/1", {"name": "Cliente", "is_active": False}),
    ("warehouse", "/customers/1", {"name": "Cliente", "is_active": True}),
    ("analyst", "/customers/1", {"name": "Cliente", "is_active": True}),
    ("seller", "/products/1", {"name": "Producto", "sku": "A", "unit_price": "10", "is_active": False}),
    ("warehouse", "/products/1", {"name": "Producto", "sku": "A", "unit_price": "10", "is_active": True}),
    ("manager", "/categories/1", {"name": "Categoría", "is_active": False}),
    ("seller", "/categories/1", {"name": "Categoría", "is_active": True}),
    ("warehouse", "/categories/1", {"name": "Categoría", "is_active": True}),
    ("manager", "/employees/1", {"full_name": "Vendedor", "is_active": False}),
    ("seller", "/employees/1", {"full_name": "Vendedor", "is_active": True}),
])
def test_catalog_updates_reject_unauthorized_roles_before_database_access(role, endpoint, payload):
    class NoDatabaseAccess:
        def execute(self, *args, **kwargs):
            pytest.fail("An unauthorized request reached the database")

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: NoDatabaseAccess()
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "company_id": 1, "role": role}
    try:
        with TestClient(app) as client:
            response = client.put("/api/v1" + endpoint, json=payload)
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "forbidden"
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
