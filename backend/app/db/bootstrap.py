import os

from sqlalchemy import create_engine, text

from app.core.config import settings
from app.core.security import hash_password


def main() -> None:
    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("ADMIN_PASSWORD", "")
    full_name = os.environ.get("ADMIN_NAME", "SalesIA Administrator").strip()
    company_name = os.environ.get("COMPANY_NAME", "SalesIA Enterprise").strip()
    currency = os.environ.get("COMPANY_CURRENCY", "PEN").upper()
    if not email or len(password) < 12:
        raise SystemExit("Define ADMIN_EMAIL y ADMIN_PASSWORD (mínimo 12 caracteres) para inicializar el primer usuario.")
    if len(currency) != 3:
        raise SystemExit("COMPANY_CURRENCY debe ser un código ISO de tres letras.")

    engine = create_engine(settings.database_url, pool_pre_ping=True)
    with engine.begin() as db:
        company_id = db.execute(text("SELECT id FROM companies ORDER BY id LIMIT 1")).scalar_one_or_none()
        if company_id is None:
            company_id = db.execute(text("INSERT INTO companies(name,currency) VALUES (:name,:currency) RETURNING id"), {"name": company_name, "currency": currency}).scalar_one()
        for code, name in [("admin", "Administrador"), ("manager", "Gerente"), ("seller", "Vendedor"), ("analyst", "Analista"), ("warehouse", "Almacén")]:
            db.execute(text("INSERT INTO roles(code,name) VALUES (:code,:name) ON CONFLICT (code) DO NOTHING"), {"code": code, "name": name})
        role_id = db.execute(text("SELECT id FROM roles WHERE code='admin'")).scalar_one()
        user_id = db.execute(text("SELECT id FROM users WHERE company_id=:company_id AND lower(email)=:email"), {"company_id": company_id, "email": email}).scalar_one_or_none()
        if user_id is None:
            user_id = db.execute(text("""INSERT INTO users(company_id,role_id,email,full_name,password_hash)
                                      VALUES (:company_id,:role_id,:email,:full_name,:password_hash) RETURNING id"""),
                                 {"company_id": company_id, "role_id": role_id, "email": email, "full_name": full_name, "password_hash": hash_password(password)}).scalar_one()
        employee_id = db.execute(text("SELECT id FROM employees WHERE company_id=:company_id AND user_id=:user_id LIMIT 1"), {"company_id": company_id, "user_id": user_id}).scalar_one_or_none()
        if employee_id is None:
            db.execute(text("INSERT INTO employees(company_id,user_id,full_name) VALUES (:company_id,:user_id,:name)"), {"company_id": company_id, "user_id": user_id, "name": full_name})
        print(f"Bootstrap listo. company_id={company_id}; admin_user_id={user_id}; email={email}")


if __name__ == "__main__":
    main()
