"""Local-only UI acceptance server. Synthetic tenant is committed for UI requests and removed on graceful shutdown.

Run explicitly with python -m tests.ui_fixture; stop with Ctrl+C.
Never included in the production entry point. Credentials are temporary test data.
"""
import json
import secrets
from pathlib import Path
from threading import Thread
from time import sleep
import uvicorn
from sqlalchemy import text
from app.main import app
from app.db.session import engine, get_db, SessionLocal
from app.core.security import hash_password


def main():
    marker = 'QA-UI-' + secrets.token_hex(12)
    company = None
    credentials = Path('tests/.ui-fixture.json')
    with engine.connect() as connection:
        transaction = connection.begin()
        def database():
            with SessionLocal() as session:
                yield session
        app.dependency_overrides[get_db] = database
        try:
            company=connection.execute(text("INSERT INTO companies(name) VALUES (:name) RETURNING id"),{'name':marker}).scalar_one()
            password=secrets.token_urlsafe(24)
            accounts={}
            for role in ['admin','manager','seller','analyst','warehouse']:
                role_id=connection.execute(text('SELECT id FROM roles WHERE code=:role'),{'role':role}).scalar_one()
                uid=connection.execute(text("INSERT INTO users(company_id,role_id,email,full_name,password_hash) VALUES (:c,:r,:email,:name,:password) RETURNING id"),{'c':company,'r':role_id,'email':role+'@example.com','name':'QA '+role,'password':hash_password(password)}).scalar_one()
                eid=connection.execute(text("INSERT INTO employees(company_id,user_id,full_name) VALUES (:c,:u,:name) RETURNING id"),{'c':company,'u':uid,'name':'QA '+role}).scalar_one()
                accounts[role]={'id':uid,'employee':eid}
            product=connection.execute(text("INSERT INTO products(company_id,sku,name,unit_price) VALUES (:c,'QA-PORTATIL','Portatil empresarial de prueba',1250) RETURNING id"),{'c':company}).scalar_one()
            connection.execute(text("INSERT INTO inventory(company_id,product_id,quantity) VALUES (:c,:p,100)"),{'c':company,'p':product})
            connection.execute(text("""INSERT INTO sales(company_id,seller_id,created_by,currency,subtotal,total,sold_at)
                SELECT :c,:e,:u,'PEN',1250,1250,now()-(n%20)*interval '1 day' FROM generate_series(1,120) AS n"""),{'c':company,'e':accounts['seller']['employee'],'u':accounts['admin']['id']})
            connection.execute(text("""INSERT INTO sale_details(company_id,sale_id,product_id,product_name_snapshot,sku_snapshot,quantity,unit_price,line_total)
                SELECT :c,id,:p,'Portatil empresarial de prueba','QA-PORTATIL',1,1250,1250 FROM sales WHERE company_id=:c"""),{'c':company,'p':product})
            credentials.write_text(json.dumps({'company':company,'marker':marker,'password':password,'email':'admin@example.com'}),encoding='utf-8')
            transaction.commit()
            for middleware in app.user_middleware:
                if middleware.cls.__name__=='CORSMiddleware':
                    middleware.kwargs['allow_origins']=[*middleware.kwargs['allow_origins'],'http://localhost:5175']
            print('QA ready: local-only port 8001; disposable tenant removed on graceful shutdown',flush=True)
            server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=8001,access_log=False))
            stop=Path('tests/.ui-stop')
            stop.unlink(missing_ok=True)
            def watch_stop():
                while not server.should_exit:
                    if stop.exists():
                        stop.unlink(missing_ok=True)
                        server.should_exit=True
                        break
                    sleep(0.5)
            Thread(target=watch_stop,daemon=True).start()
            server.run()
        finally:
            app.dependency_overrides.pop(get_db,None)
            if transaction.is_active:
                transaction.rollback()
            if company is not None:
                with engine.begin() as cleanup:
                    owned=cleanup.execute(text('SELECT id FROM companies WHERE id=:id AND name=:name FOR UPDATE'),{'id':company,'name':marker}).scalar_one_or_none()
                    if owned:
                        tables=set(cleanup.execute(text("SELECT table_name FROM information_schema.columns WHERE table_schema='public' AND column_name='company_id'")).scalars())
                        dependencies=cleanup.execute(text("""SELECT child.relname,parent.relname FROM pg_constraint fk
                            JOIN pg_class child ON child.oid=fk.conrelid JOIN pg_class parent ON parent.oid=fk.confrelid
                            JOIN pg_namespace ns ON ns.oid=child.relnamespace WHERE fk.contype='f' AND ns.nspname='public'""")).all()
                        while tables:
                            leaves={table for table in tables if not any(parent==table and child in tables and child!=table for child,parent in dependencies)}
                            if not leaves: raise RuntimeError('Cannot safely order fixture cleanup')
                            for table in sorted(leaves):
                                if not table.replace('_','').isalnum(): raise RuntimeError('Invalid table identifier')
                                cleanup.execute(text('DELETE FROM "'+table+'" WHERE company_id=:company'),{'company':company})
                            tables-=leaves
                        cleanup.execute(text('DELETE FROM companies WHERE id=:company AND name=:name'),{'company':company,'name':marker})
            credentials.unlink(missing_ok=True)
            print('QA fixture cleaned',flush=True)


if __name__=='__main__':
    main()
