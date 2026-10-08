# SalesIA Enterprise — estado de entrega

El objetivo es entregar el sistema completo definido en las 16 fases de `Plan_Desarrollo_SalesIA_Enterprise.pdf`. La entrega se construye secuencialmente; las funciones del MVP son hitos intermedios, no el límite del producto.

## Auditoría actual

La revisión del 3 de octubre de 2026 está en `auditoria-pre-despliegue.md` y prevalece sobre los estados históricos de esta tabla. Se aprobaron 83 pruebas backend, 8 frontend y una muestra integrada contra Supabase con rollback. Se identificaron requisitos funcionales pendientes; no está listo para declarar cumplimiento completo.

## Estado por fase

| Fase | Alcance | Estado y trabajo pendiente |
|---|---|---|
| 01 | Requisitos y alcance | Documentado para los dominios del proyecto, usuarios, reglas iniciales y límites asumidos. Validar reglas del negocio no definidas en el plan. |
| 02 | Arquitectura y contratos | Arquitectura React/TypeScript, FastAPI y PostgreSQL documentada; contratos API base disponibles. |
| 03 | UX/UI | Sistema visual compartido y vistas responsive principales implementadas. Revisar cada estado y navegación frente a wireframes y requisitos. |
| 04 | Base de datos | Esquema relacional y migración Alembic inicial escritos. Falta ejecutar en PostgreSQL limpio, comprobar restricciones y ensayar actualización. |
| 05 | Backend/API | Rutas de autenticación, usuarios, clientes, empleados, categorías, productos, ventas, inventario, estadísticas, probabilidad, analytics, insights, reportes y auditoría implementadas. Falta verificación integrada con PostgreSQL. |
| 06 | Frontend | Login, shell por rol, dashboard y módulos funcionales de ventas, clientes, productos, categorías, vendedores, inventario, analytics, insights, reportes y configuración implementados. |
| 07 | Catálogos | Clientes y productos tienen alta, edición, desactivación/reactivación, búsqueda y paginación de 25 filas. Categorías y vendedores incluyen altas, edición, estados, búsqueda, filtro de estado y paginación local de 25 filas. Falta validación integrada con PostgreSQL. |
| 08 | Ventas e inventario | Pedidos con detalle, cancelación y conversión atómica a venta; pago, inventario, historial de movimientos y redondeo exacto de formulario. Recibo imprimible y anulación con confirmación de devolución completa implementados. Pendientes validación integrada, concurrencia e inspección de impresión. |
| 09 | Estadística y probabilidad | Estadística descriptiva, comparaciones, análisis persistidos, variables aleatorias discretas y Bayes. Falta contraste de resultados y presentación didáctica en UI. |
| 10 | Analytics | Indicadores, series por periodo e historial; selector de rangos en dashboard. Completar filtros y definición de métricas según datos reales. |
| 11 | Insights | Reglas de descenso semanal y stock actual; semanas completas, clave única por periodo, reevaluación/resolución y evidencia legible. Falta validar la migración y concurrencia en PostgreSQL. |
| 12 | Reportes | Reportes comerciales y estadísticos con periodos de Lima, copia persistida, historial descargable, importes por moneda, CSV protegido, filtros por cliente/producto/vendedor y plantilla compartida para guardar PDF desde impresión. Falta validar migración, persistencia real e impresión multipágina. |
| 13 | Seguridad y auditoría | JWT, hash Argon2, autorización en servidor y aislamiento por empresa; auditoría de acciones críticas. Cambio de contraseña y revocación global de sesiones con auditoría implementados; Límites de autenticación persistidos y auditoría de accesos implementados. Recuperación asistida por administrador y cambio obligatorio de clave temporal implementados. Migraciones 0005–0007, recuperación autónoma y revisión integrada pendientes. El esquema completo incluye 25 tablas. |
| 14 | Pruebas y calidad | 83 pruebas backend y 8 frontend ejecutadas correctamente; CI configurada. Falta completar integración con PostgreSQL, accesibilidad y aceptación. |
| 15 | Despliegue | Compose de desarrollo y versión compilada con Nginx, proxy, respaldo PowerShell y actualización documentados. Pendiente levantar y validar stack; Docker no está disponible en el entorno actual. |
| 16 | Cierre y manuales | README, manual inicial, arquitectura y sistema visual en progreso. Falta guía operativa completa, capturas y cierre de limitaciones. |

## Siguiente secuencia de trabajo

1. Validar contra PostgreSQL la persistencia y auditoría de los cuatro catálogos; los flujos principales de interfaz y API ya están implementados.
2. Completar flujos restantes de inventario, Insights y reportes con estados claros y acciones reales.
3. Consolidar métricas, análisis estadístico y parámetros de negocio aún no especificados.
4. Revisar autorización y trazabilidad, después validar el esquema y los flujos con PostgreSQL.
5. Ejecutar la calidad definida en la fase 14, validar el despliegue y cerrar manuales.

## Límites que siguen abiertos

- El plan no define impuestos, descuentos, monedas múltiples, sucursales, umbrales de stock ni políticas de retención. Se usan PEN, reglas iniciales configurables o valores explícitos donde corresponde; se deben confirmar las reglas antes de producción.
- La migración inicial y Docker Compose están escritos, pero falta una ejecución de extremo a extremo en un entorno con PostgreSQL y Docker.
- El estado de compilación del frontend y la sintaxis Python no demuestran integración funcional contra la base de datos.
- Los datos de panel son reales cuando provienen de API; la ilustración de acceso está rotulada como ejemplo.

## Criterio de cierre

La entrega final debe cubrir las 16 fases, compilar y arrancar desde instrucciones limpias, aplicar migraciones, demostrar los flujos por rol y compañía, validar informes/estadística con datos conocidos y acompañarse de manual técnico y operativo. El sistema visual común se mantiene en todas las fases, sin sustituir ni aplazar funcionalidades del plan.
