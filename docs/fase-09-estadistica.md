# Fase 09 — Motor estadístico

Incluye media, mediana y comparación para muestras; cálculo de media/mediana y rango sobre montos o unidades por venta confirmada; persistencia de dataset, variable, observaciones, parámetros, resultados e historial; Teorema de Bayes con validación matemática y registro; y análisis de variable aleatoria discreta (esperanza, varianza y desviación estándar).

Bayes exige eventos y probabilidades explícitas; las probabilidades deben estar en [0,1] y `P(B)>0`. Variables aleatorias exigen masa de probabilidad sumando 1. Los resultados guardan entradas para reproducibilidad.

## Pendientes

Validación de persistencia e historial con PostgreSQL, inspección visual del laboratorio con datos reales, tipos cualitativos y otras distribuciones que correspondan al alcance final.

## Avance del 2 de octubre de 2026

- El laboratorio presenta resultados como métricas y explicación de Bayes; permite volver a consultar los resultados del historial.
- La distribución discreta se edita por filas de valor/probabilidad e incluye gráfico y suma visible. Los datos precargados están identificados como ejemplo.
- Se rechazan observaciones infinitas/NaN, eventos vacíos, resultados duplicados, probabilidades que no suman uno y varianzas que exceden la columna numérica de almacenamiento.
- Bayes comprueba que la intersección no supere P(B) y que la parte de B fuera de A no supere P(no A). Se rechazan combinaciones imposibles antes de persistir.
- Se admite una variable constante con un único resultado de probabilidad uno.
- Media y mediana evitan desbordamientos intermedios; comparar medias/medianas rechaza una diferencia no representable.
- Estadística manual, análisis persistidos e historial están restringidos a administrador, gerente y analista.
- Se corrigió el parámetro de vendedor faltante en las consultas de análisis. Las cantidades fraccionarias se clasifican como variable continua.

Validación: 57 pruebas backend, 4 frontend y compilación de producción aprobadas. Las pruebas nuevas cubren probabilidades incompatibles, valores no finitos, distribución constante, valores repetidos y parámetros SQL del análisis de ventas. La ejecución integrada con PostgreSQL continúa pendiente.
