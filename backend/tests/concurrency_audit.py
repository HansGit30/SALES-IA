"""Opt-in PostgreSQL audit using a disposable tenant and real independent commits.
Deletes only its uniquely named fixture tenant and its own rows after workers finish.
"""
import secrets
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from sqlalchemy import text
from fastapi import HTTPException
from app.db.session import engine,SessionLocal
from app.api.routes.sales import persist_sale
from app.schemas.sales import SaleCreate
from app.api.routes.orders import create_order,confirm_order,OrderCreate,OrderConfirm
from app.core.security import hash_password


def main():
    marker="QA-concurrency-"+secrets.token_hex(12)
    company=None
    try:
        with engine.begin() as db:
            company=db.execute(text("INSERT INTO companies(name) VALUES (:name) RETURNING id"),{"name":marker}).scalar_one()
            role=db.execute(text("SELECT id FROM roles WHERE code='admin'")).scalar_one()
            uid=db.execute(text("INSERT INTO users(company_id,role_id,email,full_name,password_hash) VALUES (:c,:r,'concurrency@example.invalid','QA temporal',:p) RETURNING id"),{"c":company,"r":role,"p":hash_password(secrets.token_urlsafe(32))}).scalar_one()
            db.execute(text("INSERT INTO employees(company_id,user_id,full_name) VALUES (:c,:u,'QA temporal')"),{"c":company,"u":uid})
            product=db.execute(text("INSERT INTO products(company_id,sku,name,unit_price) VALUES (:c,'QA','QA concurrency',10) RETURNING id"),{"c":company}).scalar_one()
            db.execute(text("INSERT INTO inventory(company_id,product_id,quantity) VALUES (:c,:p,1)"),{"c":company,"p":product})
        user={"id":uid,"company_id":company,"role":"admin"}
        barrier=Barrier(2)
        payload=SaleCreate(items=[{"product_id":product,"quantity":1}],payments=[{"method":"cash","amount":10}])
        def worker():
            with SessionLocal() as db:
                barrier.wait(timeout=30)
                try:
                    persist_sale(payload,db,user)
                    return 201
                except HTTPException as exc:
                    return exc.status_code
        with ThreadPoolExecutor(max_workers=2) as executor:
            jobs=[executor.submit(worker) for _ in range(2)]
            results=[job.result(timeout=60) for job in jobs]
        assert sorted(results)==[201,409],"Expected exactly one successful sale"
        with engine.connect() as db:
            assert db.execute(text("SELECT quantity FROM inventory WHERE company_id=:c AND product_id=:p"),{"c":company,"p":product}).scalar_one()==0
            assert db.execute(text("SELECT COUNT(*) FROM sales WHERE company_id=:c"),{"c":company}).scalar_one()==1
            assert db.execute(text("SELECT COUNT(*) FROM payments WHERE company_id=:c"),{"c":company}).scalar_one()==1
        print("PASS independent concurrent sales: one commit, one conflict, no overselling or duplicate payment",flush=True)
        with SessionLocal() as db:
            db.execute(text("UPDATE inventory SET quantity=1 WHERE company_id=:c AND product_id=:p"),{"c":company,"p":product})
            db.commit()
            order=create_order(OrderCreate(items=[{"product_id":product,"quantity":1}]),db,user)
        barrier=Barrier(2)
        def confirm_worker():
            with SessionLocal() as db:
                barrier.wait(timeout=30)
                try:
                    confirm_order(order["id"],OrderConfirm(payments=[{"method":"cash","amount":10}]),db,user)
                    return 200
                except HTTPException as exc:
                    return exc.status_code
        with ThreadPoolExecutor(max_workers=2) as executor:
            jobs=[executor.submit(confirm_worker) for _ in range(2)]
            results=[job.result(timeout=60) for job in jobs]
        assert sorted(results)==[200,409],"Expected one conversion and one conflict"
        with engine.connect() as db:
            assert db.execute(text("SELECT COUNT(*) FROM sales WHERE company_id=:c"),{"c":company}).scalar_one()==2
            assert db.execute(text("SELECT quantity FROM inventory WHERE company_id=:c AND product_id=:p"),{"c":company,"p":product}).scalar_one()==0
        print("PASS concurrent order confirmation: exactly one conversion and stock deduction",flush=True)

    finally:
        if company is not None:
            with engine.begin() as db:
                name=db.execute(text("SELECT name FROM companies WHERE id=:c FOR UPDATE"),{"c":company}).scalar_one_or_none()
                if name is not None:
                    assert name==marker and marker.startswith("QA-concurrency-"),"Fixture ownership mismatch"
                    for table in ("audit_logs","order_details","orders","inventory_movements","payments","sale_details","sales","inventory","products","employees","users"):
                        db.execute(text(f"DELETE FROM {table} WHERE company_id=:c"),{"c":company})
                    db.execute(text("DELETE FROM companies WHERE id=:c AND name=:name"),{"c":company,"name":marker})
            print("CLEANUP completed for disposable concurrency tenant",flush=True)

if __name__=="__main__":
    main()
