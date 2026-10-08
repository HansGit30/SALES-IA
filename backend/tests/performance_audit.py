"""Opt-in volume smoke test; all synthetic data is rolled back."""
import secrets
from time import perf_counter
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.main import app
from app.db.session import engine, get_db
from app.core.security import hash_password, create_access_token


def main():
    with engine.connect() as connection:
        transaction = connection.begin()
        def database():
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                yield session
        app.dependency_overrides[get_db] = database
        try:
            company = connection.execute(text("INSERT INTO companies(name) VALUES ('QA volumen rollback') RETURNING id")).scalar_one()
            role = connection.execute(text("SELECT id FROM roles WHERE code='admin'")).scalar_one()
            user = connection.execute(text("INSERT INTO users(company_id,role_id,email,full_name,password_hash) VALUES (:c,:r,'volume@example.invalid','QA volumen',:p) RETURNING id"), {"c":company,"r":role,"p":hash_password(secrets.token_urlsafe(32))}).scalar_one()
            employee = connection.execute(text("INSERT INTO employees(company_id,user_id,full_name) VALUES (:c,:u,'QA volumen') RETURNING id"),{"c":company,"u":user}).scalar_one()
            product = connection.execute(text("INSERT INTO products(company_id,sku,name,unit_price) VALUES (:c,'QA-VOLUME','QA volumen',10) RETURNING id"),{"c":company}).scalar_one()
            connection.execute(text("""INSERT INTO sales(company_id,seller_id,created_by,currency,subtotal,total,sold_at)
                SELECT :c,:e,:u,'PEN',10,10,now()-(n%90)*interval '1 day' FROM generate_series(1,10000) AS n"""),{"c":company,"e":employee,"u":user})
            connection.execute(text("""INSERT INTO sale_details(company_id,sale_id,product_id,product_name_snapshot,sku_snapshot,quantity,unit_price,line_total)
                SELECT :c,id,:p,'QA volumen','QA-VOLUME',1,10,10 FROM sales WHERE company_id=:c"""),{"c":company,"p":product})
            headers={"Authorization":"Bearer "+create_access_token(subject=str(user),company_id=company,role="admin")}
            with TestClient(app) as client:
                for path in ["/analytics/summary","/analytics/breakdown","/analytics/sales-series"]:
                    timings=[]
                    for _ in range(3):
                        start=perf_counter()
                        response=client.get('/api/v1'+path,headers=headers)
                        timings.append(round(perf_counter()-start,3))
                        assert response.status_code==200, path
                    print(f"PASS {path}: 10000 sales/10000 lines; seconds={timings}",flush=True)
        finally:
            app.dependency_overrides.pop(get_db,None)
            transaction.rollback()
            print("ROLLBACK volume fixture completed",flush=True)


if __name__ == '__main__':
    main()
