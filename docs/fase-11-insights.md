# SalesIA Enterprise — Fase 11: Insights

API de reglas determinísticas para señalar caída semanal de ingresos y productos con cinco unidades o menos. Cada insight conserva código de regla, observación, evidencia, severidad y fecha; no atribuye causalidad ni predice demanda.

## Reglas y periodos

- Descenso de ingresos: compara siete días completos con los siete anteriores en America/Lima. El usuario selecciona el último día, hasta ayer. Se excluyen ventas anuladas y fechas posteriores al periodo.
- Se activa con caída de al menos 15 % cuando existe ingreso previo positivo. La ausencia de base previa no se presenta como una caída calculable.
- Stock bajo: revisa existencias actuales de productos activos, con umbral de cinco unidades. La fecha de inventario se distingue del periodo de ventas.
- El total de productos con stock bajo se calcula sin truncar; la evidencia muestra hasta 50 con menor cantidad e indica el total.

## Repetición, concurrencia e historial

La migración 0003 incorpora clave de deduplicación, estado, fecha de evaluación y fecha de resolución. La clave combina regla y fecha de cierre; el índice único incluye empresa. Un bloqueo transaccional por empresa serializa las ejecuciones de insights.

Repetir una evaluación actualiza su registro; si la condición deja de cumplirse, se marca resuelta. Si vuelve a cumplirse, se reactiva el mismo registro. Se conservan periodos distintos. El registro almacena la última evidencia del periodo; la auditoría conserva los contadores de cada ejecución, no una copia de cada versión de la evidencia.

Los registros anteriores a la migración conservan su fecha original y no se deduplican retroactivamente. Los estados describen la última evaluación, no monitoreo en tiempo real. Las reglas se ejecutan manualmente desde el botón; no hay tarea automática programada.

## Interfaz y acceso

Administrador, gerente y analista pueden consultar/generar. El historial tiene páginas de 25 registros, fecha y estado; la evidencia se muestra como importes comparados o tabla de stock. Una ejecución sin hallazgos se presenta como resultado normal.

## Validación y pendientes

Compilación correcta, 68 pruebas backend y 8 frontend aprobadas. Las pruebas cubren umbral exacto, semanas que cruzan meses, repetición, resolución y reactivación utilizando un doble de base de datos. Alembic genera el SQL de la migración correctamente.

Pendientes: aplicar la migración en PostgreSQL, comprobar ejecuciones simultáneas y revisar la pantalla con datos reales. Se mantienen 24 tablas; esta migración añade columnas e índice a insights.
