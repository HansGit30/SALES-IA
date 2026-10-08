# SalesIA Enterprise — Fase 04: base de datos

Modelo ER del esquema real: `modelo-er.md` (27 tablas, 49 claves foráneas). Migración vigente: `0011_pricing_rules`. `database/schema.sql` es la base inicial; las migraciones Alembic son la evolución normativa y el método de instalación.

El esquema inicial ejecutable está en `database/schema.sql`.

## Mínimo obligatorio y tablas actuales

El usuario requiere un mínimo de **20 tablas**. El esquema inicial y la extensión de pedidos definen **24 tablas de negocio**, sin contar la tabla técnica de Alembic. La cantidad está comprobada en database/schema.sql (22) y database/orders.sql (2); su creación física queda pendiente de aplicar la migración en PostgreSQL.

| Tabla | Responsabilidad |
|---|---|
| companies | Empresas y contexto de aislamiento |
| roles | Perfiles de autorización |
| users | Cuentas de acceso |
| customers | Cartera de clientes |
| categories | Clasificación del catálogo |
| products | Productos y precios vigentes |
| employees | Perfiles del equipo comercial |
| sales | Cabecera y estado de ventas |
| sale_details | Productos, cantidades e importes históricos de cada venta |
| payments | Pagos asociados a ventas |
| inventory | Existencias actuales |
| inventory_movements | Entradas, salidas y ajustes trazables |
| datasets | Conjuntos de datos analíticos |
| dataset_variables | Variables de cada conjunto de datos |
| observations | Observaciones de los conjuntos |
| statistical_analyses | Ejecuciones y parámetros de análisis |
| statistical_results | Resultados estadísticos |
| bayes_analyses | Análisis del teorema de Bayes |
| random_variables | Variables aleatorias y distribuciones |
| insights | Hallazgos y evidencia |
| reports | Historial y parámetros de informes |
| audit_logs | Auditoría de acciones |
| orders | Pedidos, estado y vínculo con la venta generada |
| order_details | Artículos, cantidades y precios históricos del pedido |

Este inventario describe el modelo; la cobertura funcional y las validaciones de cada módulo se siguen en el roadmap.

La migración `0002_orders` incorpora las dos tablas de pedidos y sus claves compuestas por empresa. El SQL se genera correctamente en modo offline; falta ejecutarlo contra PostgreSQL real.

## Decisiones representadas

- Importes y cantidades usan `NUMERIC`, no `float`.
- Entidades operativas llevan `company_id`; claves foráneas compuestas evitan asociar registros de empresas distintas.
- Ventas guardan precio, SKU y nombre históricos en el detalle.
- Anular conserva la venta y queda ligado a movimientos compensatorios.
- Inventario mantiene saldo actual y libro de movimientos.
- Análisis guarda filtros, parámetros y resultados reproducibles en JSONB más tablas de métricas normalizadas.
- Índices priorizan ventas por periodo, estado, cliente y vendedor.

## Nota de migración

Este archivo define el esquema inicial para una base vacía y está incorporado a la migración inicial versionada de Alembic. Falta ejecutar y validar esa migración en PostgreSQL; no se debe aplicar manualmente a una base con datos existentes sin revisar el impacto.

## Pendiente de cierre

El MVP usa una empresa semilla, pero el modelo prepara `company_id` para aislamiento. Aún hay que añadir políticas de fila o comprobar company_id en cada consulta/servicio; las FK compuestas son una defensa de integridad y no sustituyen autorización.
