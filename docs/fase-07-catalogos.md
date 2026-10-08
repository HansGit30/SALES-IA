# Fase 07 — Clientes, productos, categorías y vendedores

Clientes, productos, categorías y vendedores tienen consulta, alta, edición y cambio de estado. Productos capturan SKU, descripción, categoría y precio vigente, e inician el inventario en cero. Las pantallas comparten estilos de tabla, filtros, formularios, confirmaciones, carga y errores. Las acciones de edición respetan los permisos del rol.

La API limita filas por company_id, verifica que la categoría seleccionada corresponda a la misma empresa y usa restricciones únicas para SKU y nombre de categoría. Los usuarios tienen correo único por empresa; los clientes pueden compartir correo.

## Pendientes

Validación integrada con PostgreSQL, pruebas de auditoría/persistencia entre empresas, filtros avanzados y paginación con total en clientes/productos. Categorías y vendedores filtran y paginan en el navegador sobre su listado completo; el filtrado en servidor será necesario para directorios de gran volumen.

## Edición de clientes y productos

- Clientes: administrador y vendedor pueden crear, editar, desactivar y reactivar. Gerencia consulta.
- Productos: solo administración modifica SKU, nombre, descripción, categoría, precio y estado.
- Los cambios se guardan mediante PUT, con identificación de empresa tomada de la sesión; un registro de otra empresa devuelve 404.
- La misma transacción guarda los cambios y su auditoría con valores anteriores/nuevos.
- La desactivación conserva el registro y sus relaciones históricas. Ventas filtra los catálogos activos, y el servidor comprueba nuevamente el estado.
- Las tablas ofrecen búsqueda y páginas de 25 registros, con carga, error, reintento y confirmación de guardado.
- Los formularios permiten Escape, conservan el foco dentro del diálogo y muestran los errores dentro del formulario.

El cambio del precio del catálogo se aplica a ventas nuevas. Las líneas históricas conservan los importes guardados al confirmar cada venta.

## Categorías y vendedores

- Administración puede crear, editar, desactivar y reactivar; los demás roles autorizados consultan.
- Categorías ofrecen búsqueda por nombre, filtro activo/inactivo y páginas de 25 registros.
- Desactivar una categoría impide nuevas asignaciones; conserva los productos asociados y no cambia su disponibilidad.
- Vendedores ofrecen búsqueda por nombre/correo, filtro de estado y páginas de 25 registros.
- La edición de un vendedor conserva su cuenta vinculada; modifica el nombre del perfil comercial y su estado.
- Un perfil de vendedor inactivo impide registrar nuevas ventas desde esa cuenta, sin eliminar sus ventas previas.
- Crear un perfil vinculado toma automáticamente el nombre de la cuenta seleccionada. Las cuentas ofrecidas están activas, tienen rol vendedor y no están vinculadas a otro perfil.
- Las actualizaciones bloquean el registro durante la transacción y guardan cambios y auditoría de forma conjunta.

La compilación de producción y 25 pruebas unitarias/de autorización pasan. Las pruebas no sustituyen la aceptación funcional con PostgreSQL ni la inspección visual de todas las pantallas.
