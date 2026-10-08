# SalesIA Enterprise — Fase 12: Reportes

Reportes comerciales y estadísticos por periodo en America/Lima. El reporte comercial contiene transacciones y estado; el estadístico contiene cantidad, ingresos, promedio, mediana, mínimo y máximo por moneda. Las anuladas se identifican y no suman ingresos.

## Copias persistidas e historial

La migración 0004 añade snapshot JSONB a reports, conservando las 24 tablas existentes. Al generar se guardan filas, parámetros, resumen y fecha. Abrir o descargar un reporte guardado usa esa copia y no vuelve a consultar ventas. Una anulación o edición posterior no cambia el archivo de un reporte anterior.

Historial y detalle comercial se paginan en la interfaz; el historial también se pagina en servidor. Los registros anteriores a la migración se identifican sin contenido descargable y permiten reutilizar sus fechas para generar un reporte nuevo.

Los accesos están limitados a administrador, gerente y analista, con filtro de empresa en servidor. Generar un reporte registra auditoría dentro de la misma transacción.

## Formato y límites

- CSV UTF-8 con BOM, comillas y escape de separadores/saltos de línea.
- Textos que podrían interpretarse como fórmulas se prefijan con apóstrofo.
- Los importes se conservan como decimales y se agrupan por moneda; no se suman monedas distintas.
- Un reporte vacío sigue siendo válido y no inventa moneda ni indicadores.
- Máximo 10 000 ventas por reporte. Si el rango excede el límite, se rechaza solicitando un periodo menor; no se truncan datos silenciosamente.
- La ruta de exportación directa sigue disponible para una consulta actual. La interfaz descarga por identificador de reporte para mantener reproducibilidad.

## Validación y pendientes

Compilación de producción correcta, 83 pruebas backend y 8 frontend aprobadas. Las pruebas cubren exclusión de anuladas, agrupación por moneda, casos vacíos, escape CSV, copia independiente de los datos originales y autorización. Alembic genera el SQL de las cuatro migraciones.

## Filtros y plantilla PDF (2026-10-02)

Implementados filtros combinables por cliente, vendedor y producto, validados por empresa en servidor. La copia archivada conserva los nombres e identificadores seleccionados. El filtro de producto incluye el total completo de las ventas que lo contienen y utiliza EXISTS para evitar duplicados.

Los reportes comerciales y estadísticos ofrecen vista de impresión A4 y guardado como PDF mediante el navegador. Se incluyen todos los registros archivados, independientemente de la página visible en pantalla. Reportes y recibos comparten los componentes DocumentBrand y DocumentFooter y el estilo report-document: azul oscuro, acentos turquesa, jerarquía tipográfica, metadatos, secciones numeradas, tablas y notas de interpretación. Las cabeceras de tabla se repiten al imprimir y se evita dividir filas entre páginas.

La compilación de producción de estos cambios terminó correctamente. Las cifras de pruebas anteriores corresponden a la versión previa a estos filtros y plantilla; no se ejecutaron nuevamente en esta entrega.

Pendientes: aplicar la migración y comprobar persistencia con PostgreSQL; inspeccionar visualmente los PDF con datos reales, textos extensos y varias páginas. El guardado PDF utiliza el diálogo de impresión del navegador; no hay un generador PDF en servidor. El recibo imprimible individual de venta pertenece a la fase 8.
