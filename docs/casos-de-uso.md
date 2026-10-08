# Casos de uso y aceptación — Fase 01

Revisión: 4 de octubre de 2026. Precondición común: cuenta activa y empresa autenticada. Las bajas son lógicas para conservar historia.

| Caso / actor | Flujo | Resultado esperado | Excepciones |
|---|---|---|---|
| CU01 Acceso / todos | Ingresar empresa, correo y contraseña | Sesión con vencimiento; módulos por rol | Credenciales inválidas 401; límite de intentos 429; cuenta bloqueada sin acceso |
| CU02 Usuarios / administrador | Crear; editar nombre, rol o estado | Cambio auditado; cambio de permisos revoca sesiones | Duplicado 409; no se puede quitar el propio acceso ni el último administrador |
| CU03 Clientes / administrador o vendedor | Crear, buscar, editar y consultar historial | Datos y ventas autorizadas de su empresa | Campos inválidos 422; registro ajeno 404 |
| CU04 Catálogo / administrador | Crear categoría y producto; editar/desactivar | SKU único, precio decimal, relación válida; ventas históricas intactas | SKU duplicado 409; precio/nombre inválido 422 |
| CU05 Inventario / administrador o almacén | Elegir almacén general o sucursal; ajustar con motivo | Saldo y movimiento atómicos; auditoría | Ajuste cero 422; saldo negativo 409 |
| CU06 Venta / administrador o vendedor | Agregar artículos con stock, cantidades y pago | Detalles, pago, saldo y auditoría confirmados juntos | Stock insuficiente, pago incoherente o reglas bloqueadas rechazan toda la venta |
| CU07 Pedido / administrador o vendedor | Crear pedido; confirmar con pago | Una sola conversión; conserva porcentajes y descuenta stock una vez | Confirmación repetida 409; cambio de precio/reglas exige recrear |
| CU08 Anulación / operador autorizado | Indicar motivo y confirmar devolución y recepción | Reposición y devolución registradas; historia conservada | Repetición rechazada; venta ajena inaccesible |
| CU09 Estadística / administrador, gerente, analista | Elegir variable/periodo; ejecutar; consultar historial | Media, mediana, dataset y observaciones persistidos | Fechas invertidas 422; ausencia de datos explicada |
| CU10 Probabilidad / administrador, gerente, analista | Definir distribución o eventos de Bayes | Esperanza/varianza o posterior reproducible y guardada | Suma distinta de 1, valores duplicados, P(B)=0 o eventos incompatibles 422 |
| CU11 Dashboard / roles autorizados | Aplicar periodo y filtros | KPIs y desgloses consistentes; vendedor limitado a sus ventas | Sin datos muestra cero; base cero no inventa porcentajes |
| CU12 Insights / administrador, gerente, analista | Evaluar reglas y abrir origen | Evidencia, análisis y dataset vinculados; sin duplicados activos | Si la regla deja de cumplirse se resuelve la alerta |
| CU13 Reportes / administrador, gerente, analista | Generar tipo/filtros; consultar; exportar | Snapshot inmutable, CSV, PDF y vista imprimible | Más de 10 000 ventas exige acotar periodo; empresa ajena 404 |
| CU14 Sucursales / consulta por rol; edición administrador | Crear ubicación/responsable; seleccionar mapa | Ficha e inventario por sede | Coordenadas inválidas 422; referencias ajenas rechazadas |
| CU15 Auditoría / administrador | Filtrar fecha/evento y paginar | Actor, referencia y cambios visibles | Otros roles 403; otras empresas excluidas |

## Reglas vigentes

- La empresa procede del token. Las referencias cruzadas se comprueban con claves foráneas y filtros de autorización.
- Cálculo por línea: bruto, descuento, impuesto sobre neto; redondeo decimal HALF_UP a dos decimales. Pagos suman el total.
- Stock nunca negativo; bloqueos transaccionales protegen ventas simultáneas.
- Descuentos/impuestos predeterminados por empresa; posibilidad de bloquear cambios por operación. Las ventas históricas no cambian.
- La anulación registra una devolución confirmada por el operador; no ejecuta una transferencia bancaria.
- Fechas comerciales America/Lima. Agregados separados por moneda.
- Probabilidades manuales se identifican como entradas del usuario. Los insights son reglas explicables, no predicciones.

Evidencia: pruebas de integración, concurrencia, permisos y aceptación en `fase-14-pruebas.md`. Producción corresponde a la fase 15.
