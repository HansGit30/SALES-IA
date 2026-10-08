# Sistema visual SalesIA Enterprise

El diseño se implementa de forma consistente a través de las fases funcionales: operaciones, Analytics, probabilidad, insights, reportes y administración comparten navegación, tipografía, escala de espacios, tarjetas, tablas, campos y mensajes de estado.

## Identidad

- Azul marino para estructura y confianza; azul medio para acciones principales; cyan solo como acento de marca.
- Superficies blancas sobre fondo gris azulado muy claro, bordes discretos y sombras cortas.
- Tipografía DM Sans para lectura e interacción, Manrope para títulos y cifras importantes.
- La moneda de la interfaz usa PEN de forma provisional; la implementación debe leer `currency` de la empresa antes de habilitar monedas distintas.

## Reglas de acabado

- Cada pantalla lleva título, una frase que explica la tarea y acciones alineadas en la parte superior.
- Filtros se muestran junto a la tabla o el dato que controlan.
- Tablas tienen encabezados consistentes, vacíos claros, carga visible y errores que permiten recuperarse.
- Formularios validan antes de enviar; las confirmaciones explican el efecto sobre el negocio.
- KPI y gráficos muestran periodo, estado de operación incluido y unidad.
- Gráficos se acompañan de texto o tabla legible y nunca codifican estado solo con color.
- Un rol solo ve acciones que su API le permite realizar; la comprobación real siempre se repite en el servidor.
- La interfaz se adapta a escritorio, tablet y móvil, mantiene foco de teclado y etiquetas accesibles.

## Componentes

`sidebar`, `topbar`, breadcrumbs, botones primarios/secundarios, tarjetas KPI, panel, tabla, badge de estado, filtros, modal, formulario, mensaje de error, vacío y carga.

## Revisión actual

El shell, login, dashboard, catálogos, ventas, inventario, laboratorio, insights, reportes y administración comparten tokens visuales en `frontend/src/styles.css`. La pantalla de acceso describe su gráfico como vista previa, sin presentar cifras de negocio como datos reales.


## Evolución corporativa — 3 de octubre de 2026

Capa de pantalla corporate.css: navegación azul profundo, acentos turquesa, superficies claras, escala tipográfica ampliada, campos y botones de 42–48 px, tablas con mayor legibilidad y estados de foco visibles. La composición DataSculpture usa CSS 3D y es decorativa (aria-hidden); no representa cifras de negocio. El hero del dashboard ofrece una acción según rol. El movimiento se desactiva mediante prefers-reduced-motion.

La ayuda del shell abre una guía de tres pasos. Se retiraron referencias a un plan contratado y un correo de soporte ficticio. Los estilos corporativos se limitan a screen para conservar las plantillas de impresión. Compilación del frontend realizada; queda pendiente inspección visual en navegador de todos los módulos y tamaños. No se ejecutaron pruebas funcionales en este avance.
