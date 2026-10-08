# Fase 05 — Backend / API

La API FastAPI se distribuye en routers por dominio, usa PostgreSQL/SQLAlchemy, configuración por entorno y autenticación bearer JWT. El usuario autenticado se vuelve a cargar desde la base y cada consulta operativa limita `company_id`; los permisos se validan en el backend.

Las rutas implementadas se listan en `README.md`. Las operaciones monetarias usan `Decimal` y los errores de integridad se devuelven como conflictos sin filtrar mensajes internos.

El primer administrador se crea con `python -m app.db.bootstrap` dentro de un entorno con el esquema aplicado. Se exige un secreto y una contraseña inicial por entorno; no se incluye una credencial real en el código.

## Estado

La sintaxis Python fue compilada. Aún no se ha ejecutado contra PostgreSQL porque Docker y `psql` no están disponibles en el entorno actual. Migraciones Alembic versionadas, restauración de contraseña y rate limiting quedan pendientes.
