# SalesIA Enterprise — Fase 01: alcance y requisitos

> Actualización 4/10/2026: casos, excepciones y reglas vigentes en `casos-de-uso.md`. Hay 27 tablas de aplicación, once migraciones y aislamiento por empresa verificado. Los supuestos siguientes conservan la planificación inicial.

**Versión:** 1.1 · **Estado:** base de trabajo · **Meta:** entregar el sistema completo por fases verificables.

## Propósito

SalesIA Enterprise gestionará las operaciones comerciales y convertirá sus datos en estadísticas, probabilidades, visualizaciones, reportes e insights explicables. La analítica usará datos operativos reales y conservará el historial de cada análisis.

## Usuarios y responsabilidades

- **Administrador:** usuarios, roles, parámetros y configuración.
- **Gerente:** dashboard, Analytics, reportes e indicadores comerciales.
- **Vendedor:** clientes, pedidos y ventas autorizadas.
- **Analista:** datasets, análisis estadísticos, probabilidades, Bayes e insights.
- **Almacén:** existencias y movimientos de inventario.

## Alcance final (16 fases)

1. Requisitos, reglas de negocio, casos de uso y criterios de aceptación.
2. Arquitectura, módulos, estructura, contratos API y decisiones técnicas.
3. UX/UI, navegación, componentes, diseño y estados de interfaz.
4. PostgreSQL: modelo ER, restricciones, índices, migraciones y datos iniciales.
5. API FastAPI, autenticación, autorización, validaciones, servicios y documentación.
6. Aplicación React/TypeScript, rutas, formularios y consumo de API.
7. Clientes, productos, categorías, vendedores y búsquedas.
8. Pedidos, ventas, pagos, inventario y trazabilidad.
9. Variables estadísticas, media, mediana, variables aleatorias, probabilidad y Bayes.
10. Dashboard Analytics con filtros, KPIs, comparaciones, distribuciones y evolución temporal.
11. Insights determinísticos explicables con evidencia y origen trazable.
12. Reportes comerciales y estadísticos, exportación e historial.
13. Roles, permisos, sesiones, auditoría y secretos.
14. Calidad: pruebas unitarias, integración, API, UI, aceptación y casos límite.
15. Despliegue, configuración de entornos, HTTPS y monitoreo.
16. Manuales, documentación API, diccionario de datos y mantenimiento.

## Flujo operativo principal

Cliente → pedido → venta con detalle → pago → movimiento de inventario → persistencia transaccional → dataset derivado → análisis → gráficos e insights → dashboard y reportes.

## Requisitos funcionales agrupados

- **Acceso:** autenticación, usuarios, roles y permisos.
- **Catálogos:** clientes, productos, categorías, vendedores.
- **Operación:** pedidos, ventas, detalles, pagos, stock y movimientos.
- **Analítica:** datasets derivados, variables, media, mediana, comparación, variables aleatorias, probabilidad y Teorema de Bayes.
- **Consumo:** dashboard, gráficos, insights explicables, reportes e historial de análisis.
- **Gobierno:** auditoría de acciones críticas.

## Requisitos no funcionales

**Requisito obligatorio de datos, confirmado por el usuario el 1 de octubre de 2026:** la base de datos debe contener al menos 20 tablas de negocio, con relaciones y una responsabilidad funcional justificada. Las dos migraciones actuales definen 24 (22 iniciales y 2 de pedidos); las tablas técnicas de migraciones no se cuentan para este mínimo.

Arquitectura modular; separación de interfaz, negocio y persistencia; integridad referencial; autenticación segura y autorización en backend; validación en cliente y servidor; API documentada; manejo centralizado de errores; secretos por entorno; trazabilidad de operaciones críticas; interfaz responsive; y rendimiento apropiado para consultas analíticas.

## Reglas de negocio base (supuestos explícitos)

1. Las operaciones monetarias usan decimales y una moneda por instalación al inicio.
2. Una venta confirmada guarda una copia histórica del precio, descripción y cantidad vendida.
3. Confirmar una venta, sus detalles, pagos iniciales y movimientos de stock es una transacción atómica.
4. El stock no puede ser negativo salvo que una configuración posterior autorice preventa.
5. La anulación exige motivo y genera movimientos compensatorios trazables; no borra historia.
6. Los análisis excluyen ventas anuladas por defecto e indican filtros, periodo, hora de cálculo y conjunto de datos utilizado.
7. Bayes requiere eventos explícitos y probabilidades válidas (incluida P(B)>0); el sistema no inventará probabilidades de entrada.
8. Los insights de la primera versión son reglas determinísticas, muestran evidencia y no se presentan como predicciones causales.
9. La entidad `companies` del plan se conserva en el diseño, pero el aislamiento multiempresa se confirma antes de tratarlo como requisito de producción. Mientras tanto se documentará el modo de empresa única.

## Criterios globales de aceptación

Un usuario autorizado completa una venta; inventario, pago y persistencia quedan consistentes; las anulaciones son trazables; Analytics reproduce cálculos sobre datos filtrados; Bayes devuelve resultados reproducibles para entradas explícitas; gráficos, insights e informes exponen los datos que los originan; análisis y acciones críticas conservan historial; y el producto incluye instrucciones de instalación y uso.

## Entrega por etapas

La primera versión demostrable priorizará acceso, catálogos, venta e inventario. Después se incorporarán progresivamente el motor estadístico, Bayes, dashboard, insights, reportes, endurecimiento y despliegue. Esto ordena la entrega y no elimina funciones del alcance final.

## Decisiones que quedan parametrizables o documentadas

Moneda; impuestos y descuentos; pagos parciales; sucursales; retención de datos; y alcance real multiempresa. Se implementarán con defaults claramente indicados, evitando bloquear arquitectura y desarrollo mientras no exista una pauta académica más específica.
