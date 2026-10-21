# AhorroScan — Inventario maestro de requisitos y funcionalidades
Última revisión: 2026-10-18
Entorno de referencia: VPS de producción `vps-b54471a2`
Repositorio principal: `/home/debian/ahorroscan/production/current/telegram-bot-v2`

## 0. Regla permanente de gestión del proyecto

Este documento es la fuente de verdad funcional para las decisiones y requisitos de AhorroScan. No sustituye al código ni a los logs: se contrasta con ellos.

Ante cada nueva petición:
1. Añadirla aquí como requisito nuevo o modificación explícita de uno existente, con fecha y estado.
2. Identificar qué módulos, canales, webs, automatizaciones, datos y campañas pueden verse afectados.
3. Antes de editar, registrar el comportamiento previo y preparar copia/rollback cuando corresponda.
4. Aplicar el cambio sin eliminar requisitos anteriores salvo instrucción explícita del usuario.
5. Ejecutar pruebas automáticas y comprobaciones funcionales de regresión.
6. Verificar el resultado en producción cuando esté autorizado, incluida la publicación real si forma parte de la petición.
7. Revisar este inventario, los logs y el estado final. No declarar completado lo que solo esté configurado o escrito en código.
8. Si dos requisitos entran en conflicto, señalarlo y preservar el requisito explícito más reciente; no decidir silenciosamente.

Estados:
- **VERIFICADO**: comprobado directamente en producción en esta revisión.
- **IMPLEMENTADO / VERIFICACIÓN PENDIENTE**: hay código o configuración, pero no se ha demostrado que funcione ahora de extremo a extremo.
- **INCIDENCIA**: existe una contradicción, bloqueo o fallo comprobado.
- **PENDIENTE / PLANIFICADO**: solicitado, pero no desplegado o no activado.
- **POR ACLARAR**: hay registros históricos contradictorios o no se puede confirmar la programación actual.

## 1. Infraestructura y separación de entornos

- **VERIFICADO** Producción principal en VPS Debian: `/home/debian/ahorroscan/production/current/telegram-bot-v2`.
- **VERIFICADO** Existe entorno separado de pruebas en `/home/debian/ahorroscan/test/current/telegram-bot-v2`.
- **VERIFICADO** El proceso unificado `run_multichannel.py --publish` estaba ejecutándose en producción durante la auditoría del 18/10/2026.
- **VERIFICADO** El ciclo de Hogar también estaba ejecutándose en producción durante esa auditoría.
- **VERIFICADO** Está presente `ha_lease_agent.py`; existe arquitectura de lease/fencing para evitar publicaciones simultáneas en nodos de respaldo.
- **IMPLEMENTADO / VERIFICACIÓN PENDIENTE** Respaldo previsto: VPS de producción → Raspberry Pi 4 → HP MicroServer. La continuidad y recuperación deben volver a comprobarse en pruebas de failover; no tocar secretos ni nodos secundarios durante tareas ajenas.
- **VERIFICADO** El dominio `ahorroscan.com` se configuró para redirigir mediante 301 a `ahorroscan.es`.
- **IMPLEMENTADO / VERIFICACIÓN PENDIENTE** Monitorización de salud, Watchdog, ciclos multicanal, catálogo web y redirector de enlaces.
- Regla: el VPS es producción. TEST no debe confundirse con producción. No realizar experimentos en producción sin necesidad y sin respaldo.

## 2. Canales, webs y redes

### Canales de Telegram
- **VERIFICADO / ACTIVO** AhorroScan Tech: canal tecnológico general.
- **VERIFICADO / ACTIVO** AhorroScan Hogar: ofertas de hogar, bricolaje y categorías relacionadas; sistema separado `ahorroscan-hogar`.
- **VERIFICADO / ACTIVO** AhorroScan Móviles: prioridad a teléfonos móviles/tablets, con proporción de contenido deseada 80% móviles y 20% accesorios; objetivo solicitado de 1–2 móviles al día cuando haya ofertas aptas.
- **VERIFICADO / ACTIVO** AhorroScan Mascotas.
- **VERIFICADO / ACTIVO** AhorroScan Moda.
- **VERIFICADO / ACTIVO** AhorroScan Deportes.
- **VERIFICADO / ACTIVO** Canal general de AhorroScan, destinado también a campañas globales.
- **PENDIENTE / NO ACTIVAR SIN AUTORIZACIÓN** Viajes y Vuelos: canal creado `@ahorroscan_viajes`, pero el usuario pidió preparar el diseño/hoja de ruta sin activar publicaciones. Debe cubrir vuelos, hoteles, paquetes, cruceros y alquiler de coches, buscar en aeropuertos españoles y priorizar ofertas.
- **PLANIFICADO** Otros verticales del registro/catálogos: Belleza, Familia, Automóvil y Bricolaje. La presencia de categorías en el registro no significa que deban publicar en producción.

### Webs
- **VERIFICADO** Web principal: https://ahorroscan.es.
- **IMPLEMENTADO / VERIFICACIÓN PENDIENTE** Web de Hogar, con catálogo y enlaces propios.
- **VERIFICADO EN LA AUDITORÍA DEL 17/10** La auditoría de catálogo devolvió HTTP 200 en los seis catálogos comprobados y sin avisos de catálogo obsoleto.
- Mantener coherencia de cabecera y menú entre Tech y Hogar, enlace/logotipo del canal de Telegram y catálogos verticales.
- **PENDIENTE DE AUDITORÍA** Confirmar que todas las webs de verticales solicitadas están publicadas, enlazadas y actualizadas.

### Instagram
- **IMPLEMENTADO / VERIFICACIÓN PENDIENTE** Publicación automática de ofertas y contenido editorial, perfiles/categorías por vertical y métricas mediante Instagram Insights.
- **IMPLEMENTADO** Registro editorial y seguimiento de views, alcance, likes, comentarios, guardados, compartidos e interacciones.
- **POR ACLARAR** Estado actual de las publicaciones automáticas, calendario editorial y permisos por perfil. Debe probarse con un caso real, no deducirse de la existencia de scripts.

## 3. Motor de búsqueda, selección y publicación de ofertas

- **VERIFICADO / IMPLEMENTADO** Conectores de Amazon y AliExpress, catálogo, clasificación por familias, puntuación/relevancia y selección.
- **VERIFICADO / IMPLEMENTADO** Enlaces de afiliación y publicación en Telegram con imagen al principio del mensaje y botón/enlace de compra, cuando la fuente proporciona imagen y enlace válidos.
- **VERIFICADO / IMPLEMENTADO** Deduplicación por producto/título, protección frente a republicaciones recientes, límites por ciclo y control de publicación.
- **VERIFICADO / IMPLEMENTADO** Flujo de selección de dos pasadas: primero filtros estrictos; si no hay candidatos válidos, filtros de respaldo más flexibles, manteniendo controles de calidad.
- **VERIFICADO / IMPLEMENTADO** Protección de descuentos engañosos mediante historial de precios cuando hay datos suficientes. No considerar una oferta auténtica solo porque el vendedor anuncie un descuento.
- **VERIFICADO / IMPLEMENTADO** Reglas para evitar que accesorios se clasifiquen como teléfonos móviles.
- **VERIFICADO / IMPLEMENTADO** Filtros de categoría, valoración, reseñas, relevancia, calidad, variedad y productos repetidos.
- **INCIDENCIA CONOCIDA** Amazon devuelve HTTP 503 en algunas búsquedas. El circuito de protección está activo y no debe desactivarse ni bombardear la fuente para forzar resultados.
- **IMPLEMENTADO / VERIFICACIÓN PENDIENTE** AliExpress tiene gestión de OAuth y un intento de renovación del token ante `IllegalAccessToken`.
- **PENDIENTE** Mejorar variedad y frecuencia de candidatos en canales verticales sin bajar los controles de calidad ni publicar productos engañosos.
- Regla: nunca solucionar la falta de publicaciones quitando filtros de seguridad sin una política explícita y pruebas.

## 4. Requisitos editoriales permanentes

- **VERIFICADO COMO PREFERENCIA DEL USUARIO** Priorizar móviles/tablets en Tech; reducir exceso de auriculares y smartwatches.
- **VERIFICADO COMO PREFERENCIA DEL USUARIO** En Móviles, objetivo 80% teléfonos y 20% accesorios, con objetivo de 1–2 teléfonos diarios si hay productos de calidad.
- **VERIFICADO COMO PREFERENCIA DEL USUARIO** Las imágenes deben aparecer al principio de los mensajes de Telegram.
- **VERIFICADO COMO PREFERENCIA DEL USUARIO** Evitar publicaciones repetitivas y repartir familias/categorías.
- **REQUISITO PERMANENTE** Los canales deben mantener continuidad razonable de publicaciones, con alertas de salud si superan los límites de inactividad; no se deben inventar publicaciones si no hay ofertas fiables.
- **PENDIENTE DE AUDITORÍA** Revisar los objetivos de frecuencia y composición por canal y convertirlos en métricas observables, no solo en preferencias en conversaciones.

## 5. Campañas estacionales: Halloween, Black Friday, Navidad y otras

### Halloween — PRIORIDAD URGENTE
- **REQUISITO EXPLÍCITO DEL USUARIO** Publicar bastantes más ofertas de Halloween, incluidos productos de Amazon Haul, en los canales que correspondan y en la web. La petición no debe olvidarse cuando se añadan otras funciones.
- **REQUISITO EXPLÍCITO DEL USUARIO** Se solicitaron creatividades/campaña de Halloween y publicación en canales y web.
- **IMPLEMENTADO PARCIALMENTE** Existen `seasonal_engine.py`, `seasonal_queries.py` y `seasonal_performance.py` con términos y ventanas estacionales de Halloween.
- **INCIDENCIA CONFIRMADA EN CÓDIGO (18/10/2026)** `selection.py` contiene términos de Halloween/disfraces en `TECH_NON_TECH_TERMS` y bloquea la categoría `seasonal_halloween` para Tech. `instagram_content_auto.py` también incluye Halloween en la lista de títulos bloqueados. Esto contradice la petición de promocionar Halloween y es una explicación plausible de la escasa presencia observada.
- **PENDIENTE PRIORITARIO** Auditar filtros, consultas, catálogo, clasificación, selección, publicación web, Instagram y Telegram. Corregir las exclusiones que impiden Halloween sin permitir que productos irrelevantes o de baja calidad entren en canales no apropiados.
- **PENDIENTE PRIORITARIO** Verificar con productos reales: descubrimiento de ofertas de Halloween, selección, publicación en Telegram/web y, cuando corresponda, Instagram. Registrar qué se publicó y en qué destino.
- La campaña debe seguir activa durante su ventana estacional, con controles de calidad y sin que una mejora técnica futura vuelva a bloquearla silenciosamente.

### Otras temporadas
- **IMPLEMENTADO / VERIFICACIÓN PENDIENTE** Motor estacional incluye Black Friday, Navidad, Año Nuevo, San Valentín, Día del Padre, Pascua, Día de la Madre y verano.
- **IMPLEMENTADO / VERIFICACIÓN PENDIENTE** Consultas estacionales programadas por ventana en `seasonal_queries.py`.
- Regla: verificar cada temporada antes y durante su ventana, y no dejar que listas de bloqueo genéricas anulen sus consultas y campañas.

### Prime Day
- Campaña temporal de Amazon Prime Day 2026: creatividad con texto “Amazon Prime Day 2026”, publicación en web, Telegram e Instagram, canal general incluido y repetición cada 6 horas hasta el final del evento.
- Se solicitó relajar filtros durante el evento con una valoración superior a 4,3 y condición de oferta, y no usar histórico de precios para la categoría informática durante esa campaña por distorsiones de escasez de memoria.
- **CERRADA TEMPORALMENTE** La campaña ya terminó. No mantener activado el modo Prime Day ni sus excepciones fuera de la ventana del evento. Recuperar filtros normales al terminar.

## 6. AhorroScan Price Watch

- **IMPLEMENTADO / VERIFICACIÓN PENDIENTE** Servicio “TÚ PONES EL PRECIO”: el usuario define el precio objetivo de un producto y el sistema lo monitoriza para avisar al alcanzarlo o caer por debajo.
- **REQUISITO EXPLÍCITO** Avisos con precio anterior, precio nuevo y enlace del producto.
- **REQUISITO EXPLÍCITO** Opciones de alerta por Telegram y correo electrónico.
- **REQUISITO EXPLÍCITO** Comprobación diaria del precio de los productos monitorizados.
- **IMPLEMENTADO / VERIFICACIÓN PENDIENTE** Página/landing Price Watch en ahorroscan.es y creatividad promocional aprobada `Buscador_AhorroScan_600.jpg`.
- **IMPLEMENTADO / VERIFICACIÓN PENDIENTE** Campaña de promoción de Price Watch en canal general, canales verticales activos e Instagram.
- **POR ACLARAR** La programación histórica tiene instrucciones distintas en conversaciones: campaña tres veces por semana (lunes/miércoles/viernes) y petición posterior de cambiar días a martes/jueves/domingo a las 19:00. No asumir que una programación está activa hasta inspeccionar y verificar la automatización concreta.
- **PENDIENTE PRIORITARIO** Comprobar alertas reales de extremo a extremo, incluidos Telegram y correo, y comprobar que la monitorización diaria sigue ejecutándose.

## 7. Contenido editorial y publicaciones programadas

- **REQUISITO EXPLÍCITO** Resumen semanal en el canal general los domingos a las 14:00, hora peninsular, y en Instagram.
- **POR ACLARAR** Existe una petición posterior de cambiar días a martes, jueves y domingo a las 19:00. Debe identificarse a qué tarea se aplicaba y qué horario debe considerarse vigente antes de reprogramar.
- **IMPLEMENTADO / VERIFICACIÓN PENDIENTE** Automatización editorial de Instagram y sincronización de métricas.
- **PENDIENTE** Crear una matriz única de todos los horarios recurrentes: ciclos de búsqueda/publicación, campañas promocionales, Price Watch, resúmenes semanales, Insights y tareas de mantenimiento. Verificar cada horario en el scheduler real y en sus logs.

## 8. Monetización, afiliación y analítica

- **VERIFICADO / IMPLEMENTADO** Amazon Afiliados y AliExpress Afiliados como fuentes principales.
- **IMPLEMENTADO / VERIFICACIÓN PENDIENTE** AWIN: conector y sincronización de informes/comisiones. Algunos anunciantes requieren aprobación y credenciales/configuración específicas.
- **PLANIFICADO / PENDIENTE DE VALIDACIÓN** TradeTracker, Webgains, eBay, Temu, Miravia y otros comerciantes/programas.
- **IMPLEMENTADO** Redirector de enlaces de afiliación, registro de clics y atribución por proyecto/canal/comerciante/producto cuando hay datos.
- **IMPLEMENTADO** Ledger de monetización, informes de clics y comisiones y sincronización de afiliados.
- **PENDIENTE** Dashboard claro con clics, origen/plataforma, canales, comerciantes, conversiones y comisiones.
- **PENDIENTE DE MEDICIÓN REAL** Confirmar que las ventas/comisiones atribuidas corresponden a datos reales; no presentar clics o ingresos estimados como ingresos confirmados.
- **PENDIENTE** Revisar exportaciones de los últimos 30 días y configuración de analítica web solicitadas anteriormente.

## 9. Watchdog, salud y recuperación

- **VERIFICADO / IMPLEMENTADO** Alerta de salud de canales por tiempo sin publicar. Ejemplo reciente: Moda alertó a las 32 horas frente al límite de 30.
- **VERIFICADO / IMPLEMENTADO** Logs de ciclos unificados y auditoría de catálogos web.
- **VERIFICADO / IMPLEMENTADO** Circuit breaker para proteger fuentes con errores repetidos como Amazon 503.
- **IMPLEMENTADO / VERIFICACIÓN PENDIENTE** HA Publisher Lease y fencing para que solo el nodo autorizado publique.
- **PENDIENTE** Revisar y resolver alertas Watchdog de forma sistemática; no silenciarlas sin corregir la causa.
- **PENDIENTE** Auditar la salud de todos los canales y automatizaciones, y asegurar que los errores de fuentes no se registran falsamente como ciclos correctos sin productos.
- **PENDIENTE** Rotar `LEASE_SECRET` cuando se ejecute la tarea específica, con coordinación de los nodos implicados.
- No tocar Raspberry Pi, MicroServer, roles HA ni secretos al resolver tareas de contenido que no lo requieran.

## 10. Otras iniciativas del usuario, separadas de AhorroScan

- **PROYECTO SEPARADO** Trading Copilot / Inversión: no mezclar sus cambios, rutas, claves ni despliegues con AhorroScan.
- **IDEA / PENDIENTE** Radar de chollos de segunda mano en Wallapop, eBay, TodoColeccion, Vinted y Milanuncios.
- **IDEA / PENDIENTE** Buscador/histórico de precios para detectar descuentos reales.
- Estas iniciativas no deben marcarse como funciones actuales de AhorroScan sin una decisión explícita de integración.

## 11. Incidencias y prioridades actuales al 18/10/2026

1. **P0 — Halloween**: los filtros del código bloquean parte del contenido de Halloween en Tech e Instagram. Auditar y corregir preservando calidad y pertinencia; comprobar publicaciones reales.
2. **P1 — Programaciones**: construir el inventario verificable de horarios y automatizaciones. Hay tareas solicitadas cuyos horarios vigentes no están confirmados.
3. **P1 — Price Watch**: probar monitorización y alertas Telegram/correo de extremo a extremo.
4. **P1 — Salud de canales**: comprobar continuidad de los seis verticales activos y canal general; mantener el VPS como producción.
5. **P2 — Amazon 503**: mantener circuit breaker, investigar recuperación sin forzar peticiones.
6. **P2 — Monetización**: auditar analítica, clics, ventas y comisiones con datos reales.
7. **P2 — Catálogos/web**: confirmar que todos los verticales activos tienen catálogo y enlaces correctos.

## 12. Registro de cambios del inventario

- **2026-10-18** — Creación del inventario maestro. Se registra la incidencia de filtros estacionales que bloquean Halloween y la necesidad de verificar los horarios reales de campañas recurrentes.
- Cada petición futura debe añadirse aquí con fecha, descripción, impacto, pruebas requeridas y estado. No borrar requisitos cumplidos: moverlos a histórico/cerrados conservando su trazabilidad.


## Actualización 2026-10-18 · Correcciones aplicadas
- **Halloween Tech:** se retiró el bloqueo de categoría global y se añadió una regla específica que solo acepta en Tech la categoría estacional cuando el título identifica electrónica/luz/proyector; disfraces siguen bloqueados. Pruebas de regresión añadidas.
- **Instagram editorial:** eliminado el bloqueo literal de la palabra Halloween en el generador editorial; se conservan bloqueos de elementos irrelevantes. El publicador principal ya no bloqueaba Halloween explícitamente.
- **Tech timer:** restaurado y habilitado con calendario cada dos horas. Próximo disparo comprobado por systemd: 16:00 UTC del 18/10/2026.
- **Price Watch promoción:** creado timer recurrente martes/jueves/domingo a las 19:00 Europe/Madrid. El script registra cada canal por fecha local para permitir recurrencia sin duplicar publicaciones el mismo día.
- **Resumen semanal:** copiado el generador a producción y creado timer domingo 14:00 Europe/Madrid. IMPORTANTE: el generador crea un borrador, no publica automáticamente en Telegram ni Instagram; esa integración queda pendiente, no se considera resuelta.
- **Validación:** pruebas Halloween 3/3; compilación Python y `bash -n run_auto.sh` correctos. La suite completa `test_selection.py` mantiene un fallo previo/no relacionado en `test_smartphone_high_confidence_can_enter_with_moderate_discount` (espera 1 producto y obtiene 0); requiere investigación separada.

- **Suite global:** `test_selection.py` conserva una prueba antigua que espera publicar un móvil con 12,5 % de descuento sin histórico suficiente; la política actual exige señales más fuertes cuando no hay histórico (descuento ≥20 %, rating ≥4,2 y ≥20 reseñas). No se relajó la política para hacer pasar ese test.

## 2026-10-18 · Lanzamiento real de publicaciones Halloween
- **Publicado en Telegram Hogar:** guirnalda LED Joomer Halloween 20 m / 200 LED (mensaje 177), con imagen, precio, enlace afiliado y valoración/reseñas.
- **Publicado en Telegram Tech:** la misma guirnalda LED, por ser iluminación tecnológica (mensaje 1165).
- **Publicado en Telegram Hogar:** arco hinchable de Halloween con fantasma y gato negro, iluminación LED (mensaje 178).
- **Web Hogar:** el catálogo `superofertastech-web/hogar/data/offers.json` se regeneró a las 15:49 UTC y contiene productos de Halloween.
- Se creó `data/halloween_manual_publications.json` para registrar envíos manuales y evitar duplicarlos al repetir la operación.
- La recolección AliExpress ya devuelve productos Halloween tras añadir reglas `future_seasonal_halloween*` en `aliexpress_classifier.py`; las guardas generales de calidad siguen activas.
- **Pendiente:** verificar el fin del ciclo Tech iniciado manualmente y comprobar Instagram. No se afirma publicación en Instagram ni en canal general.


## 2026-10-18 · Diagnóstico profundo AliExpress Tech
- Causa confirmada: `catalog.iter_queries("discovery")` devolvía las consultas dinámicas y hacía `return`, por lo que reemplazaba el catálogo base y dejaba fuera búsquedas de modelos/marcas. Corregido en producción y TEST: tendencias priorizan, catálogo base complementa sin duplicados.
- Causa confirmada: V6.3 omitía consultas de numerosas categorías por no tener ruta en `_rule_for`. Añadidas rutas para tablets, portátiles, sobremesa/mini PC, televisores, networking, componentes, CPU, placas base, smart home, wearables, gaming, alimentación, cámaras, proyectores, drones, VR, impresoras, lectores electrónicos y periféricos.
- Cobertura verificada: 61 pares de consultas de descubrimiento; 55 tienen ruta AliExpress. Se mantienen sin ruta 6 búsquedas de audio genérico/microfonía hasta validar reglas específicas.
- Prueba de API de solo lectura en producción: 12 familias consultadas; 23 ofertas brutas devueltas con imágenes/enlaces afiliados, pero se observaron falsos positivos y fichas sin suficientes reseñas. No se publicó nada.
- Endurecidas guardas por categoría para bloquear accesorios que aparecían como producto principal (p. ej. micrófono para iPad, cable elevador GPU, soporte de router, correas de reloj, piezas de batería y accesorios de robot).
- Validación: pruebas específicas de descubrimiento/clasificación pasan; suite completa TEST pasa. En producción persiste un test antiguo conocido que espera publicar un móvil con 12,5% sin histórico; no se ha usado para relajar la política.
- Pendiente: hacer búsquedas más específicas por marca/modelo y medir candidatos realmente publicables tras las guardas; revisar proporción de marcas reconocidas antes de desplegar los cambios de selector a todos los canales.


## 2026-10-18 · AliExpress: búsquedas por marca/modelo y registro de tareas
- **HECHO / VALIDADO EN CÓDIGO** Ampliado el catálogo Tech con búsquedas específicas de marcas/modelos en tablets (Xiaomi/Lenovo/Samsung), portátiles (Lenovo/ASUS/Acer/Huawei), mini-PC (Beelink/Minisforum/GMKtec/Geekom), monitores (AOC/LG/Gigabyte), televisores (Xiaomi/TCL/Hisense/LG), networking (TP-Link/ASUS/GL.iNet), SSD (Samsung/WD/Crucial/Kingston), componentes (ASUS/Gigabyte/MSI/Corsair), CPU (AMD/Intel), placas base (MSI/ASUS/Gigabyte), periféricos (Logitech/Keychron/Razer), smart home (Xiaomi/Roborock/Dreame/Tapo), wearables (Xiaomi/Amazfit/Huawei/Samsung), gaming (Anbernic/Retroid/8BitDo), power banks (Anker/Ugreen/Baseus) y proyectores (XGIMI/Anker/Optoma/Wanbo).
- **HECHO / CORRECCIÓN IMPORTANTE** La consulta específica del catálogo ahora se antepone a las consultas genéricas de respaldo en familias `future_*`; antes se generaba en el catálogo, pero `buscar()` la descartaba y ejecutaba únicamente la lista genérica de la regla.
- **HECHO** Cambios sincronizados en producción y TEST. Añadida prueba de regresión que verifica que `xiaomi pad 7` llega a la lista de consultas de AliExpress.
- **VALIDACIÓN PARCIAL** `py_compile` y pruebas específicas de descubrimiento/validación/clasificación pasan en producción y TEST. No se ha enviado ninguna publicación.
- **PENDIENTE** Ejecutar búsquedas reales de marca/modelo en modo solo lectura, contabilizar candidatos que superan todos los filtros editoriales y confirmar diversidad de marcas/productos antes de modificar frecuencia de publicación. Mantener umbrales de valoración, reseñas, descuento, relevancia, duplicados y control de accesorios.
- **REGISTRO DE TAREAS HECHAS** Esta entrada se incorpora al inventario maestro como registro persistente de trabajo realizado; no se localizó un archivo separado llamado lista de tareas hechas en el árbol inspeccionado.


## 2026-10-18 · Continuación AliExpress: consulta de marca enviada realmente a API
- **HECHO** Detectado en validación que las consultas de marca/modelo se generaban en el catálogo, pero para reglas ya existentes (móviles, monitores, SSD, ratones) también eran reemplazadas por búsquedas genéricas al llamar a AliExpress. Corregido: la consulta solicitada se ejecuta primero y se mantienen consultas de respaldo deduplicadas.
- **HECHO** Pruebas de regresión para rutas `future_*` y reglas existentes. Corregido test de catálogo completo que estaba fijado a un número antiguo (83) aunque el catálogo actual contiene 87 consultas; ahora compara con la estructura real.
- **VALIDACIÓN EN CURSO** Ejecutar suite completa en TEST y pruebas dirigidas en producción. No se publican ofertas durante esta comprobación.


## 2026-10-18 · Verificación real de búsquedas AliExpress por marca/modelo
- **HECHO / DIAGNÓSTICO** Consultadas 10 búsquedas en vivo en modo lectura: 18 ofertas devueltas, 13 superaron la guarda de categoría y solo 2 superaron un filtro preliminar de descuento/valoración/reseñas. Ese filtro preliminar no sustituye al selector completo; no se publicó nada.
- **INCIDENCIA DETECTADA** Las búsquedas específicas llegan ya a la API, pero AliExpress mezcla accesorios y productos sin historial de valoración incluso cuando la consulta menciona una marca/modelo. Ejemplos: cargadores Lenovo bajo ThinkPad, periféricos bajo tablet, accesorios bajo power bank y resultados genéricos de monitor.
- **HECHO** Endurecido el bloqueo de cargadores, adaptadores y repuestos cuando una consulta de portátil devuelve accesorios. Añadidas pruebas de regresión.
- **VALIDACIÓN** Suite completa de TEST: 36 pruebas pasan antes de este último ajuste; pruebas dirigidas y compilación se vuelven a ejecutar tras el ajuste.
- **PENDIENTE** Mejorar la relevancia semántica por categoría y medir con el selector completo, sin bajar umbrales de reseñas/valoración/descuento ni publicar durante diagnóstico.


## 2026-10-18 · AliExpress: verificación de coincidencia de marca/modelo
- **HECHO** El diagnóstico en vivo mostró que algunas búsquedas de marca devolvían artículos genéricos o de otra marca. Añadida validación explícita de marca/modelo para 50 consultas identificadas, sin relajar los umbrales editoriales.
- **HECHO** Añadida prueba de regresión para rechazar resultados genéricos y de marca incorrecta. Cambios sincronizados en producción y TEST.
- **PENDIENTE DE VALIDACIÓN FINAL** Ejecutar pruebas dirigidas y suite completa TEST; volver a medir resultados reales de solo lectura. No publicar durante el diagnóstico.


## 2026-10-18 · AliExpress: aislamiento de búsquedas específicas
- **HECHO** La prueba en vivo mostró que las búsquedas de marca se mezclaban con consultas genéricas de respaldo (por ejemplo, «Beelink mini PC» con «mini PC»), contaminando el lote con resultados sin marca o accesorios. Las reglas `future_*` ejecutan ahora únicamente la consulta solicitada; las búsquedas genéricas se ejecutan por separado desde el catálogo.
- **VALIDACIÓN** Prueba de regresión ajustada para comprobar aislamiento de la consulta específica. No se publica durante diagnóstico.


## 2026-10-18 · AliExpress: aislamiento de búsquedas específicas
- **HECHO** La prueba en vivo mostró que las búsquedas de marca se mezclaban con consultas genéricas de respaldo (por ejemplo, «Beelink mini PC» con «mini PC»), contaminando el lote con resultados sin marca o accesorios. Las reglas `future_*` ejecutan ahora únicamente la consulta solicitada; las búsquedas genéricas se ejecutan por separado desde el catálogo.
- **VALIDACIÓN** Prueba de regresión ajustada para comprobar aislamiento de la consulta específica. No se publica durante diagnóstico.


## 2026-10-18 · AliExpress: aislamiento general de búsquedas de marca
- **HECHO** La validación en vivo confirmó contaminación por aliases genéricos también en reglas ya existentes (SSD y ratones): resultados ajenos a la marca podían entrar desde la consulta genérica. Ahora toda consulta de marca/modelo que no sea un alias propio de la regla se ejecuta aislada; las consultas genéricas siguen descubriéndose por separado.
- **HECHO** Añadida guarda contra cargadores/adaptadores presentados como mini-PC. Pruebas de regresión añadidas.
- **PENDIENTE DE VALIDACIÓN** Suite completa TEST y nueva prueba en vivo de consultas aisladas. Sin publicaciones durante el diagnóstico.


## 2026-10-18 · Registro explícito de tareas hechas y guardas extra
- **HECHO** Creado `TAREAS_HECHAS.md` en producción y TEST para conservar tareas completadas y pendientes.
- **HECHO** Añadidos bloqueos de biseles/carcasa/repuestos de portátil y consumibles de aspiradoras robot (mopas, filtros HEPA, cajas de polvo, depósitos, cepillos).
- **PENDIENTE** Ejecutar suite completa TEST y una muestra final de búsquedas de solo lectura; no declarar lista la mejora hasta verificar los resultados tras las guardas.


## 2026-10-18 · Desbloqueo controlado del techo de puntuación `future_*`
- **HECHO** Detectado que los candidatos legítimos de familias nuevas recibían puntuaciones de 40-50 y no podían alcanzar ni el umbral relajado de publicación (55), aunque cumplieran descuento, valoración y reseñas. Añadida bonificación limitada de +20 solo con core coincidente, puntuación positiva y sin negativos duros.
- **SEGURIDAD** No se rebajan filtros de reseñas, valoración, descuento, categoría, accesorios ni duplicados. La bonificación solo permite que el producto llegue al selector final, no garantiza publicación.
- **VALIDACIÓN PENDIENTE** Pruebas de regresión, suite completa TEST y prueba final del selector con candidatos reales.


## 2026-10-18 · Verificación final de puntuación y selector editorial
- **HECHO** La bonificación de `future_*` permite que ofertas reales de calidad lleguen al selector, sin cambiar los umbrales de confianza.
- **PRUEBA REAL SOLO LECTURA** HONOR Pad X8a: puntuación 60, descuento 64%, valoración 5,0/5 con 364 reseñas; supera el pase relajado del predicado editorial. Robot aspirador ABIR X9: puntuación 70, descuento 63%, valoración 4,67/5 con 205 reseñas; supera el pase estricto. Ambos pasan la guarda de categoría.
- **ALCANCE** Se ha probado `_row_is_publicable` en ambos modos con productos reales; no se ha ejecutado deduplicación completa ni publicación, por lo que no se afirma que vayan a publicarse en el siguiente ciclo.
- **VALIDACIÓN** Suite completa TEST: 36 pruebas pasan; pruebas dirigidas y compilación en producción pasan.
- **SIN PUBLICACIONES DE PRUEBA**.


## 2026-10-20 · Convertidor de enlaces afiliados (MVP web)
- Añadido endpoint `POST /api/affiliate-convert` en la API web: valida URL y dominios admitidos, limita el tamaño de petición y solo consulta el catálogo local; no hace peticiones salientes a URLs aportadas por usuarios.
- Añadida sección web para pegar enlace, mostrar resultado y copiar el enlace afiliado.
- Alcance real de esta primera versión: devuelve enlaces de afiliación únicamente si el enlace original coincide exactamente con un producto del catálogo local. No convierte arbitrariamente productos externos ni simula conversiones cuando faltan APIs/credenciales.
- Pendiente: integrar APIs oficiales por tienda y flujo Telegram; validar mediante pruebas en entorno servido antes de promoción pública.


## 2026-10-20 · Conversión general de enlaces afiliados
- Sustituida la búsqueda exclusiva en catálogo por adaptadores por plataforma en `affiliate_connectors/link_converter.py`.
- Amazon España: incorpora el ID de asociado configurado al enlace original y conserva la ruta/parámetros útiles; solo acepta dominios Amazon.es.
- AliExpress: invoca `aliexpress.affiliate.link.generate` con credenciales y token OAuth existentes; no requiere producto previo en catálogo, aunque la API puede rechazar enlaces/productos no elegibles.
- Awin: usa el Link Builder oficial para Brico Depôt (anunciante 69488); otros anunciantes no se activan mientras su estado sea pendiente/rechazado/no unido o no esté habilitado.
- Web y Telegram comparten el convertidor. `/convertir` admite URL como argumento o enviada después del comando.
- Pruebas: Amazon fuera del catálogo OK; endpoint web Amazon fuera del catálogo OK; AliExpress generó URL afiliada para producto URL; entradas inválidas/no permitidas rechazadas; `py_compile` OK.
- Limitaciones: Amazon solo España; AliExpress depende de elegibilidad en API oficial; Awin solo Brico Depôt por ahora. No se ha publicado promoción.

## 2026-10-20 · Convertidor de afiliación responsive
- Rediseñada la interfaz web del convertidor para móvil, tablet y escritorio.
- El resultado muestra el enlace con ajuste de línea y dos acciones independientes: copiar al portapapeles y abrir en una pestaña nueva.
- Añadidos estados de conversión, error y confirmación de copia; controles accesibles y botones táctiles adaptados a móvil.
- El frontend reutiliza POST /api/affiliate-convert; no se modifica el backend ni se realizan publicaciones.
- Verificación técnica: revisión estática del frontend y respuesta HTTP del endpoint; la comprobación visual en dispositivos físicos queda pendiente si no hay navegador de prueba conectado.

## 2026-10-20 · Rediseño de inicio para acceso rápido
- Hero más compacto con propuesta de valor resumida.
- Dos accesos directos destacados al Buscador de precios y al Convertidor de enlaces, visibles justo bajo el encabezado.
- Herramientas organizadas en dos columnas en escritorio, una columna en móvil, y distribución adaptada para tablet.
- Se conservan IDs, formularios, endpoints, enlaces de navegación y contenido funcional existente.
- Verificación técnica: HTML/JS estático y servicio web; comprobación visual real en distintos tamaños pendiente si no hay navegador de prueba conectado.

## 2026-10-20 · Contraste visual de accesos principales
- Se refuerzan los CTA de inicio con alto contraste: azul para Buscador de precios y verde para Convertir enlace.
- Añadidos iconos en placas de color, sombras, bordes diferenciados, estados hover/foco y tamaños táctiles.
- Los paneles de herramientas conservan sus funciones, con acentos de color distintos para distinguirlos.

## 2026-10-20 · Fondo visual más suave
- Se reduce el blanco dominante de la página principal con un fondo gris azulado suave.
- Las áreas de Buscador y Convertidor usan fondos pastel diferenciados, manteniendo los CTA azul y verde de alto contraste.
- Los campos y resultados conservan superficies claras para legibilidad.

## 2026-10-20 · Tema nocturno oscuro
- La página principal pasa a un fondo azul marino muy oscuro para navegación nocturna y menor brillo percibido.
- Texto, bordes, campos, estados, resultados y controles adaptados para mantener contraste y legibilidad.
- Los accesos rápidos conservan el azul y verde intensos; las tarjetas de herramientas usan tonos oscuros diferenciados.

## 2026-10-20 · Tarjetas oscuras para canales
- Las tarjetas de canales de la página principal adoptan fondos oscuros con degradados sutiles y bordes superiores de color para destacar sin perder la estética nocturna.
- Texto y descripciones ajustados a alto contraste; botones de cada canal usan acentos cromáticos diferenciados.
- Las tarjetas de canales futuros se mantienen más discretas, también en modo oscuro.

## 2026-10-20 · Tema nocturno unificado en webs verticales
- Aplicados fondos oscuros, tarjetas contrastadas, tipografía clara y acentos cromáticos a las hojas de estilo compartidas por las webs verticales de AhorroScan.
- AhorroScan Tech recibe también ajustes específicos por utilizar estilos propios; Hogar recibe la capa oscura en su hoja local.
- Conservadas estructura HTML, rutas, scripts funcionales y metadatos SEO. Backups creados antes de modificar cada archivo.

## 2026-10-20 · Contraste reforzado en fichas de productos
- Tarjetas de producto y ofertas con panel azul marino oscuro, borde superior azul, sombra más profunda y texto de alto contraste.
- Precios actuales en verde claro, precios anteriores atenuados e imágenes con superficie clara para preservar las fotos de producto.
- Ajustes responsivos y backups previos en hojas de estilo compartidas y plantilla Tech.

## 2026-10-20 · Fondo oscuro para imágenes de producto
- La zona de imagen de las fichas usa un fondo azul marino; el elemento img queda transparente para que las imágenes con transparencia hereden el fondo. Las fotografías que ya incluyen fondo blanco dentro del propio archivo seguirán mostrando ese blanco.

## 2026-10-20 · Fase 1 multilingüe web (infraestructura inicial)
- Creado selector visible de idioma en la navegación y detección inicial del idioma del navegador. Idiomas: español, catalán, inglés, chino simplificado y portugués.
- La selección se guarda en localStorage y prevalece en visitas posteriores; si el idioma no se reconoce, se usa español.
- Añadida traducción inicial de elementos comunes y de los bloques principales de la página de inicio. No equivale todavía a una traducción completa de todas las páginas ni de contenido dinámico; URLs localizadas, hreflang y SEO multilingüe quedan para la siguiente etapa.

## 2026-10-20 · Ampliación de traducciones y cobertura de páginas
- Ampliado el vocabulario traducible de navegación, estados de catálogo, categorías, fichas y páginas informativas para ca/en/zh/pt.
- Selector incorporado también a privacidad, cookies, aviso legal, publicidad y página Prime Day.
- La cobertura sigue siendo parcial: títulos/nombres de productos y textos dinámicos arbitrarios no se traducen automáticamente; las páginas legales necesitan traducción completa y revisión jurídica por idioma.

## 2026-10-20 · Auditoría multilingüe: ampliación de cobertura y protección de datos de producto
- Ampliado el diccionario de la portada y canales verticales en catalán, inglés, chino simplificado y portugués: Price Watch, conversor de enlaces, tarjetas de canal, contacto y contenidos editoriales.
- Ampliadas etiquetas de catálogo/fichas: valoración, precio comprobado, precio actual/anterior, descuentos, filtros, resultados y estados de carga/error.
- Regla editorial: no traducir nombres de marcas, modelos, especificaciones ni títulos comerciales de productos; traducir únicamente la interfaz alrededor de ellos.
- Nueva versión de caché `20261020-audit2`; `node --check` correcto y JavaScript servido públicamente comprobado.
- Auditoría estática de portada, verticales y páginas legales detecta que la cobertura aún no puede declararse completa: quedan páginas legales, parte de los mensajes dinámicos y elementos que requieren comprobación en navegador real. No marcar multilingüe como terminado hasta ejecutar pruebas de cobertura por página/idioma y revisión visual.

## 2026-10-20 · Auditoría multilingüe: páginas públicas y protección de títulos de producto
- Inyectado el selector/script multilingüe en 2.288 páginas públicas adicionales que no lo cargaban (incluidas páginas de seguimiento de precios y subcategorías); se excluyeron las áreas internas/operativas. Copias originales en `superofertastech-web/.i18n-audit-backup-20261020-141530`.
- Ampliadas traducciones de interfaz y secciones legales/publicidad para catalán, inglés, chino simplificado y portugués.
- Cambio de seguridad lingüística: traducción exacta de nodos, sin sustitución parcial de frases. Esto evita alterar nombres de marca, modelos, especificaciones y títulos comerciales de los productos.
- Caché renovada a `20261020-audit4`; `node --check` y recurso público validados.
- Estado de auditoría: mejor cobertura de carga y traducción, pero aún requiere revisión visual y cobertura exhaustiva de mensajes de cada función. No marcar como terminado hasta validar las cadenas restantes de formularios/datos dinámicos y cada página legal.

## 2026-10-20 · Correcciones de auditoría multilingüe y tema oscuro
- Tema oscuro aplicado a fichas, marcos de imagen, categorías, información, estados de carga/error y pie de página en las páginas verticales; fondos y textos ajustados para mejorar el contraste.
- Diccionarios de catalán, inglés, chino y portugués ampliados para cadenas residuales identificadas en las capturas (categorías, textos informativos, contacto y etiquetas de oferta).
- Actualizado el versionado de caché del CSS y del script de idioma en las páginas HTML públicas para forzar la carga de los cambios.
- `node --check` validado en el script multilingüe y en la copia servida públicamente. Rutas públicas comprobadas: inicio, Tech, Hogar, Móviles, Mascotas, Moda y Deportes.
- La auditoría global continúa abierta: quedan por validar visualmente todos los componentes y cadenas dinámicas en los cinco idiomas; no declarar la traducción completa hasta terminar esa comprobación.


## 2026-10-20 · Auditoría de traducciones extendida
Se añadieron traducciones completas para textos institucionales, contacto, paneles informativos y páginas legales en catalán, inglés, chino y portugués. Se preservan títulos y nombres de productos, marcas y modelos. Referencia de caché: `language.js?v=20261020-legal-full1`. Copia previa del motor: `language.js.bak-legal-completion-20261020-185509`. Páginas actualizadas: 2302.


## 2026-10-21 · Recuperación del canal Móviles y captación AliExpress
- Ampliadas las consultas del escáner de Móviles con términos de teléfonos, Xiaomi, Redmi y POCO; consulta principal de AliExpress cambiada a `telefonos moviles`.
- Aumentado el límite de candidatos de 5 a 15 para ampliar el conjunto evaluado antes de selección.
- Filtro específico para AliExpress sin histórico: descuento mínimo 12 %, valoración 4,0 y 10 reseñas; Amazon mantiene sus requisitos anteriores. Relevancia de AliExpress para móviles: 60 en pase estricto y 50 en respaldo.
- Copias de seguridad creadas para `mobile_scanner.py`, `mobile_channel.py`, `sources/aliexpress.py` y `aliexpress_classifier.py` con sufijo `bak-mobile-aliexpress-expansion-20261021`.
- `test_mobile_filters.py`: 12 pruebas superadas; compilación Python correcta. Escaneo real de validación iniciado en modo de búsqueda/selección, sin publicación de mensajes.
- Pendiente de confirmar el resultado final del escaneo y que la selección genere ofertas publicables. Amazon sigue bajo circuito de protección por HTTP 503; no se desactivó.

## 2026-10-21 · Ajuste de filtros de Móviles AliExpress
- Umbral de relevancia para candidatos AliExpress reducido a 50 en el selector, manteniendo la clasificación obligatoria como smartphone o accesorio permitido y los bloqueos de accesorios.
- Para móviles AliExpress sin histórico: descuento anunciado mínimo 7 %, valoración mínima 4,0/5 y al menos 10 reseñas. El descuento anunciado no se presenta como ahorro real demostrado si no existe histórico.
- Umbral de captación de AliExpress reducido de 8 % a 7 % para no descartar antes de la selección ofertas que cumplen el nuevo baremo.
- Copias de seguridad creadas antes de modificar `mobile_channel.py` y `sources/aliexpress.py` (sufijo `bak_mobile_filters_20261021_102153`).
- Compilación Python correcta y `test_mobile_filters.py`: 12 pruebas superadas. Pendiente validar candidatos reales con el escáner en modo sin publicación y comprobar motivos de rechazo.
