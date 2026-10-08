# Fase 10 — Dashboard Analytics

El dashboard obtiene transacciones, ingresos, ticket medio, mediana y serie diaria desde ventas confirmadas. Se excluyen ventas anuladas. Los rangos disponibles son 7, 30, 90 y 365 días; KPIs y gráfico reciben las mismas fechas explícitas.

## Periodos, comparación y lectura

- Los rangos se calculan con el día de America/Lima. La API agrupa y filtra el dashboard con esa misma zona.
- Cada KPI compara contra un periodo adyacente de igual duración y muestra el valor anterior.
- Si la base anterior es cero y el valor actual es positivo, se indica que no hay base para una variación porcentual.
- El día actual puede estar incompleto; la interfaz lo explica al interpretar la comparación.
- Los días sin ventas se representan con cero. No se descartan los primeros días del rango.
- Los periodos cortos se muestran por día, 90 días por bloques de siete días desde el inicio seleccionado y 365 días por mes. Se conservan los intervalos parciales.
- La agregación monetaria del gráfico utiliza centavos enteros. Una tabla desplegable muestra los intervalos exactos, ventas e ingresos.
- La moneda se obtiene de la empresa; el vendedor consulta únicamente sus propias ventas.
- El dashboard de almacén conserva su enfoque de existencias. El dashboard comercial incluye accesos permitidos a ventas, laboratorio, reportes e insights.

Validación del 2 de octubre de 2026: compilación de producción, 59 pruebas backend y 8 frontend aprobadas. Se comprueban periodos de Lima, comparación sin base, agrupación y conservación de importes, más parámetros de empresa/vendedor y zona en las consultas. Falta verificar consultas y resultados contra PostgreSQL real.

## Pendientes

Distribución comparativa de ventas entre segmentos e inspección visual/integrada con datos reales. La comparación temporal, el selector de periodos y los filtros por vendedor/producto/categoría están implementados.

## Filtros por segmento

- Los selectores de vendedor, producto y categoría usan opciones de la empresa activa, incluidos registros inactivos que conservan historial.
- La selección se aplica al resumen actual, resumen anterior y serie temporal con los mismos parámetros.
- Un vendedor sigue limitado a sus ventas, incluso si envía manualmente otro identificador de vendedor.
- Producto y categoría seleccionan ventas que contienen una línea coincidente con ambos filtros. Se usa EXISTS para evitar duplicar una venta con varias líneas.
- Los ingresos y tickets son los totales completos de las ventas seleccionadas; no son los ingresos exclusivos de las líneas filtradas. La interfaz explica esta definición.
- La categoría corresponde a la clasificación actual del producto, pues no hay snapshot histórico de categoría en el detalle de venta.
- Cambiar categoría limpia el producto seleccionado. Limpiar filtros conserva el periodo elegido.
- Los parámetros nulos tienen tipos explícitos en las consultas para facilitar su resolución en PostgreSQL.

Verificación posterior a los filtros: 61 pruebas backend y 8 frontend aprobadas, y compilación de producción correcta. Las pruebas de parámetros y alcance no reemplazan la comprobación de resultados sobre PostgreSQL.
