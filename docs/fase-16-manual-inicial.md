# SalesIA Enterprise — Fase 16: Manual inicial

## Inicio local

1. Instala Docker Desktop con Compose.
2. Copia `.env.example` a `.env` y cambia las claves de ejemplo.
3. Ejecuta `docker compose up --build` desde la carpeta raíz del proyecto.
4. Espera el mensaje del servicio `bootstrap` con el identificador de empresa.
5. Abre `http://localhost:5173` e inicia sesión con `ADMIN_EMAIL`, `ADMIN_PASSWORD` y el identificador informado.
6. Consulta la API y esquemas en `http://localhost:8000/docs`.

## Flujo de demostración

Crea un producto, añade stock en Inventario, crea un cliente, registra una venta y revisa el Dashboard. Desde Analytics corre un análisis de ventas; desde Bayes o Variable aleatoria ejecuta un análisis manual. Insights genera reglas comerciales y Reportes permite CSV.

## Respaldo y mantenimiento

Haz copia de PostgreSQL usando `pg_dump` y guarda `.env` en un gestor secreto. Conserva la copia de base y el commit del esquema/migración juntos. La inicialización de una instalación limpia ejecuta `alembic upgrade head`; una actualización existente debe respaldarse y revisarse antes de migrar.

Este manual es inicial. La guía de producción requiere proveedor, TLS, dominio, retención y política de respaldo definidos.
