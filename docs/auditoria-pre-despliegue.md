# Auditoría previa al despliegue

Fecha: 3 de octubre de 2026. Dictamen: NO LISTO para declarar cumplimiento completo de las 16 fases.

## Evidencia ejecutada

- Backend: 83 pruebas aprobadas. Aviso de obsolescencia Starlette/httpx pendiente.
- Frontend: 8 pruebas aprobadas y compilación TypeScript/Vite correcta.
- Integración PostgreSQL/Supabase: 27 solicitudes HTTP mediante TestClient, autenticación JWT real y sesiones SQLAlchemy con savepoints dentro de una transacción externa.
- Consultas: clientes, productos, categorías, empleados, inventario y movimientos, pedidos, ventas, filtros/resumen/series/historial de Analytics, Insights, reportes y filtros, auditoría y acciones.
- Flujo: categoría → cliente → producto → entrada de 10 unidades → venta de 2 a S/10 → stock 8 → recibo → reporte filtrado y CSV → anulación → stock 10 → reporte archivado sin alteración.
- Se revirtió la transacción exterior. No quedaron filas de prueba; las secuencias PostgreSQL pueden avanzar pese al rollback.
- Script reproducible: backend/tests/integration_audit.py. Ejecución desde backend con runpy; es opt-in y no forma parte de pytest por defecto.

Estas comprobaciones no demuestran commits durables entre conexiones independientes, concurrencia, funcionamiento del navegador ni aceptación visual de PDF. La conexión y el login reales del usuario ya funcionaron previamente.

## Matriz de fases

| Fase | Evidencia y pendientes |
|---|---|
| 01 Requisitos | Documento base disponible. Faltan cerrar reglas de impuestos, descuentos y sucursales solicitadas por el plan. |
| 02 Arquitectura | Separación React/FastAPI/PostgreSQL implementada. Documentar arquitectura final local + Supabase y destino Vercel/Render. |
| 03 Diseño | Diseño corporativo aplicado. Falta inspección de todas las pantallas, estados y tamaños, teclado y contraste. |
| 04 Datos | Ocho migraciones aplicadas previamente, 25 tablas y RLS habilitado. Ensayo de actualización y restauración pendiente. |
| 05 API | Pruebas unitarias y muestra integrada aprobadas. Cobertura incompleta de todos los endpoints. |
| 06 Frontend | Build y ocho pruebas de cálculos aprobadas. Navegación basada en estado, sin rutas persistentes/atrás-adelante; aceptación de formularios pendiente. |
| 07 Catálogos | Altas comprobadas en flujo real y edición cubierta parcialmente con dobles. Falta ficha/historial individual de cliente exigido por el PDF. |
| 08 Operación | Venta, pago, inventario, detalle y anulación comprobados con rollback. Pedidos/conversión concurrente y reglas de impuestos/descuentos desde UI pendientes. |
| 09 Estadística | Pruebas de motor aprobadas. Revisar clasificación de variables y cobertura completa de persistencia de análisis. |
| 10 Dashboard | Consultas principales responden. Faltan sucursales, distribuciones/frecuencias y vistas agregadas por producto/vendedor; filtrar ventas completas no equivale a esas vistas. |
| 11 Insights | Consulta y pruebas de reglas disponibles. Generación/concurrencia real y vínculo explícito a dataset/análisis requeridos por el PDF pendientes. |
| 12 Reportes | Copia, filtrado y CSV comprobados. Reportes específicos de productos/clientes/vendedores no equivalen a una lista de ventas filtrada. PDF multipágina y detalle propio de cada reporte pendientes. |
| 13 Seguridad | Login real previo; permisos con dobles y autenticación JWT en integración. Revisar roles cruzados, empresas cruzadas, recuperación, revocación y límites reales. |
| 14 Calidad | Resultados anteriores aprobados; falta suite integrada ampliada, navegador, concurrencia y aceptación. |
| 15 Despliegue | Supabase conectado. Vercel/Render todavía no desplegados ni configurados completamente. HTTPS/CORS y arranque deben verificarse en destino. |
| 16 Entrega | Documentación inicial. Faltan manual final actualizado, diagrama, diccionario consolidado, capturas y evidencias completas. |

## Orden de cierre

1. Completar requisitos funcionales de fases 07, 08, 10, 11 y 12.
2. Ampliar pruebas de seguridad e integración, con transacciones y concurrencia en un entorno aislado.
3. Revisar UI y exportaciones en navegador; corregir resultados.
4. Consolidar manuales y preparar configuración Vercel/Render.
5. Desplegar y comprobar el sistema en destino antes de entregar.

No interpretar una compilación o una suite parcial aprobada como garantía de ausencia de errores.


## Avance operativo — 3 de octubre de 2026

- Diez migraciones aplicadas; 27 tablas de aplicación, incluida sucursales y existencias por sucursal.
- Inventario general independiente del inventario por sede; ventas, anulaciones y conversión de pedidos conservan la sede y actualizan su stock.
- Ficha/historial individual de clientes implementado y comprobado con PostgreSQL dentro de transacción revertida.
- Reportes agrupados por producto, cliente y vendedor implementados; creación, importes y descarga CSV comprobados en integración. La inspección visual de PDF sigue pendiente.
- Sucursales: mapa departamental del Perú, ficha, indicadores de existencias, ventas por moneda y personal comercial; asignación de vendedor desde directorio.
- Frontend compila; 83 pruebas backend y 8 frontend aprobadas. Esto no sustituye pruebas de concurrencia ni aceptación visual.
- Se mantienen pendientes los demás puntos de la matriz; no se declara el proyecto listo para producción. Documentación final de fase 16 permanece al último, según indicación del usuario.


### Dashboard y aislamiento — avance adicional

- Dashboard: agregados por producto y vendedor (hasta 20 resultados), distribución de tickets en cinco intervalos y porcentajes por moneda; respeta los filtros y restringe vendedores a sus propias ventas.
- Laboratorio descriptivo: límites de fecha alineados con America/Lima.
- Integración PostgreSQL: importes agregados, frecuencias, intervalo de fechas inválido, acceso entre empresas a fichas y agregados, restricción de ventas para vendedor y prohibición de crear reportes con ese rol comprobados.
- La primera ejecución devolvió 503 al crear un vendedor; la repetición completa pasó. No se determinó la causa de ese error transitorio. Las filas temporales se revirtieron en ambas ejecuciones.
- Compilación frontend, 83 pruebas backend y 8 frontend aprobadas. Pendientes: vínculo de insights a análisis/dataset, impuestos/descuentos en UI, pruebas concurrentes y aceptación visual/PDF, además del despliegue y documentación final.


### Descuentos e impuestos en ventas

- Formulario de venta: porcentajes por producto, validación 0–100 con dos decimales, subtotal/descuentos/impuestos/total antes de confirmar. No se aplica una tasa por defecto. El precio del catálogo es base y el impuesto se añade después del descuento.
- Cálculo en céntimos con BigInt, mismo redondeo half-up y orden del backend. Pedidos conservan su contrato de cantidades sin esos campos adicionales.
- Build aprobado; 10 pruebas frontend y 83 backend aprobadas.
- Integración real: venta de 20.00, descuento 2.00, impuesto 3.24, pago 21.24 y anulación aprobados. La suite completa posterior se interrumpió con 503 en consulta de sucursal durante aislamiento de empresa; rollback final completado. No declarar esta ejecución completa aprobada. Investigar los errores 503 intermitentes antes del despliegue.
