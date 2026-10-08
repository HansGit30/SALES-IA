# Fase 14 — Plan y resultados de aceptación

Revisión: 4 de octubre de 2026. Entorno: Windows, React/Vite local, FastAPI y PostgreSQL en Supabase. Alcance: fases 1–14; la aceptación de producción pertenece a la fase 15.

## Resultado ejecutado

| Nivel | Resultado |
|---|---|
| Backend | **123 pruebas aprobadas**: cálculos, validaciones, permisos, reportes, errores y contratos |
| Frontend | **15 pruebas aprobadas**: dinero, periodos, series y reintento limitado de lecturas |
| Compilación | TypeScript y Vite de producción: aprobada |
| Integración PostgreSQL | `tests/integration_audit.py`: completada, rollback final confirmado |
| Concurrencia real | Última unidad vendida una sola vez; pedido convertido una sola vez; limpieza final |
| Volumen | 10 000 ventas y detalles; rollback final |
| Navegador | Cinco roles; formularios comerciales, análisis, dashboard, mapa y reportes revisados |
| PDF | Cinco tipos y recibo; inspección de las nueve páginas del reporte descargado de 120 ventas |

El aviso de obsolescencia Starlette/httpx no produjo fallos. Estos resultados describen los casos ejecutados; no garantizan ausencia de cualquier defecto.

## Casos de aceptación

| Casos | Comprobación | Evidencia |
|---|---|---|
| CU01–02 | Autenticación, roles, usuarios, revocación y protección del administrador | Suite de permisos, integración y cinco inicios de sesión UI |
| CU03–04 | Altas/edición/baja lógica, búsqueda, historia y aislamiento | Integración; alta de categoría y producto en navegador |
| CU05–08 | Ajustes, venta, pagos, stock, anulación, pedido y conversión | Integración y concurrencia entre conexiones independientes; venta UI con descuento/impuesto |
| CU09–10 | Descriptivo, comparación, Bayes, variable aleatoria y persistencia | Suite e integración; distribución UI guardada: media 1.1, varianza 0.49 |
| CU11 | KPIs, filtros, días sin venta, moneda, participación y frecuencia | Pruebas y dashboard UI: 120 ventas, S/150 000, ticket S/1 250 |
| CU12 | Reglas explicables y vínculo a análisis/dataset | Suite e integración de generación/trazabilidad; pantalla revisada |
| CU13 | Copias archivadas, cinco tipos, CSV/PDF, moneda y límites | Integración; descarga real salesia-reporte-53.pdf, 9 páginas |
| CU14 | Sucursal, ubicación, marcador, ficha e indicadores | Integración y alta UI de sede sintética en Lima |
| CU15 | Auditoría y acceso restringido | Integración: altas, análisis, reglas comerciales y usuarios |

## Límites y regresiones

- Validaciones: vacíos, SKU/nombres, fechas, probabilidades incompatibles y magnitudes fuera del almacenamiento.
- Stock insuficiente, anulación/confirmación repetidas, pagos y reglas incompatibles: rechazo sin operaciones parciales.
- Regresión SQL de observaciones aleatorias: guardado y consulta aprobados.
- Roles: 31 casos de denegación directa de API, complementados por suites existentes y acceso UI de admin, manager, seller, analyst y warehouse.
- Empresas cruzadas: referencias de cliente, sucursal y trazabilidad inaccesibles; vendedor limitado a sus operaciones.
- Responsive: escritorio, tablet 768 px y móvil 375 px; corregido desbordamiento del resultado estadístico. Navegación, formularios, carga y estados vacíos revisados en los flujos indicados.
- PDF: cabeceras repetidas y márgenes conservados en 9 páginas. Se guardó en Descargas; el evento de automatización del navegador agotó el tiempo de espera, aunque el archivo real se verificó y renderizó.

## Rendimiento y disponibilidad

Tres ejecuciones con 10 000 ventas: resumen 0.715–0.760 s, desglose 1.129–1.287 s, serie 0.559–0.568 s. Volumen de un usuario, no carga de producción.

Se observaron interrupciones transitorias de conexión a Supabase en la sesión prolongada. La API responde 503 con referencia; las lecturas reintentan una vez y las escrituras nunca se repiten automáticamente. El formulario conserva sus datos. Integración y descarga finales terminaron correctamente. Disponibilidad del proveedor y monitoreo en destino se revisarán en fase 15.

## Reproducción

Desde backend, con variables locales configuradas:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m tests.integration_audit
.\.venv\Scripts\python.exe -m tests.concurrency_audit
.\.venv\Scripts\python.exe -m tests.performance_audit
```

Desde frontend: `npm test` y `npm run build`.

Integración/volumen revierten datos. Concurrencia/UI limpian solo la empresa sintética identificada. `tests/ui_fixture.py` sirve aceptación en 127.0.0.1:8001; crear `tests/.ui-stop` termina limpiamente. Nunca es entrada de producción.

## Evidencia visual

- `producto-qa-verificado.jpg`: producto creado.
- `sucursal-qa-verificada.jpg`: sede y mapa.
- `pdf-descarga-contacto.jpg`: nueve páginas descargadas.
- `pdf-products.png`, `pdf-customers.png`, `pdf-sellers.png`, `pdf-statistical.png`, `pdf-recibo.png`: plantillas revisadas.

Fase 15: HTTPS, CORS, secretos, arranque, logs y operación en destino. Fase 16: documentación final a cargo del usuario.
