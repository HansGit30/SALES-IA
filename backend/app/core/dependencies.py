from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DbSession, request: Request) -> dict:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "invalid_credentials", "message": "Sesión inválida o expirada"},
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub", ""))
        company_id = int(payload.get("company_id", 0))
    except (InvalidTokenError, TypeError, ValueError):
        raise credentials_error from None

    user = db.execute(
        text("""SELECT u.id, u.company_id, u.email, u.full_name, u.session_version, u.must_change_password, r.code AS role
                  FROM users u JOIN roles r ON r.id = u.role_id
                 WHERE u.id = :user_id AND u.company_id = :company_id AND u.is_active = TRUE"""),
        {"user_id": user_id, "company_id": company_id},
    ).mappings().first()
    if user is None or payload.get("session_version") != user["session_version"]:
        raise credentials_error
    if user["must_change_password"] and request.url.path not in {"/api/v1/auth/password", "/api/v1/auth/logout-all"}:
        raise HTTPException(status_code=403, detail={"code": "password_change_required", "message": "Cambia tu contraseña temporal para continuar"})
    return dict(user)


def require_roles(*roles: str):
    def check(user: Annotated[dict, Depends(get_current_user)]) -> dict:
        if user["role"] != "admin" and user["role"] not in roles:
            raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "No tienes permiso para esta acción"})
        return user

    return check

