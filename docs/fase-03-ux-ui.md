# SalesIA Enterprise — Fase 03: UX/UI

## Principios de interfaz

- Interfaz de trabajo empresarial: navegación persistente, títulos claros y acciones principales visibles.
- Primero escritorio/tablet; comportamiento adaptable en móvil para consulta y tareas esenciales.
- Un lenguaje visual compartido para estados, formularios, tablas, filtros, métricas y gráficos.
- Cargas, vacíos, errores y éxitos siempre visibles y recuperables.
- Cada indicador muestra periodo y filtros aplicados; gráficos incluyen unidades y etiquetas.
- Acciones irreversibles como anular requieren confirmación y motivo.

## Mapa de navegación

1. **Inicio de sesión**
2. **Dashboard** — resumen, tendencias e insights recientes.
3. **Ventas** — listado, filtros, nueva venta, detalle y anulación autorizada.
4. **Clientes** — listado, ficha e historial comercial.
5. **Productos** — catálogo, categorías, precios y estado.
6. **Inventario** — existencias, alertas y movimientos.
7. **Analytics** — resumen, ventas, productos, clientes, vendedores, variables y probabilidad.
8. **Insights** — reglas, evidencia, severidad e historial.
9. **Reportes** — selección de reporte, filtros, vista imprimible/exportación.
10. **Administración** — usuarios, roles y configuración (solo permisos adecuados).

## Pantallas y componentes

- Shell: sidebar, topbar, selector de periodo, perfil y contenido.
- Dashboard: tarjetas KPI, serie temporal, ranking de productos/vendedores y panel de insights.
- Tabla compartida: búsqueda, filtros, orden, paginación y estados accesibles.
- Formulario de venta: cliente, productos/cantidades, subtotal/descuento/impuesto/total, pago y validación de stock.
- Analytics: filtros persistentes, gráficos con tablas accesibles equivalentes, media/mediana y detalle del cálculo.
- Bayes: formulario de P(A), P(B|A), P(B); muestra resultado, validaciones, fórmula y explicación.
- Insights: texto explicable, valor observado, umbral/regla, periodo y enlace al análisis origen.

## Sistema visual inicial

- Color primario: azul corporativo; acento: cyan; superficies blancas y grises neutrales.
- Semántica: verde para éxito, ámbar para advertencia, rojo para error/anulación.
- Tipografía sans-serif de sistema; tamaños y espaciados basados en escala consistente.
- Contraste y foco de teclado visibles; no usar color como único portador de significado.

Los valores exactos se definirán como tokens al construir el frontend; no se inventa identidad gráfica del cliente.

## Roles y visibilidad

El frontend oculta navegación y acciones no pertinentes para reducir errores, pero toda autorización real se hace y valida en la API. Gerente y Analista ven Analytics/reportes; Almacén ve inventario; Administrador gestiona usuarios; Vendedor trabaja con clientes y ventas según permisos.

## Entregable UX

Este mapa sirve como base de componentes y rutas. Las pantallas finales se validarán visualmente al implementarlas; cada formulario tendrá estados de validación y respuesta de API.
