# Sucursales: implementación progresiva

3 de octubre de 2026. Referencia visual: captura de Matrixflow proporcionada por el usuario. Adaptación a SalesIA mediante mapa departamental peruano, marcadores, ficha lateral, responsable y directorio. No se copiaron sedes ni cifras del ejemplo.

Implementado: tabla branches con integridad por empresa y RLS (migración 0009 aplicada a Supabase); consulta para roles del sistema, altas y edición exclusivas de administrador, activación/desactivación, validación de coordenadas y auditoría transaccional. Total: 26 tablas de aplicación. Las coordenadas son opcionales y deben ingresarse como pareja; sedes sin coordenadas aparecen en el directorio.

Mapa Leaflet con GeoJSON local geoBoundaries PER ADM1, identificador PER-ADM1-1875124, fuente declarada Wikimedia Commons, licencia declarada Public Domain. Referencia y descarga exacta en frontend/public/maps/SOURCE.txt. No utiliza teselas externas ni geocodificación. Los departamentos se asocian mediante punto-en-polígono con las coordenadas registradas; se conserva atribución. El módulo se carga bajo demanda.

Pendientes funcionales: asignación de sucursal en ventas y pedidos; inventario y movimientos por sede; filtros y agregaciones por sucursal en Analytics y reportes; asignación de personal. Los KPIs de personal, stock y ventas por sede no se muestran hasta disponer de esas relaciones. No se reasignaron operaciones históricas a ubicaciones inventadas.

Validación: compilación TypeScript/Vite y aplicación de migración realizadas. Falta revisión visual y pruebas integradas de alta/edición, aislamiento entre empresas, puntos fronterizos y teclado. La fase 16 queda aplazada hasta finalizar funcionalidades.
