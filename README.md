# SalesIA Enterprise

Sistema web empresarial para ventas, clientes, productos, inventario y analítica comercial. La implementación avanza en las 16 fases del plan; las partes pendientes permanecen explícitas en `docs/roadmap-entrega.md`.

## Progreso

| Fase | Entregable | Estado actual |
|---|---|---|
| 01 | Requisitos y alcance completo | Documentado |
| 02 | Arquitectura y contratos | Documentado |
| 03 | UX/UI y navegación | Sistema visual común y módulos responsive; revisión contra todos los estados aún en curso |
| 04 | PostgreSQL y modelo de datos | Esquema y migración inicial escritos; falta ejecución sobre PostgreSQL |
| 05 | FastAPI, login, roles y servicios | API implementada; falta ejecución integrada |
| 06 | React/TypeScript | Login, shell por rol, dashboard y módulos principales conectados a la API |
| 07 | Catálogos y vendedores | Cuatro catálogos con altas, edición y estados; búsqueda/paginación implementadas, integración pendiente |
| 08 | Pedidos, ventas, pagos e inventario | Pedidos, ventas, recibo imprimible, devolución completa confirmada e historial; validación integrada pendiente |
| 09 | Motor estadístico | Estadística descriptiva, comparaciones, variables discretas, Bayes e historial; validación numérica pendiente |
| 10 | Dashboard Analytics | KPIs, selector de periodo, series e historial conectados |
| 11 | Insights | Reglas por periodo, evidencia legible e historial sin duplicados implementados; integración pendiente |
| 12 | Reportes | Reportes comerciales/estadísticos con copia persistida, historial y CSV; validación integrada pendiente |
| 13 | Seguridad y auditoría | Revocación, cambio de clave, recuperación asistida, límites de acceso y explorador de auditoría; integración pendiente |
| 14 | Pruebas y calidad | 83 pruebas backend y 8 frontend aprobadas; CI configurada, integración pendiente |
| 15 | Despliegue | Recetas de desarrollo y web compilada con Nginx; respaldo y actualización documentados; ejecución pendiente |
| 16 | Cierre y manuales | README, arquitectura, manual inicial y roadmap; documentación operativa pendiente |

## Requisitos locales

Docker Desktop con Docker Compose. Copia `.env.example` a `.env`, cambia `SECRET_KEY` y define una contraseña inicial de al menos 12 caracteres en `ADMIN_PASSWORD`.

```powershell
Copy-Item .env.example .env
# Edita .env y asigna secretos propios.
docker compose up --build
```

Abre `http://localhost:5173`. La API y documentación OpenAPI estarán en `http://localhost:8000` y `http://localhost:8000/docs`. Para el primer inicio, Compose aplica las siete migraciones desde el esquema inicial y el servicio `bootstrap` imprime el `company_id` del administrador; el valor inicial es normalmente `1`.

La base de datos guarda el estado en un volumen Docker. No elimines volúmenes para actualizar la app. Hay siete migraciones versionadas; falta validar una actualización con datos existentes antes de usarla en producción.

## API inicial

- `POST /api/v1/auth/login`
- `GET|POST /api/v1/users` (administrador)
- `GET|POST /api/v1/customers`
- `GET|POST /api/v1/products`
- `GET|POST /api/v1/sales`, `GET /api/v1/sales/{id}`, `POST /api/v1/sales/{id}/void`
- `GET /api/v1/inventory`, `/movements`, `POST /api/v1/inventory/adjustments`
- `GET /api/v1/analytics/summary`, `/sales-series`, `/analyses`
- `POST /api/v1/analytics/analyses`
- `POST /api/v1/statistics/mean`, `/median`, `/compare`
- `POST /api/v1/probability/bayes`, `/random-variables/analyze`
- `GET|POST /api/v1/insights`
- `GET|POST /api/v1/reports`, `GET /api/v1/reports/sales.csv`
- `GET /api/v1/audit` (administrador)




### Actualización de seguridad (fase 13)

Aplicar `alembic upgrade head` antes de iniciar la API: las migraciones 0005 y 0006 incorporan revocación de sesiones y límites compartidos de autenticación. El esquema completo tiene 25 tablas. Los parámetros `AUTH_WINDOW_SECONDS`, `AUTH_ACCOUNT_ATTEMPTS` y `AUTH_IP_ATTEMPTS` se documentan en `backend/.env.example`. La implementación y las comprobaciones pendientes están descritas en `docs/fase-13-seguridad.md`.

La migración 0007 añade cambio obligatorio de contraseña para altas y recuperaciones administrativas. En Configuración se restablece el acceso de otro usuario activo; la clave temporal se entrega manualmente y debe cambiarse al entrar.

La cabecera consulta `/ready` para informar disponibilidad. `/health` indica que la API está viva; `/ready` requiere conexión a PostgreSQL y revisiones Alembic actuales. Compose espera este segundo estado antes de iniciar la web. Los puertos del entorno de desarrollo se publican únicamente en 127.0.0.1.

Para la versión compilada usar `compose.release.yml`; consultar `docs/fase-15-despliegue.md` para arranque, respaldo y actualización. Esta receta usa un volumen separado del entorno de desarrollo.
