"""Check that hidden modules also reject direct API access."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.dependencies import get_current_user
from app.db.session import get_db

DENIED={
    'manager':['/users','/audit','/audit/actions'],
    'seller':['/users','/audit','/inventory','/inventory/movements','/employees','/analytics/datasets','/analytics/analyses','/insights','/reports'],
    'analyst':['/users','/audit','/sales','/orders','/customers','/products','/categories','/employees','/inventory'],
    'warehouse':['/users','/audit','/sales','/orders','/customers','/employees','/analytics/summary','/analytics/datasets','/insights','/reports'],
}


@pytest.mark.parametrize('role,path',[(role,path) for role,paths in DENIED.items() for path in paths])
def test_role_cannot_read_other_modules(role,path):
    app.dependency_overrides[get_current_user]=lambda:{'id':1,'company_id':1,'role':role,'session_version':0}
    app.dependency_overrides[get_db]=lambda:None
    try:
        with TestClient(app) as client:
            assert client.get('/api/v1'+path).status_code==403
    finally:
        app.dependency_overrides.pop(get_current_user,None)
        app.dependency_overrides.pop(get_db,None)
