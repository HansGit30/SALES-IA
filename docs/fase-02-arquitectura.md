# SalesIA Enterprise — Fase 02: arquitectura técnica

**Versión:** 1.0 · **Estado:** propuesta técnica de implementación

## Decisiones de arquitectura

| Área | Decisión | Motivo |
|---|---|---|
| Frontend | React + TypeScript + Vite | Aplicación modular y tipada, acorde al plan. |
| Backend | Python + FastAPI | API REST tipada y documentación OpenAPI automática. |
| Persistencia | PostgreSQL | Transacciones e integridad relacional para ventas e inventario. |
| ORM/migraciones | SQLAlchemy 2 + Alembic | Modelos y evolución versionada del esquema. |
| Validación API | Pydantic | Contratos de entrada/salida y errores consistentes. |
| Analítica | Python; NumPy/Pandas/SciPy solo donde aporten | Cálculos reproducibles en servicios de dominio. |
| UI | Componentes React por dominio | Reutilización y separación de pantallas. |
| Comunicación | JSON sobre REST/HTTPS | Contratos simples, documentables y consumibles por frontend. |

## Límites y dependencias

- El navegador nunca conecta directamente a PostgreSQL.
- Los routers HTTP traducen solicitudes; las reglas viven en servicios de dominio.
- Repositorios/consultas encapsulan persistencia.
- Los servicios de ventas usan una transacción de base de datos para venta, detalle, pago y movimiento de inventario.
- El motor analítico recibe datos tipados y filtros explícitos; cada análisis guarda parámetros, rango, fecha, usuario y resultados.
- La autorización se verifica en cada endpoint; ocultar botones no es control de acceso.
- La interfaz presenta estados de carga, vacío, error y éxito.

## Módulos backend

`auth`, `users`, `customers`, `products`, `employees`, `sales`, `inventory`, `analytics`, `statistics`, `probability`, `insights`, `reports`, `audit`.

Cada módulo puede tener `router.py`, `schemas.py`, `service.py`, `models.py` y `repository.py` según complejidad. Los routers se versionan bajo `/api/v1`.

## Módulos frontend

`auth`, `dashboard`, `customers`, `products`, `sales`, `inventory`, `analytics`, `probability`, `insights`, `reports`, con `app` para arranque/rutas, `components` para piezas compartidas, `services` para cliente HTTP, `types` y `utils`.

## Contrato de API inicial

- `POST /api/v1/auth/login`
- `GET|POST /api/v1/customers`
- `GET|POST /api/v1/products`
- `GET|POST /api/v1/sales`, `GET /api/v1/sales/{id}`, `POST /api/v1/sales/{id}/void`
- `GET /api/v1/inventory`, `GET /api/v1/inventory/movements`
- `GET /api/v1/analytics/summary`, `GET /api/v1/analytics/sales-series`
- `POST /api/v1/statistics/mean`, `/median`, `/compare`
- `POST /api/v1/probability/bayes`
- `GET /api/v1/insights`, `GET /api/v1/reports`

Los endpoints de cálculo aislado sirven para enseñanza; el dashboard consultará servicios de Analytics que construyen métricas desde ventas persistidas.

## Errores y seguridad

Respuesta de error común: `detail` legible y `code` estable; validaciones de FastAPI conservan errores por campo. Contraseñas con hash robusto; secretos en variables de entorno; CORS por lista explícita; permisos por rol en backend; operaciones sensibles en auditoría. No se guardan secretos en el repositorio.

## Esquema de alto nivel

`companies` agrupa `users`, `customers`, `products`, `employees` y datos operativos; `sales` tiene `sale_details` y `payments`; `inventory` se representa por existencias y `inventory_movements`; los análisis vinculan dataset/filtros con `dataset_variables`, `observations`, `statistical_analyses`, `statistical_results`, `bayes_analyses` e `insights`; `audit_logs` registra acciones críticas. Las relaciones y restricciones exactas se especifican en Fase 04.

## Estructura del repositorio

```text
salesia-enterprise/
  backend/
    app/{api/routes,core,db,schemas,services}/
    alembic/
    pyproject.toml
  frontend/
    src/ (App y componentes por dominio)
    src/{services,hooks}/
    package.json
  docs/
  docker-compose.yml
  .env.example
  README.md
```

## Evolución y despliegue

Desarrollo local con servicios aislados y configuración por entorno. La aplicación se despliega como frontend estático, API FastAPI y PostgreSQL administrado o contenedorizado. Producción requiere HTTPS, copias de seguridad, migraciones controladas, logs sin secretos y estrategia de recuperación; proveedor y objetivos de disponibilidad quedan por definir.

## Riesgos técnicos a resolver en fases siguientes

- Precisar permisos y aislamiento de `companies` antes de multiempresa real.
- Definir concurrencia de stock para ventas simultáneas (bloqueo/actualización atómica).
- Evitar que cambios de catálogo alteren el historial de ventas.
- Asegurar que filtros del dashboard y reportes compartan semántica.
- Evitar guardar datasets duplicados innecesarios: derivar de transacciones o materializar solo cuando los requisitos de rendimiento lo justifiquen.


## Arquitectura aplicada al cierre de fases 1-14

- React organiza vistas por dominio con componentes reutilizables, hooks de datos locales y hook compartido de descarga; la navegación por hash conserva recarga e historial.
- FastAPI recibe esquemas Pydantic y resuelve permisos en dependencias. Los routers contienen consultas del dominio y coordinación transaccional; servicios compartidos encapsulan reglas comerciales, auditoría, límites de acceso y generación PDF. No se afirma una capa de repositorios independiente.
- PostgreSQL usa once migraciones, claves compuestas por empresa, 27 tablas de aplicación y RLS. Acceso desde la API; el navegador no recibe credenciales de base de datos.
- Ventas y pedidos bloquean filas de inventario antes de confirmar. Las pruebas reales de concurrencia comprueban una sola deducción/pago.
- Los errores de red mantienen formularios; solamente lecturas GET se reintentan una vez ante error transitorio. Las escrituras nunca se repiten automáticamente.
- Los endpoints públicos /health y /ready separan proceso disponible de conexión/esquema disponible. Los destinos de producción se configuran en fase 15.
- Contrato REST verificable: /openapi.json y /docs. Todos los módulos usan /api/v1.
