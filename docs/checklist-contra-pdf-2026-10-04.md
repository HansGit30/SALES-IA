# SalesIA Enterprise — Checklist contra el PDF original

> **Auditoría inicial conservada como evidencia histórica.** Los fallos y ausencias de implementación indicados aquí se corrigieron posteriormente en esta sesión. Consultar `cierre-pendientes-2026-10-04.md` para el estado actualizado, pruebas y pendientes de aceptación/despliegue.

**Revisión:** 4 de octubre de 2026 (Lima).  
**Fuente:** Plan_Desarrollo_SalesIA_Enterprise.pdf, versión 1.0, 14 páginas.  
**Alcance:** revisión de requisitos, código, esquema real de Supabase, pruebas y entregables. La fase 16 corresponde al usuario. Este checklist es una auditoría solicitada; no sustituye sus manuales.

## Cómo leer los estados

- `[x]` Implementado y localizado en código; se indica expresamente cuando también se verificó con PostgreSQL.
- `[ ] PARCIAL` Existe una parte, pero el requisito no puede darse por cerrado.
- `[ ] PENDIENTE` No implementado, no entregado o sin verificación suficiente.
- `[ ] FALLO` Comportamiento incorrecto reproducido.

Un test aprobado no certifica todas las pantallas ni todo el producto. No se calcula un porcentaje de finalización porque ocultaría diferencias entre implementación, aceptación y despliegue.

## Hallazgos que impiden declarar el proyecto terminado

1. **Fallo real en variables aleatorias (fase 09, RF-15).** El servicio escribe simultáneamente `numeric_value` y `text_value` en `observations`, pero PostgreSQL exige exactamente uno no nulo. Reproducido con distribución válida: valores 0 y 1, probabilidades 0.5 y 0.5; devuelve `CheckViolation`, SQLSTATE `23514`. La transacción se revierte. El manejador HTTP lo transforma en 409. Debe corregirse el almacenamiento de la probabilidad y añadirse una prueba real de regresión. Evidencia: `backend/app/api/routes/probability.py`, `database/schema.sql` y restricción comprobada en Supabase.
2. **Gestión de usuarios incompleta (RF-02).** Se puede crear, listar y restablecer contraseña; no hay actualización de perfil/rol ni activación/desactivación de cuentas desde API/UI. Desactivar un perfil de vendedor no equivale a desactivar su cuenta. Evidencia: `users.py`, `SettingsPage.tsx`.
3. **Reglas configuradas de impuestos/descuentos (fase 08).** Existen porcentajes manuales por línea y cálculo correcto; falta configuración persistente de reglas/tasas por empresa o política aplicable. Los pedidos no incluyen esos porcentajes. El PDF pide cálculo según reglas configuradas; no basta con afirmar que el formulario tiene campos.
4. **Variables estadísticas y datasets (RF-10, RF-14).** Hay generación y clasificación interna de monto/unidades; falta una vista que permita identificar claramente tipo, naturaleza y observaciones de las variables operativas. No existe gestión general de datasets en UI.
5. **Paneles Analytics de la página 11 incompletos.** Falta indicador de clientes en resumen, panel de compras/frecuencia/ticket por cliente y participación porcentual por producto. El dashboard de vendedores muestra ventas e ingresos; el promedio está en reportes, no en ese panel. El historial de cliente no sustituye todos estos indicadores.
6. **Trazabilidad parcial.** Ventas, pedidos, ajustes, modificaciones de catálogos, seguridad y algunos análisis generan auditoría. Las altas de clientes/productos/categorías/vendedores y el análisis de variable aleatoria no insertan su evento de auditoría. Debe acordarse el alcance de acciones críticas y cubrirlo.
7. **Pruebas UI, PDF y rendimiento sin cierre.** No hay evidencia suficiente de aceptación visual completa, formularios/navegación en todos los roles, tablet, impresión multipágina y pruebas de volumen.
8. **Producción pendiente.** Los archivos de Vercel/Render existen, pero no hay versión desplegada y verificada, HTTPS/CORS de destino ni monitoreo operativo comprobado.

## Checklist por las 16 fases

### Fase 01 — Análisis y levantamiento (PDF pp. 5–6, 13)

- [x] Problema, alcance y cinco roles descritos en `docs/fase-01-requisitos-y-alcance.md`.
- [x] Flujo cliente → pedido → venta → pago → inventario definido.
- [x] Datos para Analytics identificados y usados por consultas/datasets.
- [ ] PARCIAL: reglas de negocio; faltan reglas configurables de impuestos/descuentos y precisar límites de gestión de usuarios/datasets.
- [ ] PARCIAL: casos de uso; hay flujo y objetivos, no un catálogo detallado con escenarios, excepciones y resultado esperado.
- [ ] PARCIAL: criterios de aceptación definidos en general; falta evidencia completa de cumplimiento individual.
- **Estado:** parcial. Los documentos iniciales contienen afirmaciones desactualizadas.

### Fase 02 — Arquitectura técnica (PDF pp. 6, 9–10)

- [x] React + TypeScript / FastAPI / PostgreSQL separados.
- [x] Módulos por dominio, schemas Pydantic, REST y OpenAPI.
- [x] Autenticación, autorización y manejadores de errores.
- [x] Alembic, configuración de entorno y archivos de despliegue.
- [ ] PARCIAL: separación interna; varios routers mezclan HTTP, reglas de negocio y SQL, en vez de la separación descrita en la arquitectura.
- [ ] PARCIAL: estructura propuesta: frontend mayormente plano en `src`, sin carpetas `modules/hooks/layouts` como el ejemplo. No bloquea por sí solo, pues el PDF la llama propuesta; debe reflejarse honestamente en la arquitectura final.
- **Estado:** arquitectura operativa; alineación documental y separación interna parciales.

### Fase 03 — UX/UI empresarial (PDF pp. 5–6)

- [x] Sidebar, topbar, dashboard, tablas, formularios y componentes comunes.
- [x] Paleta corporativa azul/cyan, CSS compartido, hero y elementos visuales 3D en CSS.
- [x] Estados de carga, vacío, error y éxito presentes en diversos módulos.
- [x] Gráficos y panel de insights implementados.
- [ ] PENDIENTE: inspección de legibilidad, contraste, teclado, tablet y estados en todas las pantallas.
- [ ] PENDIENTE: wireframes como entregable independiente; hay mapa de navegación y pantallas implementadas, no se encontró el conjunto de wireframes.
- **Estado:** implementado, aceptación visual pendiente.

### Fase 04 — PostgreSQL (PDF pp. 6, 10, 13)

- [x] Tablas operativas y analíticas con relaciones.
- [x] Índices, restricciones, claves foráneas y cantidades/importes NUMERIC.
- [x] Diez migraciones; Supabase está en `0010_branch_operations`.
- [x] 27 tablas de aplicación, excluyendo `alembic_version`; supera el mínimo de 20 pedido por el usuario. Incluye una tabla de soporte (`auth_rate_limits`); aun excluyéndola quedan 26 tablas.
- [x] RLS habilitado en las 27 tablas. Acceso previsto mediante backend; esto no equivale a políticas para acceso directo desde el navegador.
- [x] Creación inicial de roles/administrador disponible.
- [ ] PARCIAL: modelo ER; hay SQL y descripción de relaciones, no se localizó un diagrama ER gráfico completo actualizado.
- [ ] FALLO: el código de variables aleatorias no respeta la restricción vigente de `observations`.
- **Estado:** esquema aplicado; incompatibilidad de un flujo y entregable ER pendientes.

### Fase 05 — Backend/API (PDF pp. 6, 12)

- [x] FastAPI, módulos, autenticación y autorización.
- [x] Ventas transaccionales con pagos y movimientos.
- [x] Servicios de estadística, probabilidad, reportes e insights.
- [x] OpenAPI/Swagger generado automáticamente.
- [ ] FALLO: persistencia de variable aleatoria con entrada válida.
- [ ] PARCIAL: cobertura integral de endpoints y códigos de error; restricciones distintas pueden convertirse en mensajes genéricos de conflicto.
- **Estado:** API operativa, cierre bloqueado por el fallo señalado.

### Fase 06 — Frontend React (PDF p. 6)

- [x] Layout y navegación por hash; recarga y atrás/adelante implementados.
- [x] Componentes reutilizables, cliente HTTP y formularios con validación.
- [x] Consumo de API con efectos/hooks React y estados de carga/error.
- [x] Build de TypeScript/Vite aprobado en esta revisión.
- [ ] PARCIAL: hooks de datos reutilizables; predominan efectos locales por pantalla.
- [ ] PENDIENTE: aceptación de formularios, rutas, filtros, teclado y estados en navegador con sesión real.
- **Estado:** implementado; verificación UI pendiente.

### Fase 07 — Clientes y productos (PDF p. 7)

- [x] Altas, consultas, edición y desactivación de clientes/productos/categorías.
- [x] Historial de cliente con ventas, importes y sucursal.
- [x] Búsqueda, filtros, paginación y relación producto-categoría.
- [x] Directorio de vendedores y asignación a sucursal.
- [ ] PARCIAL: el término CRUD se implementa con baja lógica, no borrado físico. Validar esa interpretación en aceptación; conservar historial es coherente con ventas.
- [ ] PENDIENTE: aceptación visual y de todas las operaciones de edición por rol.
- **Estado:** funcionalmente implementado, aceptación pendiente.

### Fase 08 — Ventas, pedidos e inventario (PDF p. 7)

- [x] Carrito y detalles con cantidades y precios históricos.
- [x] Subtotal, descuento, impuesto y total en backend y pantalla de venta.
- [ ] PARCIAL: reglas configuradas; porcentajes manuales por venta, sin parametrización empresarial persistente.
- [x] Registro de pago y conciliación con el total.
- [x] Actualización de inventario general y por sucursal.
- [x] Pedidos, conversión, historial y anulación compensatoria.
- [x] Auditoría de ventas, pedidos y ajustes.
- [x] Pruebas concurrentes para última unidad y confirmación simultánea de pedido disponibles.
- **Estado:** flujo central implementado; configuración de reglas pendiente.

### Fase 09 — Motor estadístico Semana 07 (PDF pp. 7, 11)

- [x] Media y mediana correctas en casos cubiertos por tests.
- [x] Análisis descriptivo de ventas persiste dataset, variable, observaciones y resultados; comprobado de nuevo con PostgreSQL.
- [x] Comparación media/mediana por API y valores presentados en UI.
- [ ] PARCIAL: identificación/clasificación visible de variables; clasificación cuantitativa interna, sin una vista completa de tipos/naturaleza.
- [x] Cálculo y validación de distribución discreta en código.
- [ ] FALLO: guardar esa distribución/variable aleatoria produce SQLSTATE 23514 con entradas válidas.
- [x] Probabilidades y Bayes con validación, fórmula y explicación; caso 0.2 × 0.6 / 0.3 = 0.4 comprobado con persistencia.
- [ ] PARCIAL: registrar cada análisis. Descriptivo y Bayes persisten; variable aleatoria falla; endpoints didácticos `/statistics/mean`, `/median`, `/compare` no guardan historial.
- **Estado:** incompleto y con un fallo confirmado.

### Fase 10 — Dashboard Analytics (PDF pp. 7, 11)

- [x] Ventas, ingresos, transacciones, ticket promedio y mediana.
- [x] Serie temporal, comparación entre periodos y días sin ventas.
- [x] Ranking de productos y vendedores; hasta 20 resultados.
- [x] Distribución de importes, frecuencias y porcentajes por intervalo.
- [x] Filtros de periodo, sucursal, vendedor, categoría y producto.
- [ ] PENDIENTE: clientes en resumen ejecutivo (p. 11).
- [ ] PENDIENTE: panel de clientes con compras, frecuencia y ticket (p. 11).
- [ ] PENDIENTE: participación de cada producto en ingresos (p. 11).
- [ ] PARCIAL: promedio por vendedor en dashboard; existe en reportes agrupados.
- [ ] PARCIAL: panel de variables con tipo, distribución y estadísticas (p. 11).
- **Estado:** parcial; los puntos adicionales de la página 11 también forman parte del plan.

### Fase 11 — Insights empresariales (PDF p. 7)

- [x] Reglas determinísticas de caída semanal y stock bajo.
- [x] Explicación y evidencia numérica con fechas y umbrales.
- [x] Vínculo insight → análisis → dataset → observaciones para nuevas evaluaciones.
- [x] Consulta de evidencia/origen, historial, deduplicación y resolución.
- [x] Prueba integrada de stock bajo, reevaluación sin duplicados y resolución disponible.
- [ ] PENDIENTE: aceptación visual del detalle del análisis.
- **Límites explícitos:** stock bajo usa inventario general y guarda hasta 50 productos; insights históricos sin vínculo no se completan retroactivamente salvo nueva evaluación aplicable. El PDF no fija más reglas mínimas.
- **Estado:** funcionalidad principal implementada; aceptación visual pendiente.

### Fase 12 — Reportes (PDF p. 8)

- [x] Ventas y estadística descriptiva.
- [x] Productos, clientes y vendedores como reportes agrupados propios.
- [x] Filtros, historial y copia persistida de datos del reporte.
- [x] Exportación CSV.
- [x] Vista imprimible corporativa compartida con comprobantes de venta.
- [ ] PENDIENTE: inspección real de PDF multipágina, saltos, tablas extensas y recortes.
- **Alcance:** guardar PDF usa la impresión del navegador, no un generador PDF del backend; cumple como mecanismo imprimible si supera la validación visual.
- **Estado:** implementado; salida PDF no aceptada aún.

### Fase 13 — Seguridad y auditoría (PDF p. 8)

- [x] Roles y permisos en API, validación de entrada y autorización por empresa.
- [x] Contraseñas con hash, JWT, expiración y versión de sesión.
- [x] Cambio obligatorio de contraseña temporal, recuperación por administrador y revocación de sesiones.
- [x] Límite de intentos de acceso y secretos por entorno; `.env` ignorado.
- [x] Auditoría consultable de operaciones principales.
- [ ] PARCIAL: eventos ausentes en altas de catálogos/vendedores y variable aleatoria.
- [ ] PARCIAL: administración de cuentas; falta edición de rol/estado desde el sistema.
- [ ] PENDIENTE: matriz exhaustiva de permisos y pruebas en producción/HTTPS. Las pruebas de aislamiento cubren escenarios seleccionados.
- **Estado:** controles principales implementados, cobertura incompleta.

### Fase 14 — Pruebas y calidad (PDF pp. 8, 12–13)

- [x] 85 tests backend aprobados en esta revisión.
- [x] 10 tests frontend de cálculos/fechas aprobados; no son tests completos de formularios.
- [x] Build frontend aprobado.
- [x] Scripts de integración PostgreSQL y concurrencia disponibles y ejecutados previamente; resultados de repetición al final de este archivo.
- [x] Revisión adicional encontró un fallo no cubierto por la suite: persistencia de variable aleatoria.
- [ ] PENDIENTE: prueba de regresión que cubra y luego verifique la corrección de ese fallo.
- [ ] PENDIENTE: formularios, navegación, roles, tablet y PDF en navegador.
- [ ] PENDIENTE: aceptación completa por casos del PDF.
- [ ] PENDIENTE: rendimiento analítico con volumen representativo.
- **Estado:** parcial; 95 tests aprobados no equivalen a proyecto sin errores.

### Fase 15 — Despliegue (PDF pp. 8, 12–13)

- [x] Configuración frontend en `frontend/vercel.json` y backend en `render.yaml`.
- [x] Supabase conectado y migraciones aplicadas.
- [x] Variables de entorno, CORS configurable y endpoints `/health` y `/ready`.
- [x] Ajustes de pool/conexión y diagnóstico seguro para indisponibilidad.
- [ ] PENDIENTE: frontend publicado en Vercel y API en Render.
- [ ] PENDIENTE: URLs finales, variables reales de producción, CORS/HTTPS de destino.
- [ ] PENDIENTE: logs, monitoreo y aceptación de la versión desplegada.
- **Estado:** preparado parcialmente; no desplegado. La causa original de los 503 intermitentes de integración no quedó demostrada. Los procesos locales duplicados se corrigieron, pero eso no prueba la causa de errores dentro de TestClient.

### Fase 16 — Cierre y documentación (PDF p. 8)

**Responsable: usuario, por indicación expresa. No se marca completa.**

- [ ] Manual técnico.
- [ ] Manual de usuario.
- [ ] Diagrama final.
- [ ] Diccionario de datos.
- [ ] Documentación API final (OpenAPI existe como base).
- [ ] Evidencias consolidadas de pruebas.
- [ ] Plan de mantenimiento.

Los documentos actuales sirven de borrador; algunos indican 24/25 tablas y migraciones pendientes aunque Supabase ya tiene 27 tablas y diez migraciones. Deben actualizarse antes de entregarlos.

## Trazabilidad de los requisitos funcionales (PDF pp. 4–5)

| Código | Requisito | Estado |
|---|---|---|
| RF-01 | Autenticación y roles | Implementado; aceptación completa por rol pendiente |
| RF-02 | Gestión de usuarios | Parcial: alta/listado/reset; falta editar rol/estado |
| RF-03 | Clientes | Implementado con baja lógica e historial |
| RF-04 | Productos y categorías | Implementado con baja lógica |
| RF-05 | Vendedores | Implementado; asignación a sucursal incluida |
| RF-06 | Venta y detalle | Implementado y probado en integración |
| RF-07 | Pagos y métodos | Registro de pagos y cuatro métodos; no pasarela ni pagos parciales. El PDF no exige pasarela |
| RF-08 | Inventario y movimientos | Implementado general/por sucursal |
| RF-09 | Dashboard ejecutivo | Parcial respecto al panel de clientes de p. 11 |
| RF-10 | Datasets derivados | Generación automática; gestión/exploración general parcial |
| RF-11 | Media | Implementado y probado |
| RF-12 | Mediana | Implementado y probado |
| RF-13 | Comparación media/mediana | Implementado; endpoint didáctico no persiste |
| RF-14 | Variables estadísticas | Parcial: clasificación interna sin identificación completa en UI |
| RF-15 | Variables aleatorias | Fallo confirmado al persistir |
| RF-16 | Probabilidades | Cálculos presentes; distribución afectada por RF-15 |
| RF-17 | Bayes | Implementado; cálculo/persistencia comprobados |
| RF-18 | Gráficos | Series y distribución presentes; aceptación visual pendiente |
| RF-19 | Insights | Reglas, evidencia y origen implementados |
| RF-20 | Reportes | Cinco tipos y CSV; PDF pendiente de aceptación |
| RF-21 | Historial de análisis | Parcial por RF-15 y cálculos didácticos sin persistencia |
| RF-22 | Auditoría | Parcial: operaciones principales sí, altas indicadas no |

## Requisitos no funcionales (PDF p. 5)

| Código | Requisito | Veredicto |
|---|---|---|
| RNF-01 | Modularidad/mantenimiento | Parcial; módulos existen, routers y componentes concentran lógica |
| RNF-02 | Validación frontend/backend | Presente; fallo de persistencia demuestra cobertura incompleta |
| RNF-03 | Integridad referencial | Constraints y FK comprobadas; corregir escritura incompatible |
| RNF-04 | Autenticación/autorización segura | Implementada; falta aceptación exhaustiva y producción |
| RNF-05 | API documentada | OpenAPI disponible; manual final corresponde a fase 16 |
| RNF-06 | Escritorio/tablet responsive | CSS presente; no verificación completa |
| RNF-07 | Trazabilidad crítica | Parcial; completar eventos ausentes y alcance |
| RNF-08 | Separación de responsabilidades | Capas principales sí; separación interna parcial |
| RNF-09 | Unitarias/integración/aceptación | Primeras dos con evidencia; aceptación UI pendiente |
| RNF-10 | Variables de entorno | Implementado |
| RNF-11 | Errores centralizados | Implementado; diagnóstico y estabilidad pendientes de cierre prolongado |
| RNF-12 | Rendimiento analítico | Índices/límites presentes; sin prueba de carga representativa |

## Criterios de aceptación (PDF p. 13)

- [ ] PARCIAL: usuario autorizado accede solo a sus módulos; permisos comprobados en escenarios seleccionados, no matriz completa.
- [x] Venta con detalle actualiza inventario; integración y concurrencia aportan evidencia.
- [x] Ventas consultables desde Analytics.
- [x] Media y mediana correctas en casos probados.
- [ ] PARCIAL: identificar variables estadísticas desde la interfaz.
- [ ] FALLO: analizar y guardar variables aleatorias definidas.
- [x] Bayes reproducible para entradas válidas comprobadas.
- [x] Resultados de ventas en gráficos y KPIs; faltan paneles de p. 11 y aceptación visual.
- [x] Insights muestran evidencia y vínculo al análisis para nuevas evaluaciones.
- [ ] PARCIAL: todos los análisis almacenados y consultables; ver RF-21.
- [ ] PARCIAL: todas las acciones críticas auditadas; ver RF-22.
- [ ] PENDIENTE: superar toda la estrategia de pruebas antes del despliegue.

## Diferencias que no deben confundirse con faltantes obligatorios

- El PDF no impone Supabase, Vercel ni Render. Se eligieron en la conversación y respetan React/FastAPI/PostgreSQL.
- Las rutas están versionadas con `/api/v1`; el resumen es `/analytics/summary` y las variables aleatorias están bajo `/probability`. Son adaptaciones de la API inicial propuesta.
- La arquitectura dibuja NumPy/Pandas/SciPy; los cálculos actuales usan Python estándar y Decimal. No se encontraron esas dependencias. Si la rúbrica exige literalmente dichas librerías, debe ajustarse; el plan no exige usarlas para cada fórmula.
- La evolución a hipótesis, p-valor y modelos predictivos está en la sección 21 como trabajo posterior, no pendiente obligatorio de Semana 07. Ya hay varianza/esperanza en código, pero el guardado de variables aleatorias sigue fallando.
- El mapa departamental y diseño 3D son pedidos adicionales del usuario; hay implementación. La aceptación visual del mapa sigue pendiente.

## Prioridad de cierre propuesta

1. Corregir RF-15 y añadir regresión con PostgreSQL.
2. Completar gestión de usuarios, clasificación visible/datasets, reglas configurables y eventos de auditoría faltantes.
3. Completar paneles Analytics de la página 11.
4. Probar UI, responsive, PDF multipágina y aceptación integral; comprobar rendimiento/estabilidad.
5. Desplegar y verificar Vercel/Render/Supabase.
6. El usuario prepara la fase 16 con evidencias actualizadas.

## Evidencias y límites de esta auditoría

- Leídas las 14 páginas del PDF; revisados routers, formularios, consultas, esquemas, migraciones, configuraciones y pruebas relevantes.
- Supabase: consulta de tablas, RLS, migración vigente y constraint de `observations`, sin leer credenciales ni datos personales de negocio.
- Prueba dirigida en transacción revertida: análisis de venta 20.00 → media/mediana 20.00; Bayes → 0.4; variable aleatoria válida → fallo 23514. No quedaron filas de esa prueba.
- Código de producción no modificado en esta revisión. Este documento registra el estado real; no da los hallazgos por corregidos.
- No hubo sesión autenticada de navegador para la aceptación visual. No se certifican PDFs ni todos los estados de UI.


### Resultado final de verificaciones

- 4 de octubre: pytest **85 aprobadas**, pruebas frontend **10 aprobadas**, build TypeScript/Vite aprobado.
- 4 de octubre: prueba dirigida de descriptivo y Bayes aprobada; guardado de variable aleatoria falla con `CheckViolation 23514`.
- Integración comercial e insights y concurrencia de venta/pedido: evidencia completa aprobada en la sesión anterior (3 de octubre). La repetición lanzada durante esta auditoría emitió progreso, pero no se recuperó su resultado final tras el cambio de turno; no se contabiliza como nueva ejecución completa aprobada.
- Comprobación posterior: **0 empresas temporales** de las pruebas de concurrencia y **0 empresas temporales** de las pruebas con rollback. No se encontraron esos datos de prueba retenidos.
- El documento distingue implementación, pruebas seleccionadas y aceptación completa; el sistema todavía no cumple íntegramente el plan.
