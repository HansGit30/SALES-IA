"""Explicit opt-in integration audit. All fixture rows are rolled back.

Run from backend: python -m tests.integration_audit (or via runpy).
Uses an outer PostgreSQL transaction with per-request savepoints.
Sequences may advance; existing business rows are not changed.
"""
import secrets
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.main import app
from app.db.session import engine, get_db
from app.core.security import hash_password, create_access_token


def main():
    outcomes = []
    with engine.connect() as connection:
        transaction = connection.begin()
        def database():
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                yield session
        app.dependency_overrides[get_db] = database
        try:
            company = connection.execute(text("INSERT INTO companies(name) VALUES ('QA temporal revertido') RETURNING id")).scalar_one()
            role = connection.execute(text("SELECT id FROM roles WHERE code='admin'")).scalar_one()
            uid = connection.execute(text("""INSERT INTO users(company_id,role_id,email,full_name,password_hash)
                VALUES (:c,:r,'qa@example.invalid','QA temporal',:p) RETURNING id"""),
                {"c": company, "r": role, "p": hash_password(secrets.token_urlsafe(24))}).scalar_one()
            connection.execute(text("INSERT INTO employees(company_id,user_id,full_name) VALUES (:c,:u,'QA temporal')"), {"c":company,"u":uid})
            headers={"Authorization":"Bearer "+create_access_token(subject=str(uid),company_id=company,role="admin")}
            with TestClient(app, raise_server_exceptions=False) as client:
                def call(method, path, body=None, expected=200):
                    response=client.request(method,"/api/v1"+path,headers=headers,json=body)
                    ok=response.status_code==expected
                    outcomes.append((method+" "+path,ok,response.status_code))
                    print(("PASS " if ok else "FAIL ")+method+" "+path+" "+str(response.status_code),flush=True)
                    if not ok:
                        raise RuntimeError("Unexpected HTTP status; no response body logged")
                    return response.json() if response.content and "json" in response.headers.get("content-type","") else None
                for path in ["/customers?q=QA","/products?q=QA","/categories","/employees","/inventory","/inventory/movements","/orders","/sales","/analytics/filter-options","/analytics/summary","/analytics/sales-series","/analytics/analyses","/insights","/reports","/reports/filter-options","/audit","/audit/actions"]:
                    call("GET",path)
                category=call("POST","/categories",{"name":"QA"},201)
                customer=call("POST","/customers",{"name":"QA cliente"},201)
                product=call("POST","/products",{"sku":"QA-"+secrets.token_hex(4),"name":"QA producto","unit_price":"10.00","category_id":category["id"]},201)
                call("POST","/inventory/adjustments",{"product_id":product["id"],"quantity_delta":"10","reason":"QA rollback"},201)
                sale=call("POST","/sales",{"customer_id":customer["id"],"items":[{"product_id":product["id"],"quantity":"2"}],"payments":[{"method":"cash","amount":"20.00"}]},201)
                quantity=connection.execute(text("SELECT quantity FROM inventory WHERE company_id=:c AND product_id=:p"),{"c":company,"p":product["id"]}).scalar_one()
                assert quantity==Decimal("8"), "Stock mismatch"
                print("PASS stock 10 -> 8",flush=True)
                call("GET","/sales/"+str(sale["id"]))
                history=call("GET","/customers/"+str(customer["id"])+"/history")
                assert len(history["sales"])==1 and history["totals"][0]["sales_count"]==1
                for kind in ["products","customers","sellers"]:
                    grouped=call("POST","/reports/sales",{"report_type":kind},201)
                    assert len(grouped["groups"])==1
                    assert Decimal(grouped["groups"][0]["revenue"])==20
                    call("GET","/reports/"+str(grouped["id"])+"/download")
                    pdf=client.get('/api/v1/reports/'+str(grouped['id'])+'/pdf',headers=headers)
                    assert pdf.status_code==200 and pdf.content.startswith(b'%PDF-')

                report=call("POST","/reports/sales",{"customer_id":customer["id"],"product_id":product["id"]},201)
                assert report["summary"]["sales_count"]==1
                call("GET","/reports/"+str(report["id"])+"/download")
                for path in ['/reports/'+str(report['id'])+'/pdf','/sales/'+str(sale['id'])+'/pdf']:
                    pdf=client.get('/api/v1'+path,headers=headers)
                    assert pdf.status_code==200 and pdf.content.startswith(b'%PDF-')
                print('PASS PDF exports for report groups, sales report and receipt',flush=True)
                call("POST","/sales/"+str(sale["id"])+"/void",{"reason":"QA rollback","refund_confirmed":True,"restock_confirmed":True})
                quantity=connection.execute(text("SELECT quantity FROM inventory WHERE company_id=:c AND product_id=:p"),{"c":company,"p":product["id"]}).scalar_one()
                assert quantity==Decimal("10"), "Restock mismatch"
                archived=call("GET","/reports/"+str(report["id"]))
                assert archived["summary"]["sales_count"]==1, "Snapshot changed"
                print("PASS stock restored and report preserved",flush=True)
                branch=call("POST","/branches",{"code":"QA","name":"QA sede","address":"Direccion QA","city":"Lima","latitude":"-12.046374","longitude":"-77.042793"},201)
                call("POST","/inventory/adjustments",{"branch_id":branch["id"],"product_id":product["id"],"quantity_delta":"5","reason":"QA sede"},201)
                branch_sale=call("POST","/sales",{"branch_id":branch["id"],"items":[{"product_id":product["id"],"quantity":"1"}],"payments":[{"method":"cash","amount":"10.00"}]},201)
                stock=call("GET","/inventory?branch_id="+str(branch["id"]))
                assert Decimal(str(stock[0]["quantity"]))==4
                call("GET","/products?branch_id="+str(branch["id"]))
                summary=call("GET","/analytics/summary?branch_id="+str(branch["id"]))
                assert summary["transaction_count"]==1
                breakdown=call("GET","/analytics/breakdown?branch_id="+str(branch["id"])+"&category_id="+str(category["id"]))
                assert len(breakdown["products"])==1 and Decimal(str(breakdown["products"][0]["revenue"]))==10
                assert breakdown["sellers"][0]["transactions"]==1
                assert breakdown["frequencies"]==[{"currency":"PEN","band":0,"frequency":1}]
                call("GET","/analytics/breakdown?start=2026-10-03&end=2026-10-01",expected=422)

                employee=call("POST","/employees",{"full_name":"QA sede vendedor","branch_id":branch["id"]},201)
                edited=call("PUT","/employees/"+str(employee["id"]),{"full_name":"QA sede vendedor","is_active":True,"branch_id":branch["id"]})
                assert edited["branch_id"]==branch["id"]
                metrics=call("GET","/branches/"+str(branch["id"])+"/summary")
                assert Decimal(str(metrics["units"]))==4 and metrics["products"]==1
                assert metrics["staff"]==1
                assert metrics["sales_visible"] and Decimal(str(metrics["sales"][0]["revenue"]))==10
                call("GET","/branches/0/summary",expected=404)

                call("POST","/sales/"+str(branch_sale["id"])+"/void",{"reason":"QA branch","refund_confirmed":True,"restock_confirmed":True})
                order=call("POST","/orders",{"branch_id":branch["id"],"items":[{"product_id":product["id"],"quantity":"1"}]},201)
                call("POST","/orders/"+str(order["id"])+"/confirm",{"payments":[{"method":"cash","amount":"10.00"}]})
                stock=call("GET","/inventory?branch_id="+str(branch["id"]))
                assert Decimal(str(stock[0]["quantity"]))==4
                general=call("GET","/inventory")
                assert Decimal(str(general[0]["quantity"]))==10
                print("PASS branch stock, order conversion and independent general inventory",flush=True)
                priced=call("POST","/sales",{"items":[{"product_id":product["id"],"quantity":"2","discount_percent":"10","tax_percent":"18"}],"payments":[{"method":"cash","amount":"21.24"}]},201)
                assert Decimal(str(priced["subtotal"]))==20
                assert Decimal(str(priced["discount_total"]))==2
                assert Decimal(str(priced["tax_total"]))==Decimal("3.24")
                assert Decimal(str(priced["total"]))==Decimal("21.24")
                call("POST","/sales/"+str(priced["id"])+"/void",{"reason":"QA impuestos","refund_confirmed":True,"restock_confirmed":True})
                print("PASS discounts, taxes, payment reconciliation and cancellation",flush=True)
                call("POST","/inventory/adjustments",{"product_id":product["id"],"quantity_delta":"-6","reason":"QA alerta stock"},201)
                generated=call("POST","/insights/generate")
                assert generated["created"]>=1
                alerts=call("GET","/insights")
                alert=next(row for row in alerts if row["rule_code"]=="inventory_low_stock")
                trace=call("GET","/insights/"+str(alert["id"])+"/trace")
                assert trace["available"] and trace["dataset_id"] and trace["analysis_id"]
                assert Decimal(str(trace["observations"][0]["numeric_value"]))==4
                repeated=call("POST","/insights/generate")
                assert repeated["created"]==0 and repeated["unchanged"]>=1
                same_trace=call("GET","/insights/"+str(alert["id"])+"/trace")
                assert same_trace["analysis_id"]==trace["analysis_id"]
                call("POST","/inventory/adjustments",{"product_id":product["id"],"quantity_delta":"6","reason":"QA restaurar stock"},201)
                resolved=call("POST","/insights/generate")
                assert resolved["resolved"]>=1
                print("PASS insight dataset, analysis, observations, deduplication and resolution",flush=True)

                random=call("POST","/probability/random-variables/analyze",{"name":"QA discreta","outcomes":[{"value":0,"probability":0.5},{"value":1,"probability":0.5}]},201)
                assert random["mean"]==0.5 and random["variance"]==0.25
                datasets=call("GET","/analytics/datasets")
                dataset=next(row for row in datasets if row["name"]=="Variable aleatoria: QA discreta")
                detail=call("GET","/analytics/datasets/"+str(dataset["id"]))
                assert len(detail["observations"])==2 and all(row["text_value"] is None for row in detail["observations"])
                assert detail["analyses"][0]["parameters"]["outcomes"][0]["probability"]==0.5
                call("PUT","/pricing",{"default_tax_percent":"18","default_discount_percent":"10","allow_pricing_override":False})
                call("POST","/sales",{"items":[{"product_id":product["id"],"quantity":1,"tax_percent":0}],"payments":[{"method":"cash","amount":10}]},expected=409)
                priced_order=call("POST","/orders",{"items":[{"product_id":product["id"],"quantity":2}]},201)
                assert Decimal(str(priced_order["total"]))==Decimal("21.24")
                converted=call("POST","/orders/"+str(priced_order["id"])+"/confirm",{"payments":[{"method":"cash","amount":"21.24"}]})
                priced_detail=call("GET","/sales/"+str(converted["sale_id"]))
                assert Decimal(str(priced_detail["total"]))==Decimal("21.24")
                call("PUT","/pricing",{"default_tax_percent":"0","default_discount_percent":"0","allow_pricing_override":True})
                account=call("POST","/users",{"email":"qa-managed@example.com","full_name":"QA managed","password":secrets.token_urlsafe(24),"role":"seller"},201)
                call("PUT","/users/"+str(account["id"]),{"full_name":"QA managed","role":"analyst","is_active":False})
                status=connection.execute(text("SELECT is_active,session_version FROM users WHERE company_id=:c AND id=:u"),{"c":company,"u":account["id"]}).mappings().one()
                assert not status["is_active"] and status["session_version"]==1
                call("PUT","/users/"+str(uid),{"full_name":"QA temporal","role":"seller","is_active":True},expected=409)
                overview=call("GET","/analytics/breakdown")
                assert overview["customers"] and "share_percent" in overview["products"][0] and "average_ticket" in overview["sellers"][0]
                audited=set(connection.execute(text("SELECT action FROM audit_logs WHERE company_id=:c"),{"c":company}).scalars())
                assert {"product.created","customer.created","category.created","employee.created","pricing.updated","user.updated","analytics.random_variable_created"}.issubset(audited)
                print("PASS random variable persistence, datasets, pricing policies/orders, user updates and audit events",flush=True)
                for operation in ["mean", "median", "compare"]:
                    result=call("POST","/statistics/"+operation,{"values":[10,20,30]})
                    saved=call("GET","/analytics/datasets/"+str(result["dataset_id"]))
                    assert len(saved["observations"])==3
                    assert result.get("mean",20)==20 and result.get("median",20)==20
                call("POST","/statistics/mean",{"values":[1e12]},422)
                print("PASS manual statistics persisted with observations",flush=True)
                original_headers=headers
                other_company=connection.execute(text("INSERT INTO companies(name) VALUES ('QA aislamiento revertido') RETURNING id")).scalar_one()
                other_uid=connection.execute(text("INSERT INTO users(company_id,role_id,email,full_name,password_hash) VALUES (:c,:r,'isolation@example.invalid','QA aislamiento',:p) RETURNING id"),{"c":other_company,"r":role,"p":hash_password(secrets.token_urlsafe(24))}).scalar_one()
                headers={"Authorization":"Bearer "+create_access_token(subject=str(other_uid),company_id=other_company,role="admin")}
                call("GET","/insights/"+str(alert["id"])+"/trace",expected=404)
                isolated=call("GET","/analytics/breakdown?branch_id="+str(branch["id"]))
                assert isolated["products"]==[] and isolated["sellers"]==[] and isolated["frequencies"]==[]
                call("GET","/customers/"+str(customer["id"])+"/history",expected=404)
                call("GET","/branches/"+str(branch["id"])+"/summary",expected=404)
                seller_role=connection.execute(text("SELECT id FROM roles WHERE code='seller'")).scalar_one()
                seller_uid=connection.execute(text("INSERT INTO users(company_id,role_id,email,full_name,password_hash) VALUES (:c,:r,'seller@example.invalid','QA vendedor',:p) RETURNING id"),{"c":company,"r":seller_role,"p":hash_password(secrets.token_urlsafe(24))}).scalar_one()
                headers={"Authorization":"Bearer "+create_access_token(subject=str(seller_uid),company_id=company,role="seller")}
                own=call("GET","/analytics/breakdown")
                assert own["products"]==[] and own["sellers"]==[] and own["frequencies"]==[]
                limited=call("GET","/branches/"+str(branch["id"])+"/summary")
                assert not limited["sales_visible"] and limited["sales"]==[]
                call("POST","/reports/sales",{},expected=403)
                headers=original_headers
                print("PASS tenant isolation and seller access restrictions",flush=True)


        finally:
            app.dependency_overrides.pop(get_db,None)
            transaction.rollback()
            print("ROLLBACK completed: fixture rows not retained",flush=True)
    print("Integration audit completed",flush=True)


if __name__=="__main__":
    main()
