# Fase 15 — Vercel + Render + Supabase

Guía de despliegue acordado, 4 de octubre de 2026. Estado: preparado; todavía no publicado. Docker es una alternativa y no es necesario para este procedimiento.

## 1. Repositorio

Subir la raíz `salesia-enterprise` a un repositorio privado de GitHub. Debe contener frontend, backend, database, render.yaml y .github. No subir .env, .venv, node_modules, logs ni respaldos. El .gitignore los excluye. No arrastrar toda la carpeta al navegador: usar Git/VS Code para respetar exclusiones.

## 2. Backend en Render

Importar el repositorio mediante **New > Blueprint**, usando `render.yaml` de la raíz. Esa configuración instala `pip install ./backend`, migra con Alembic y ejecuta Uvicorn escuchando en `$PORT`. Se conserva la raíz del repositorio para acceder a `database/schema.sql`.

Variables:

| Variable | Valor |
|---|---|
| PYTHON_VERSION | 3.12.12 (declarada en render.yaml) |
| ENVIRONMENT | production |
| DATABASE_URL | Conexión PostgreSQL de Supabase que usa el backend, con prefijo postgresql+psycopg:// y SSL; introducirla solo en Render |
| SECRET_KEY | Generada por Render; conservarla entre despliegues |
| CORS_ORIGINS | Origen HTTPS exacto de Vercel, sin barra final; temporalmente puede ser http://localhost:5173 mientras se publica el frontend |

No crear una nueva base ni ejecutar el asistente de administrador: ya existen en Supabase. Nunca copiar DATABASE_URL o SECRET_KEY a Vercel ni compartirlas en el chat.

Si se configura **Web Service** manualmente: runtime Python, Root Directory vacío, Build Command `pip install ./backend`, Start Command `cd backend && python -m alembic upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`, Health Check `/ready`.

Una vez Live, comprobar `https://URL-REAL.onrender.com/health` y `/ready`. Guardar la URL real que asigna Render.

## 3. Frontend en Vercel

Importar el mismo repositorio:

- Root Directory: `frontend`
- Framework: Vite
- Node: 22.x
- Install: `npm ci`
- Build: `npm run build`
- Output: `dist`
- Variable de Production: `VITE_API_BASE_URL=https://URL-REAL.onrender.com/api/v1`

El valor se incorpora al compilar: si cambia, volver a desplegar. Los ejemplos URL-REAL se sustituyen por la URL del servicio, no se copian literalmente.

## 4. Conectar los orígenes

Copiar la URL de producción estable de Vercel a CORS_ORIGINS en Render y guardar los cambios. No usar un comodín. Si se mantiene desarrollo local, separar los orígenes exactos por coma. Las URL de preview de Vercel no se habilitan automáticamente.

## 5. Aceptación del despliegue

- [ ] Repositorio privado publicado sin secretos.
- [ ] API Live y /ready devuelve ready.
- [ ] Frontend publicado en HTTPS y apunta a la API real.
- [ ] CORS permite el dominio de producción.
- [ ] Login con usuario/empresa existentes y menú correcto.
- [ ] Catálogos, ventas, stock, Analytics y mapa cargan.
- [ ] Operación de prueba acordada, persistencia después de recargar y PDF descargado.
- [ ] Logs sin errores persistentes; revisar consumo y alertas del proveedor.
- [ ] Política de respaldo y recuperación definida en Supabase antes de operación real.

El plan Free de Render puede suspender el servicio por inactividad y demorar el primer acceso; no equivale a disponibilidad continua. Elegir un plan de pago solo con autorización del usuario. El blueprint actual utiliza Free.

Fuentes oficiales: https://render.com/docs/deploy-fastapi ; https://render.com/docs/free ; https://vercel.com/docs/frameworks/frontend/vite
