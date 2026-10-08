"""Interactive initial administrator setup; passwords are never echoed."""
import os
from getpass import getpass

from pydantic import TypeAdapter, EmailStr, ValidationError
from app.db.bootstrap import main as bootstrap


def main():
    print("Crear administrador inicial de SalesIA")
    email = input("Correo del administrador: ").strip()
    try:
        email = str(TypeAdapter(EmailStr).validate_python(email))
    except ValidationError:
        raise SystemExit("El correo no es válido.") from None
    name = input("Nombre del administrador: ").strip()
    company = input("Nombre de la empresa: ").strip()
    if not name or not company:
        raise SystemExit("El nombre y la empresa son obligatorios.")
    password = getpass("Contraseña (mínimo 12 caracteres, no se mostrará): ")
    if len(password) < 12 or len(password) > 200:
        raise SystemExit("La contraseña debe tener entre 12 y 200 caracteres.")
    if password != getpass("Repite la contraseña: "):
        raise SystemExit("Las contraseñas no coinciden.")
    os.environ.update(ADMIN_EMAIL=email, ADMIN_PASSWORD=password,
                      ADMIN_NAME=name, COMPANY_NAME=company)
    try:
        bootstrap()
    finally:
        os.environ.pop("ADMIN_PASSWORD", None)


if __name__ == "__main__":
    main()
