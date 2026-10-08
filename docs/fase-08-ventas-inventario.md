# Fase 08 — Ventas, pagos e inventario

La API valida perfil de vendedor y cliente, carga precios vigentes desde el catálogo, bloquea filas de inventario durante la venta, calcula importes decimales, valida stock y coincidencia total de pagos, guarda snapshots del artículo y hace los cambios dentro de una única transacción PostgreSQL.

La anulación exige motivo, revierte stock con movimiento compensatorio, marca pagos como reembolsados, cambia el estado sin borrar filas y registra auditoría. El vendedor solo puede anular sus propias ventas; admin puede anular cualquier venta.

La interfaz permite elegir cliente, artículos con stock, cantidad y método de pago. Impuestos y descuentos por porcentaje están admitidos por la API y quedan en cero desde la interfaz mientras no se confirme una regla de negocio.

## Pendientes

Prueba integrada simultánea de stock, aceptación de la conversión de pedidos y de la anulación con PostgreSQL, e inspección visual del recibo impreso con ventas largas. Los pagos son registros internos; no hay conexión con una pasarela que ejecute cobros o devoluciones.

## Avances de trazabilidad y autorización

- Historial de inventario visible, con páginas de 25 movimientos y filtro por producto; incluye fecha, tipo, cantidad con signo, responsable, motivo y referencia de venta.
- El historial incluye productos inactivos al consultar todos los movimientos y se actualiza tras un ajuste.
- El servidor restringe inventario a administración, gerencia y almacén. El detalle de ventas está disponible para administración, gerencia y vendedor, conservando el filtro de ventas propias de este último.
- La anulación comprueba la propiedad de la venta antes de modificar stock o pagos. Una venta ajena devuelve 404 para el vendedor.
- La auditoría conserva el motivo real de anulación; no acepta motivos compuestos solo de espacios.
- Creación y anulación recorren los productos en orden de identificador para reducir el riesgo de bloqueos cruzados entre operaciones concurrentes.
- Los rangos de consulta validan fechas y rechazan un final anterior al inicio.

La compilación del frontend y las 47 pruebas actuales pasan. Las nuevas pruebas incluyen rechazo de anulación ajena antes de mutaciones, acceso a datos operativos por rol y validación de rango/motivo. La concurrencia, persistencia y reversa real de stock siguen pendientes de integración en PostgreSQL.

## Pedidos previos a la venta

- Nuevas tablas `orders` y `order_details`, añadidas por la migración 0002.
- Administrador y vendedor crean y gestionan pedidos; gerente consulta. El vendedor accede solo a sus propios pedidos.
- Crear un pedido guarda precios y nombres del catálogo. No registra pagos ni reserva/descuenta inventario.
- Los estados son pendiente, convertido y cancelado. Solo un pendiente admite conversión o cancelación.
- La conversión vuelve a comprobar precios, moneda, disponibilidad, stock y suma del pago. Un cambio de precio exige cancelar y crear un pedido actualizado.
- Una sola transacción guarda la venta, pago, movimientos, vínculo con el pedido y auditoría. El pedido se bloquea para evitar doble conversión.
- La cancelación exige motivo y conserva las líneas. La cuenta de origen y el historial no se eliminan.
- La pantalla incluye lista paginada, detalle, importe, método de pago y confirmación explícita.

## Formulario y cálculo monetario

Ventas y pedidos comparten un formulario con búsqueda de cliente/artículo, selección explícita, cantidades fraccionarias, errores dentro del diálogo y bloqueo del envío repetido. Las búsquedas muestran hasta 50 coincidencias y permiten acotar por nombre, correo o SKU.

El frontend calcula con enteros: precio en centavos por cantidad en milésimas, redondeo half-up por línea y suma de líneas redondeadas. Cuatro pruebas cubren mitades de centavo, sumas por línea, importes grandes y valores inválidos. La API vuelve a cargar precios y calcular importes al guardar.

## Recibo interno y devolución completa

- El historial de ventas tiene filtros de fecha/estado y paginación en servidor con orden estable por fecha e identificador.
- Cada venta ofrece detalle con empresa, cliente, vendedor, artículos históricos, cantidades, precios, descuentos, impuestos, totales y pagos.
- El recibo usa la moneda guardada en la venta. Su impresión oculta navegación, botones y formularios y utiliza formato A4; el navegador permite guardarlo como PDF.
- Las ventas anuladas conservan total original, motivo, fecha de anulación y estado de cada pago.
- La anulación se realiza desde un formulario con motivo y dos confirmaciones: artículos recibidos para reposición y dinero devuelto íntegramente.
- La API exige `refund_confirmed: true` y `restock_confirmed: true`, además de `reason`; no acepta omitirlas ni enviarlas en falso. Ambas confirmaciones quedan en auditoría.
- El registro es de una devolución completa, realizada por el operador mediante los medios de pago correspondientes. La aplicación no mueve dinero. Las devoluciones parciales no están implementadas.

Validación del 2 de octubre de 2026: compilación de producción, 47 pruebas backend y 4 frontend aprobadas. El recibo está implementado, pero su impresión y la operación con datos reales siguen pendientes de comprobación.
