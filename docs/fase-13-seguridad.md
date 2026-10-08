# SalesIA Enterprise — Fase 13: Seguridad y auditoría

JWT con expiración configurable, contraseña Argon2, consulta del usuario activo en cada solicitud, autorización de roles en API, aislamiento por company_id y referencias compuestas de integridad. La venta, anulación, ajuste de inventario, alta de usuarios y análisis guardan eventos auditables. Los errores de unicidad no exponen detalles SQL.

## Gestión de sesiones y contraseña

Se añadió la migración 0005_session_version, que incorpora una versión de sesión por usuario sin crear tablas adicionales. Los JWT incluyen esta versión y fecha de emisión; cada solicitud autenticada contrasta la versión con la base de datos. Los tokens anteriores sin las nuevas declaraciones requieren iniciar sesión nuevamente.

Todos los roles disponen de «Mi seguridad»: cambio de contraseña con comprobación de la actual y mínimo 12 caracteres, y cierre de todas las sesiones con confirmación. Ambas operaciones incrementan la versión y registran auditoría en la misma transacción. El cambio de contraseña bloquea la fila del usuario para evitar cambios concurrentes con una sesión obsoleta. No se guardan contraseñas ni tokens en auditoría.

La salida habitual del menú sigue siendo local; la revocación en servidor se realiza desde «Mi seguridad». Aplicar `alembic upgrade head` antes de iniciar esta versión de la API.

**Pendiente:** recuperación de cuenta, política de retención de auditoría, controles automatizados de permisos y revisión integrada con PostgreSQL antes del despliegue real. No se ejecutaron pruebas en este avance.


## Protección de autenticación (2026-10-02)

La migración 0006_auth_rate_limits agrega una tabla operativa de ventanas de intentos. El esquema completo pasa a 25 tablas. Los contadores se comparten entre procesos de API mediante actualizaciones atómicas de PostgreSQL y se confirman antes de comprobar las credenciales.

Valores predeterminados: 10 solicitudes por cuenta y empresa, 100 por IP, en ventanas fijas de 900 segundos. Se cuentan tanto aciertos como errores; un inicio exitoso no reinicia la ventana. El cambio de contraseña dispone de su propio límite por usuario. Las solicitudes excedidas reciben HTTP 429, Retry-After y un mensaje con segundos de espera. Las solicitudes rechazadas no prolongan la ventana.

Las claves se guardan como HMAC SHA-256 con el secreto de la aplicación; no se persisten correos ni IP en esta tabla. Cada solicitud elimina hasta 100 ventanas vencidas y las ventanas reutilizadas se reinician al vencer. Esta limpieza es oportunista: no constituye una garantía de eliminación a plazo fijo cuando no hay tráfico.

Se auditan auth.login_succeeded y auth.login_failed para usuarios activos existentes. Los intentos con cuentas inexistentes o inactivas reciben el mismo mensaje y una comprobación de hash de reemplazo; no generan eventos vinculados a una empresa no validada. Contraseñas y tokens no se incluyen en los eventos.

La IP se obtiene de request.client; no se leen directamente cabeceras reenviadas. En despliegues con proxy debe configurarse la confianza de Uvicorn exclusivamente para los proxies conocidos. Los límites por IP pueden agrupar usuarios que comparten una red.

Se corrigió además el rechazo del secreto de ejemplo replace-with-... en producción y se acotaron los parámetros de expiración y límites. Aplicar alembic upgrade head antes de arrancar la API actualizada. Pendiente comprobar migración, concurrencia, expiración y auditoría con PostgreSQL; no se ejecutaron pruebas en este avance.


## Recuperación asistida de cuentas (2026-10-02)

La migración 0007_password_change añade must_change_password a users, manteniendo 25 tablas. Las cuentas existentes conservan su estado; las nuevas cuentas creadas desde administración requieren cambiar la contraseña inicial.

En Configuración, Restablecer acceso permite a un administrador recuperar a otro usuario activo de su empresa. Se exige la contraseña actual del administrador, una clave temporal de al menos 12 caracteres diferente de la anterior y confirmación en la interfaz. La operación limita intentos, bloquea las filas en orden estable, revoca todas las sesiones del usuario y registra user.password_reset sin secretos. Para cambiar su propia contraseña, el administrador usa Mi seguridad.

El inicio con clave temporal conduce a Protege tu cuenta. El servidor bloquea todos los endpoints autenticados excepto cambio de contraseña y cierre global de sesiones hasta completar el cambio. Al guardar la contraseña personal, elimina la obligación y revoca las sesiones temporales. La compilación del frontend terminó correctamente; no se ejecutaron pruebas en este avance.

La entrega de la clave temporal es manual por un canal seguro; no se envían correos. La recuperación autónoma por correo y la recuperación del único administrador sin acceso siguen pendientes. Aplicar alembic upgrade head antes de iniciar esta versión y comprobar con PostgreSQL el flujo completo, aislamiento, concurrencia y permisos.


## Explorador de auditoría

Configuración incluye el registro completo paginado de 25 eventos por página, filtros por tipo de evento y fechas de Lima, actualización manual y detalle desplegable. La API aplica autorización de administrador, aislamiento por empresa y paginación en servidor. El catálogo de eventos se obtiene de las acciones registradas en la misma empresa. Las fechas finales incluyen el día completo. No se ofrecen modificaciones ni borrado desde la interfaz.

Pendiente comprobar filtros, paginación y acceso con PostgreSQL y datos reales. No se ejecutaron pruebas en este avance.
