# Telegram Bot V2 - Estado del Proyecto

> Documento de continuidad del proyecto.
> Actualizar al finalizar cada sesión importante.

---

## 1. Información general

- Proyecto: telegram-bot-v2
- Sistema: Raspberry Pi 4
- Usuario: juanjo
- Ruta: /home/juanjo/telegram-bot-v2
- Fecha de creación del documento: 2026-09-14

## 2. Objetivo del proyecto

Crear un sistema automatizado de búsqueda, selección y publicación
de ofertas de productos en un canal de Telegram.

El proyecto incluye integración con fuentes de productos,
clasificación de ofertas, histórico de precios y publicación
automatizada.

## 3. Estado actual

### Componentes identificados

- Integración con AliExpress.
- Autenticación y pruebas de API.
- Clasificación de productos y relevancia.
- Sistema de scoring y selección.
- Base de datos de productos.
- Histórico de precios.
- Recolección automática del histórico.
- Publicación en Telegram.
- Control de calidad de publicaciones.
- Redireccionador de enlaces.
- Sistema de ejecución automática.
- Pruebas automatizadas.

### Estado de Telegram

- Bot de Telegram en desarrollo.
- Publicación de ofertas implementada.
- Funciones de publicación y envío existentes.
- Pendiente documentar el estado exacto de producción.

### Estado del histórico

- Base de datos: data/ofertas.db
- Tablas conocidas:
  - products
  - price_history
- Se ha comprobado el estado del histórico durante la sesión
  del 14/09/2026.

## 4. Archivos principales

### AliExpress

- aliexpress.py
- aliexpress_advanced_patch/
- aliexpress_classifier.py
- aliexpress_oauth_server.py
- catalog.py
- patch_sources_aliexpress.py

### Motor de ofertas

- scanner.py
- scoring.py
- selection.py
- dedupe.py
- models.py
- database.py

### Histórico

- history.py
- history_collector.py
- history_report.py
- registrar_g502_historico.py
- run_history_scan.sh
- install_history_cron.sh
- README_history.md

### Telegram

- telegram_sender.py
- telegram_publisher.py
- telegram_copy.py
- publish_one_real.py
- run_publish.py

### Automatización

- auto_runner.py
- run_auto.sh
- publication_guard.py

### Configuración

- config.py
- .env
- .env.example
- requirements.txt

## 5. Base de datos

Archivo:

data/ofertas.db

Tablas confirmadas:

- products
- price_history

Pendiente documentar:
- Esquema completo.
- Número de productos.
- Número de registros históricos.
- Relaciones entre tablas.
- Última comprobación realizada.

## 6. Backups

El proyecto contiene copias de seguridad de varios archivos
importantes, incluyendo:

- auto_runner.py
- config.py
- models.py
- publication_guard.py
- telegram_publisher.py
- telegram_sender.py

No eliminar backups sin comprobar antes su utilidad.

## 7. Pendientes

- Documentar completamente la arquitectura.
- Documentar el flujo de ofertas.
- Documentar configuración de Telegram.
- Documentar integración con AliExpress.
- Documentar el sistema de histórico.
- Confirmar estado real de producción.
- Registrar pruebas realizadas y sus resultados.
- Definir el siguiente objetivo del proyecto.

## 8. Última sesión

Fecha: 2026-09-14

Trabajo realizado:
- Revisado el contenido del directorio del proyecto.
- Confirmada la existencia de README.md.
- Confirmada la ausencia de PROJECT_STATUS.md.
- Preparada la documentación inicial de continuidad.

## 9. Próximo paso

Completar este documento con el estado real del bot,
la arquitectura y las tareas pendientes de la última sesión.

---

## Monetización global centralizada · 2026-09-21

- Se auditó la monetización de AhorroScan como sistema global, no separada por Hogar/Tech.
- `monetization_engine.py` mantiene un ledger común en `data/monetization.db` y un informe `data/monetization.json`.
- El informe ahora separa tráfico por proyecto, ingresos por red/merchant y por proyecto, comisión de 30 días y acumulada, conversion proxy y comisión por clic.
- Se normaliza la atribución de proyectos para `tech`, `hogar`, Instagram, Telegram y Web.
- Los `clickref` AWIN con formato `hogar:merchant:external_id` o `tech:merchant:external_id` pueden recuperar automáticamente el `product_id` interno cuando existe en las BDs correspondientes.
- `status_report.py` y `monitor/project_metrics.py` ya exponen el estado global de monetización.
- Corrección importante: los 2 clics `instagram_hogar` detectados inicialmente eran tráfico sintético de pruebas (`AhorroScan-Test/Smoke`). El ledger de monetización ahora los excluye, junto con `curl` y `python-requests`.
- Situación cualificada al 2026-09-21: 0 clics comerciales cualificados desde el inicio de tráfico real, 0 transacciones y 0 € de comisión. Esto evita contaminar el aprendizaje con pruebas internas.
- El `status_report.py` conserva el recuento bruto histórico del redirector, mientras `monetization_engine.py` y `performance_engine.py` trabajan con clics cualificados.
- No se ha cambiado todavía el scoring por ingresos: primero se necesita muestra real suficiente.
- AWIN Hogar: Leroy Merlin, ManoMano, Conforama siguen Pending; BAUHAUS figura Rejected y Temu Not joined en el último estado local comprobado. AliExpress y Amazon continúan siendo las vías operativas actuales de Hogar.
- Backup MicroServer posterior a los cambios: snapshot `be63fb7d6c02`, generado 2026-09-21 15:28:15 +02:00, 626 archivos. Backup OK.
- Tests Tech ejecutados correctamente: 23 tests. Hogar: 168 tests, todos OK.

## Regla de continuidad

Al finalizar cada sesión:

1. Actualizar el estado.
2. Registrar los cambios realizados.
3. Escribir el próximo paso exacto.
4. No borrar información histórica útil.

---

## 10. Integración AliExpress V6.1

### Objetivo

Integrar el motor de relevancia V6.1 en
sources/aliexpress.py de V2.

### Familias de producción validadas

- Ratones.
- SSD NVMe.
- Monitores 4K.
- Teclados mecánicos.

### Reglas confirmadas

- Solo se activan familias validadas.
- Se utilizan consultas especializadas de producción.
- Se devuelven candidatos con relevancia >= 70.
- Se mantienen intactos SQLite, histórico, scoring,
  Quality Gate, selección y Telegram.
- No se modifica .env, data/ofertas.db ni el token OAuth.
- Se aplica detección conservadora de paneles/pantallas
  de sustitución.
- No se utiliza "teclado gaming mecanico" como query
  de producción debido a resultados excesivos de switches
  e interruptores.

### Comportamiento esperado

- mice: ratones reales arriba; adaptadores/dongles abajo.
- storage: SSD M.2/NVMe reales; carcasas/adaptadores fuera.
- monitors: monitores 4K reales; paneles/repuestos fuera.
- peripherals: teclados mecánicos reales; switches/keycaps fuera.
- El resto de categorías AliExpress se omite hasta validación.

### Pruebas documentadas

Prueba de integración live sin publicar Telegram:

python test_aliexpress_v61_integration.py

Prueba del pipeline completo sin publicación:

python dry_run.py

### Rollback

El backup de sources/aliexpress.py se genera con el patrón:

sources/aliexpress.py.pre-v61-YYYYMMDD-HHMMSS


---

## 11. Estado real del histórico y automatización

### Base de datos - comprobación 2026-09-14

Archivo:
data/ofertas.db

Registros confirmados:

- products: 774
- price_history: 2818

Estos valores corresponden a la comprobación realizada
mediante SQLite el 14/09/2026.

### Cron activo

Tareas confirmadas mediante crontab -l:

- Histórico:
  15 3 * * * run_history_scan.sh
  Ejecución diaria a las 03:15.

- Motor automático:
  0 */2 * * * run_auto.sh
  Ejecución cada 2 horas, en el minuto 0.

### Motor automático

Script de lanzamiento:
run_auto.sh

Script principal:
auto_runner.py

Entorno virtual:
venv/bin/activate

Protección contra ejecuciones simultáneas:
data/auto_runner.lock

Mecanismo:
flock -n

Log principal:
logs/auto_runner.log

Log del cron:
logs/cron.log

El script registra inicio, finalización y código de salida
de cada ejecución.


---

## 12. Motor automático y control de publicaciones

### auto_runner.py

Flujo confirmado:

1. Carga config.
2. Ejecuta scanner.run(return_publicable=True).
3. Obtiene ofertas publicables.
4. Si no hay ofertas, muestra estadísticas y termina.
5. Ejecuta telegram_publisher.publish() con force=False.
6. Clasifica resultados: published, dry_run, blocked y error.
7. Muestra resumen y estadísticas.
8. Devuelve código de salida:
   - 0: ejecución correcta.
   - 1: error fatal.
   - 2: errores de publicación.

### publication_guard.py

Tabla utilizada:
publications

Reglas confirmadas en el código:

- REPEAT_BLOCK_DAYS = 7
- REPEAT_PRICE_IMPROVEMENT_PCT = 10.0
- REPEAT_DISCOUNT_IMPROVEMENT_POINTS = 10.0
- MAX_PUBLICATIONS_PER_RUN: configuración, por defecto 5.
- MAX_PUBLICATIONS_PER_DAY: configuración, por defecto 10.

La función can_publish() comprueba:

1. Límite por ejecución.
2. Límite diario.
3. Duplicado reciente.

La función record_publication() registra una publicación
después de que Telegram confirme correctamente el envío.

Las publicaciones se guardan en la tabla publications.

### Pendiente de verificación

- Valores efectivos de MAX_PUBLICATIONS_PER_RUN.
- Valores efectivos de MAX_PUBLICATIONS_PER_DAY.
- Coherencia entre el resumen de auto_runner.py y los límites.
- Estado real de producción.
- Últimas pruebas de publicación.



## Optimización estructural - 2026-09-18

- El scanner admite `full` y `discovery`.
- El auto runner de cada 2 horas usa `discovery` con 12 consultas prioritarias.
- La recogida histórica diaria fuerza `SCAN_MODE=full` y conserva las 56 consultas del catálogo completo.
- La deduplicación de Tech usa `source + external_id`, URL canónica y título normalizado como fallback, sin fuzzy matching para fusionar.
- El filtro editorial bloquea términos típicos de accesorios/recambios antes de publicar.
- Telegram tiene reintentos limitados para errores transitorios 5xx y respeta `Retry-After` en 429.
- Se añadió `requirements-dev.txt` con pytest y `pytest.ini` para una suite segura sin ejecutar scripts de pruebas live durante la colección.
- Suite automática segura verificada: 9 pruebas pasando.
- Los scripts de integración/live existentes quedan para ejecución manual y no se ejecutan automáticamente con pytest.
- Estado real verificado de la BD: 959 productos, 4263 registros de `price_history` y 60 publicaciones.
- El producto de prueba que había quedado en la BD durante la primera comprobación del entorno fue eliminado; no quedan registros con `source=test` y `external_id=test-quality-v4`.
- Se añadió `status_report.py` para métricas operativas y futuras integraciones con el monitor.
- No se cambió la política de publicación real de Telegram.
- No se modificaron credenciales ni tokens.
- 2026-09-18: corregido `NameError: amazon_state` en `scanner.py`; validado con ejecución real en DRY_RUN, sin publicación.
- 2026-09-18: el redirector Tech de `127.0.0.1:8790` quedó levantado y protegido con reinicio automático mediante `@reboot` en cron; health comprobado OK.
- 2026-09-18: el watchdog ahora detecta un fallo posterior al último éxito del Auto Runner y evita marcarlo como Activo por un éxito antiguo.

- Se añadió `calibration_report.py`: analiza la distribución de scores y el volumen de clics antes de cualquier recalibración, sin cambiar pesos automáticamente.
- Verificación actual de calibración: 60 publicaciones con score y 5 clics registrados; muestra insuficiente para recalibrar con seguridad.
- La calibración queda preparada para ejecutarse cuando exista atribución de clics consistente y una muestra mayor.
- `status_report.py` expone métricas de BD, publicaciones y clics para futuras integraciones con el monitor.

## Cierre de optimización, resiliencia y observabilidad - 2026-09-18

- Amazon incorpora estado por consulta y el scanner aplica un corte de seguridad después de 3 fallos consecutivos.
- Cuando la salud de Amazon es degradada o no disponible, el auto runner filtra las ofertas Amazon del lote de publicación de esa ejecución.
- El scanner genera `data/source_health.json` después de cada escaneo real; todavía no se fuerza ningún escaneo manual para crear datos artificiales.
- AliExpress incorpora contadores de intentos, errores y errores de API para su health report.
- La atribución de clics queda calculada sobre `clicks_v2` contra la publicación activa correspondiente al momento del clic.
- `status_report.py` muestra health de fuentes y atribución; `calibration_report.py` usa clics atribuidos para decidir cuándo habrá muestra suficiente.
- Se añadió `project_metrics.py` al monitor central y un cron cada 10 minutos para alimentar el dashboard agregado.
- El dashboard del monitor muestra servicios, alertas y métricas de ambos proyectos.
- Los tests del core se ampliaron para cubrir los estados de salud de fuentes.
- Suite automática segura final de Tech: 13 pruebas pasando.
- Estado real de BD verificado: 959 productos, 4263 registros de `price_history`, 60 publicaciones y 51 productos publicados.
- Estado real de clics: 5 totales; 2 atribuidos a publicaciones y 3 sin atribución.
- La muestra sigue siendo insuficiente para recalibrar pesos automáticamente: 60 publicaciones con score y 2 clics atribuidos.
- No se cambiaron credenciales, tokens ni la política de publicación real.
- No se ejecutó manualmente un ciclo de producción Tech durante esta fase.

- El dashboard central de monitor incluye ahora métricas agregadas de ambos proyectos y la atribución de clics.
- `project_metrics.py` se ejecuta cada 10 minutos por cron y no modifica ninguna base de datos de los proyectos.
- Verificación estática final: compilación Python y validación de JavaScript correctas.

## Continuidad y operación - 2026-09-18 (fase posterior)
- El Auto Runner real sigue operativo y en la última ejecución registrada publicó 3 ofertas correctamente; el acumulado de publicaciones llegó a 63.
- La selección mantiene el embudo ampliado: hasta 2 por categoría y determinados INTERESANTE de alta confianza.
- El redirector v3 queda integrado en Telegram Tech mediante `get_or_create_product_link`.
- Los 5 enlaces legacy existentes de `links_v2` fueron migrados de forma compatible a `links_v3`, conservando sus códigos y destinos.
- `link_manager.py` ahora materializa también el registro v3 cuando reutiliza un enlace legacy.
- Se añadió cobertura de tests para el enlace trackeable v3.
- Suite segura automática actual: 15 pruebas pasando.
- `project_metrics.py` cuenta ahora clics v2 + v3 y muestra clics atribuidos y CTR atribuido.
- Se corrigió una incidencia en la atribución v3 entre los alias de SQLite de Tech/Hogar.
- El dashboard de métricas muestra publicaciones, clics atribuidos, CTR y enlaces trackeables por proyecto.
- Se creó un esquema de seguimiento compatible con Hogar mediante `publications.product_id`.
- No se cambiaron límites ni credenciales de Telegram durante esta fase.
- El backup Restic remoto ya contiene un segundo snapshot posterior a los cambios y la restauración de los ficheros críticos fue probada correctamente.
- El repositorio Restic se mantiene en el MicroServer mediante SFTP y cifrado.
- Backup diario programado: 04:45.
- Mantenimiento Restic programado: domingos 05:30.
- Mantenimiento de logs programado: diario 05:45.

## Cierre de fase - 2026-09-18
- Suite segura de Tech verificada tras las mejoras: 15 pruebas pasando.
- Tracking v3 y métricas de clics/CTR verificados sin generar clics artificiales.
- El dashboard de métricas muestra clics atribuidos, CTR y enlaces por proyecto.
- Backup Restic remoto y restore de prueba operativos.

## Seguimiento tracking v3 y backup - 2026-09-18 (continuación)
- Antes de continuar con la validación se ejecutó el backup Restic al MicroServer.
- Nuevo snapshot remoto: 7f7f27df.
- Backup incremental completado correctamente; 453 archivos procesados y estado persistente OK.
- Se comprobó que el redirector en 127.0.0.1:8790 estaba ejecutando una instancia antigua iniciada antes de la modificación de app.py.
- Se reinició de forma segura la instancia antigua y quedó cargada la lógica v3 actual.
- La prueba v3 de redirección devolvió HTTP 302 y registró el clic en clicks_v3; el 404 observado inicialmente era el destino de prueba de example.com al seguir automáticamente el 302.
- El enlace v3 de prueba y sus clics sintéticos fueron eliminados después de la validación para no contaminar las métricas.
- Se verificó que links_v3 mantiene 5 enlaces Tech compatibles con los enlaces legacy existentes.
- project_metrics.py ya contabiliza clicks_v2 + clicks_v3 y separa Tech/Hogar; ejecución correcta.
- /metrics/ responde HTTP 200 tanto localmente como a través de https://ahorroscan.es/metrics/.
- Estado real actual de Tech: 968 productos, 4291 price_history, 63 publicaciones, 53 productos publicados; 5 clics, 2 atribuidos y 3 no atribuidos.
- Suite segura de Tech verificada de nuevo: 15 pruebas pasando.
- No se realizaron publicaciones manuales ni se modificaron datos históricos de Tech.


## Hardening Amazon frente a HTTP 503 - 2026-09-18
- Revisado el incidente de las 20:00: 5 respuestas HTTP 503 de 12 consultas Amazon.
- Se añadió reintento controlado para 429, 500, 502, 503 y 504, y para respuestas detectadas como bloqueadas.
- Máximo de 3 intentos por consulta; los reintentos rotan User-Agent y usan backoff aleatorio 4-7 s, después 8-14 s, respetando Retry-After cuando existe y con tope de 30 s.
- Se reforzaron las cabeceras de búsqueda y se aumentó el espaciado normal entre consultas a 2,5-4,5 s.
- Una consulta que se recupera tras un 503 ya no cuenta como fallo para la salud de Amazon; el estado sigue siendo OK y queda registrado el número de reintentos.
- Una consulta que agota los reintentos sigue registrándose como fallo para no ocultar una incidencia persistente.
- Se añadieron pruebas automatizadas para recuperación tras 503, agotamiento de reintentos y metadatos de reintentos.
- Suite completa de Tech verificada después del cambio: 15 pruebas pasando.
- Prueba controlada de una consulta real movil 5g: respuesta HTTP 200 en el primer intento; no se escribió en la BD.
- Backup posterior al cambio realizado correctamente. Último snapshot: f4eec27c.
- No se modificaron credenciales ni la política de publicación.

## Diversificación editorial - 2026-09-19
- El descubrimiento automático de Tech pasa de 12 a 21 categorías por ejecución, manteniendo el escaneo histórico diario completo en 56 consultas.
- Se incorporó una preferencia de categoría no publicada en las últimas 18 horas para evitar que el mismo tipo de producto domine varias ejecuciones seguidas.
- El límite de seguridad de máximo 2 publicaciones por categoría y los límites globales de publicación no se han eliminado.
- Las pruebas completas de Tech siguen pasando tras el cambio.
- No se ejecutó una publicación real de Tech durante esta modificación.
- Backup final de esta sesión: el último snapshot Restic confirmado sigue siendo 482b27a0 (19:10). Dos intentos posteriores a las 19:20 y 19:22 fallaron porque el MicroServer 192.168.1.150 no era alcanzable por SSH (No route to host). No se alteró el repositorio ni se forzaron cambios de red.

## Cumplimiento Amazon y tracking - 2026-09-19
- Auditoría externa realizada contra las políticas actuales de Amazon Afiliados España, actualizadas el 14/04/2026.
- Se detectó un riesgo de cumplimiento en el uso del redirector interno para enlaces Amazon: Amazon exige Enlaces Especiales accesibles directamente y excluye compras atribuidas mediante un Enlace de Redirección.
- Telegram Tech ahora envía enlaces Amazon directamente a la URL etiquetada con tag=; AliExpress y otras fuentes conservan el redirector v3 para tracking interno.
- Se añadió cobertura de prueba para Amazon directo y se mantuvo la ruta trackeable para AliExpress.
- La suite completa de Tech queda en 16 pruebas pasando. La suite completa de Hogar queda en 165 pruebas pasando.
- Se añadió la identificación pública de AhorroScan como asociado de Amazon en la portada, Tech, Hogar y aviso legal. Se corrigió además el placeholder de email de contacto en Privacidad.
- No se modificaron credenciales, tokens ni la política de publicación real.

## Verificación operativa - 2026-09-19
- RasPi4 y MicroServer online.
- Redirector local: 127.0.0.1:8790/health devuelve HTTP 200; Nginx activo.
- Health de fuentes Tech: Amazon OK (12/12 consultas, 0 fallos) y AliExpress OK (13/13, 0 errores API) en el último health report disponible.
- Backup Restic al MicroServer ejecutado antes de esta fase y después de los cambios: último snapshot verificado e673a98e, 479 archivos procesados, estado OK.
- El backup USB de Hogar continúa con alerta: el último éxito registrado es 18/09 04:15. La ejecución manual actual no pudo crear la copia porque /mnt/ahorroscan-backup no está montado para el usuario; el USB aparece montado por devmon en /media/devmon/AHOROSCABKP, pero ese punto no es accesible al proceso actual. No se ha forzado ningún cambio de permisos ni de montaje.

## Pendientes manuales de producción
- Comprobar en Amazon Afiliados > Configuración de la cuenta > Editar lista de sitios web que https://ahorroscan.es/ y las superficies que realmente vayan a usar enlaces Amazon estén declaradas.
- Confirmar en la cuenta el estado de aceptación/revisión de Afiliados antes de considerar cerrada la parte de cumplimiento.
- Resolver el montaje/permiso del USB de backup Hogar para recuperar la copia local programada.
- No activar HOGAR_TELEGRAM_DRY_RUN=0 ni publicaciones reales de Hogar hasta contar con las aprobaciones/feed y autorización explícita.

## 2026-09-19 - Descubrimiento agresivo Centro de Anuncios

- AliExpress Tech incorpora descubrimiento masivo desde aliexpress.affiliate.hotproduct.query y pools dinamicos de aliexpress.affiliate.featuredpromo.products.get.
- Se cachea featuredpromo.get durante 6 horas para descubrir promociones actuales sin consultar la lista en cada ciclo.
- Centro Tech: hasta 60 candidatas por ciclo, con filtros de accesorios/repuestos y clasificacion por familias.
- Limites Tech: MAX_PUBLICATIONS_PER_RUN=8, MAX_PUBLICATIONS_PER_DAY=24, MAX_PRODUCTS_PER_QUERY=4.
- Seleccion Tech: hasta 8 ofertas y maximo 1 por categoria para aumentar variedad.
- AliExpress Hogar incorpora Centro de Anuncios con pools de hogar, cocina, jardin, herramientas, iluminacion, muebles, etc.
- Hogar: HOGAR_TELEGRAM_MAX_PER_RUN=5, HOGAR_TELEGRAM_MAX_PER_DAY=20.
- Cron Hogar pasa de cada 6h a cada 2h, a las xx:15, para acercarlo al ritmo de Tech.
- Tests: Tech y Hogar pasan completos tras los cambios.
- Hogar continua en modo real HOGAR_TELEGRAM_DRY_RUN=0, segun la configuracion actual.


## Verificacion final - 2026-09-19 23:23
- Suite Tech: 16 pruebas pasando.
- Suite Hogar: 165 pruebas pasando.
- Hogar cron confirmado: cada 2 horas, minuto 15.
- Backup MicroServer completado correctamente. Snapshot mas reciente: b8a41a139018 (541 archivos, 12.8 MiB).
- Configuracion de publicacion real Tech: 8 por ejecucion / 24 por dia.
- Configuracion de publicacion real Hogar: 5 por ejecucion / 20 por dia.


## Prueba de publicacion Centro de Anuncios - 2026-09-19 23:43
- Ejecucion real completa de Tech con la nueva version.
- 103 candidatas encontradas: 72 Amazon + 31 AliExpress; 101 validas tras duplicados.
- Centro de Anuncios Tech aporto 7 candidatas filtradas.
- El selector final dejo 1 oferta publicable por las reglas actuales.
- Publicada correctamente en Telegram: AliExpress, producto 1005005977110025, message_id 489, publication_id 86.
- Limite diario ahora 24; contador tras la prueba: 8/24.
- La prueba confirma que el cuello de botella ya no es el descubrimiento, sino la elegibilidad/rotacion final: varias ofertas de AliExpress eran buenas candidatas pero quedaron fuera por reseñas, categoria de riesgo o por la regla de maximo 1 categoria.

## 2026-09-20 - Selector 2 plazas por categoria + Centro de Ofertas Amazon

- Se rediseño el selector Tech para que la diversidad sea una preferencia y no un bloqueo absoluto.
- Pase 1: garantiza una oferta por categoria.
- Pase 2: rellena las plazas restantes por score y permite una segunda oferta de la misma categoria cuando sigue siendo competitiva.
- Limite por categoria: 2; limite por ejecucion: 8; limite diario: 24.
- Se mantiene la proteccion contra duplicados recientes, minimo de descuento, rating/reseñas y bloqueos de accesorios/repuestos.
- Prueba unitaria directa: con 3 ofertas de una categoria y varias de otras, el selector publico 2 de la categoria dominante y utilizo las plazas restantes para diversidad.

### Auditoria Amazon

- La investigacion de la documentacion oficial confirma que Amazon no ofrece un equivalente 1:1 al Centro de Anuncios de AliExpress como feed global de productos promocionados.
- La via oficial actual es Creators API, sucesora de PA-API 5. SearchItems permite filtrar por minSavingPercent, ordenar resultados y solicitar OffersV2.dealDetails, incluyendo ofertas Lightning Deal. La API devuelve hasta 10 items por consulta y requiere credenciales de Creators API + Partner Tag de amazon.es.
- Como segunda via inmediata, Amazon.es expone un filtro vivo de ofertas en sus resultados de busqueda. El sistema ahora descubre dinamicamente el identificador p_n_deal_type del marketplace, sin hardcodearlo, y lanza una bateria adicional de consultas tecnologicas contra ese filtro.
- Nuevo Centro de Ofertas Amazon: hasta 60 candidatas adicionales por ciclo, deduplicadas y enviadas al mismo scoring/guardas que el resto del pipeline.
- Prueba real del Centro Amazon: 12 candidatas obtenidas en la primera prueba, con descuentos observados de hasta ~69%, incluyendo portatiles, teclados, almacenamiento y audio.
- El centro filtra un minimo del 12% de descuento y aplica controles basicos de rating/reseñas cuando Amazon los proporciona. El selector final sigue siendo la barrera de calidad.
- Se deja preparada la arquitectura para una futura ruta oficial Creators API en cuanto existan credenciales; no se han inventado credenciales ni se ha alterado el .env con secretos.
- Suite Tech: 16 pruebas pasando antes de la prueba de escaneo completo.
- El escaneo completo de previsualizacion se inicio pero se detuvo para no seguir generando carga sobre Amazon mientras habia respuestas 503 transitorias. No se hizo ninguna publicacion adicional con esa previsualizacion.

## 2026-09-20 - Correccion enlaces publicos AhorroScan Hogar

- Incidencia detectada en Telegram Hogar: los botones AliExpress estaban mostrando https://raspi4.tail8794f8.ts.net/go/... porque redirector/link_manager.py tenia esa URL como PUBLIC_BASE_URL por defecto.
- Se cambio la base publica de tracking no-Amazon a https://ahorroscan.es/go.
- Se publico /go/ en el Nginx de la web AhorroScan y se conecta internamente al redirector 172.24.0.1:8790.
- El redirector ahora escucha en 172.24.0.1:8790, no en todas las interfaces, manteniendo el servicio accesible para el proxy web sin exponer directamente el puerto 8790 a Internet.
- El enlace Hogar existente de la captura (lsrxrwi0, producto 130) queda servido como https://ahorroscan.es/go/lsrxrwi0 y devuelve HTTP 302 al enlace de afiliado de AliExpress.
- Se actualizaron los botones de las 4 publicaciones Hogar AliExpress existentes: mensajes Telegram 5, 6, 8 y 9. Las publicaciones Amazon no se tocaron y mantienen enlace directo.
- Prueba publica realizada y eliminada la fila de click sintetico para no contaminar las metricas. Los clicks reales previos del enlace se conservaron.
- Se cambio el arranque @reboot del redirector para esperar 30 s y dar tiempo al bridge Docker a estar disponible antes de enlazar 172.24.0.1:8790.
- Suite Hogar: 165 pruebas pasando.
- Verificacion de compilacion del redirector: OK.


## 2026-09-20 - Auditoria enlaces Tech + endurecimiento de canales

- Incidencia replicada en Telegram Tech: las publicaciones AliExpress antiguas conservaban botones generados con el dominio Tailscale anterior aunque el generador ya usaba ahorroscan.es.
- Se migraron/verificaron las 13 publicaciones Tech AliExpress existentes (mensajes 409, 412, 419, 433, 434, 437, 450, 454, 465, 466, 471, 474 y 489) a botones https://ahorroscan.es/go/....
- El problema no afectaba a Amazon: sus botones siguen siendo enlaces directos de afiliado.
- Se verificaron todos los enlaces de tracking almacenados: 20 Tech + 4 Hogar, todos responden HTTP 302 y aterrizan en Amazon.es o AliExpress.
- Durante la migracion masiva Telegram aplico un 429 temporal; la migracion se completo respetando el ritmo y termino 13/13 sin fallos.
- Tech: se endurecio el manejo de Retry-After de Telegram para no recortar esperas indicadas por la API.
- Hogar: se anadio una pausa de 1,2 s entre publicaciones del mismo ciclo y tambien se respeta exactamente Retry-After ante 429.
- Se auditaron cron, Docker, salud de fuentes, bases de datos, redirector y estado de produccion. Sin errores activos en los canales.

## 2026-09-20 - Correccion backup USB Hogar

- El watchdog detecto un fallo real: el USB de backup Hogar llevaba ~47 h sin un OK.
- Causa: el sistema habia automontado /dev/sda1 bajo /media/devmon/AHOROSCABKP con permisos que impedian al usuario juanjo escribir, mientras el script esperaba /mnt/ahorroscan-backup.
- Se hizo el montaje persistente por UUID 380E-D36C en /mnt/ahorroscan-backup con uid/gid de juanjo y nofail.
- El script backup_to_usb.sh ahora detecta tambien el montaje alternativo y mueve el lock al directorio de logs para evitar problemas de permisos en VFAT.
- Backup manual ejecutado correctamente el 20/09/2026 a las 03:18, con SHA256 verificado y copia creada.
- El watchdog quedo recuperado: active_count=0.
- Suite Tech: 16 pruebas pasando. Suite Hogar: 165 pruebas pasando.

## 2026-09-20 - Descubrimiento adaptativo por tendencias + móviles/monitores

- Se detectó que Tech estaba infrarrepresentando smartphones y monitores. El motivo era doble: las consultas AliExpress `movil 5g` y `monitor 27 144hz` estaban sin familia productiva validada, y el escaneo automático no tenía todavía un perfil de tendencias que reforzara categorías calientes.
- Se añadieron familias AliExpress `smartphone_5g` y `monitor_gaming`, con filtros específicos contra fundas, repuestos, soportes y otros accesorios.
- Se eliminó la desactivación de `monitor 27 144hz` y se añadieron consultas de producción para móviles y monitores.
- Pruebas reales: AliExpress devuelve teléfonos 5G y monitores gaming/productividad; Amazon devuelve móviles 5G y monitores 24/27/32 pulgadas con descuentos y volumen de reseñas suficientes en varios candidatos.
- Nuevo `trend_engine.py`: cada 6 horas consulta el Centro de Anuncios de AliExpress y el Centro de Ofertas de Amazon y genera `data/trends_tech.json`.
- La señal Tech pondera especialmente el volumen reciente `lastest_volume` de AliExpress y usa presencia en ofertas, descuento, rating y reseñas de Amazon como señal secundaria.
- El discovery automático usa el perfil para ordenar categorías y añadir una segunda consulta a las categorías calientes. Smartphones y monitores quedan además como categorías estratégicas que nunca pierden su segunda consulta por una lectura puntual de tendencias.
- El escaneo histórico diario sigue usando las 56 consultas completas. Solo el ciclo automático de publicación usa `SCAN_MODE=discovery`.
- Nuevo `trend_engine_hogar.py`: cada 6 horas analiza el Centro de Anuncios de AliExpress Hogar y genera `data/trends_hogar.json`.
- Hogar mantiene una primera pasada diversa y, con `HOGAR_TREND_ADAPTIVE=1`, puede usar una segunda plaza para hasta las categorías con tendencia fuerte, sin convertir el canal en una monocultura de la misma familia.
- Cron añadidos: Tech a los minutos 45 cada 6 horas y Hogar a los minutos 50 cada 6 horas.
- Suite Tech: 16 pruebas pasando. Suite Hogar: 165 pruebas pasando.


## 2026-09-20 - AhorroScan central + feedback loop

- Nuevo canal central creado: @ahorroscan (chat_id configurado: -1004335220917).
- @Superofertastech_bot añadido como administrador con gestión de mensajes.
- Nuevo `aggregator.py`: reúne publicaciones recientes de Tech + Hogar, deduplica, puntúa y selecciona las mejores ofertas.
- Score global combina score original, clics propios, descuento, rating, reseñas y frescura.
- Control de diversidad: una oferta por categoría en primera pasada y máximo dos por categoría.
- Límite central: 6 por ejecución, 12 por día.
- Ventana de agregación: 7 días.
- Tracking central usa proyecto `central` en el redirector existente; Amazon conserva enlace directo.
- Primera publicación real en @ahorroscan completada: 6 ofertas, mensajes Telegram 3-8, sin errores.
- Nuevo `performance_engine.py`: genera `data/performance.json` con rendimiento por producto, categoría, proyecto y fuente.
- Métrica inicial observada: Tech 84 publicaciones / 46 clics; Hogar 5 publicaciones / 7 clics en ventana de 30 días.
- Tests `test_aggregator.py`: 3/3 pasados.
- `aggregator.py` y `performance_engine.py` compilan correctamente.
- Backup previo guardado como `.env.bak-before-central-20260920`.


---

## 2026-09-21 · Continuidad AhorroScan / Instagram

### Estado de esta sesión
- AhorroScan se mantiene como marca paraguas multicanal. No limitar el mensaje a Tech + Hogar.
- Mensaje principal de la landing Instagram: “Escaneamos miles de oportunidades. Tú solo ves las que merecen la pena.”
- Landing: /home/juanjo/superofertastech-web/instagram/index.html
- Generador: /home/juanjo/superofertastech-web/generate_instagram_page.py
- Landing pública: https://ahorroscan.es/instagram/
- Landing comprobada HTTP 200.
- Landing genera 12 ofertas automáticamente.
- Se eliminó el cálculo artificial de “precio normal” en la landing. No mostrar precio tachado salvo que exista precio de referencia explícito de la fuente.
- La landing ahora presenta etiquetas legibles: Wearables, Limpieza, Ratones, Smartphones, Hogar inteligente, Audio, Iluminación.
- analytics.js en /home/juanjo/superofertastech-web/assets/js/analytics.js registra en GA4 store, category y project desde data-source, data-category y data-project.
- Landing backup realizado.

### Instagram producción
- Cuenta: @ahorroscan
- Instagram User ID: 17841430634433765
- Graph API: https://graph.instagram.com/v26.0
- Publicaciones reales existentes: 6 PUBLISHED.
- Automatización de ofertas: /home/juanjo/telegram-bot-v2/instagram_auto.py
- Cron: 35 */4 * * * cd /home/juanjo/telegram-bot-v2 && venv/bin/python instagram_auto.py --publish
- Límite actual: 1 oferta por ejecución, 4 ofertas/día.
- Se corrigió el error transitorio de Meta “Media ID is not available” mediante reintentos.
- Se corrigió el HTML literal en captions.
- CTA actual: “🔗 Oferta: enlace en la bio → ahorroscan.es/instagram/”
- Se eliminó de las captions el precio normal reconstruido matemáticamente.

### Contenido editorial Instagram
- Nuevo generador: /home/juanjo/telegram-bot-v2/instagram_content_auto.py
- Pillow instalado en venv.
- Genera imagen vertical 1080x1350 y caption para formato top3.
- Salida pública: /home/juanjo/superofertastech-web/instagram/generated/
- URL pública: https://ahorroscan.es/instagram/generated/<archivo>.jpg
- Primer arte generado y comprobado HTTP 200: top3_20260921_085004.jpg
- El generador crea DB: /home/juanjo/telegram-bot-v2/data/instagram_content.db
- Tabla: editorial_publications
- Campos: content_type, image_path, public_url, caption, status, media_id, generated_at, published_at, impressions, reach, likes, comments, shares, saves.
- El generador registra cada pieza como GENERATED.
- Todavía NO se ha conectado la publicación automática de top3 a Instagram. Próximo paso: añadir publicación Graph API, registrar media_id, status PUBLISHED y published_at, con límite editorial independiente de las ofertas.
- Las publicaciones editoriales no deben consumir el límite de ofertas individuales.
- Próximo objetivo: medir rendimiento editorial y comparar content_type con publicaciones de ofertas.

### Métricas actuales
- Instagram PUBLISHED: 6.
- Redirector trackable clicks últimos 30d: 4, todos instagram_hogar, producto 25. Muestra pequeña.
- Amazon: tracking mediante GA4 porque los enlaces permanecen directos.
- AliExpress: tracking mediante redirector + GA4 landing.
- Monetización real reiniciada con data/REAL_TRAFFIC_START.txt = 2026-09-20T21:24:59.585Z
- Actualmente no hay conversiones registradas.

### Integridad / confianza
- No inventar precios de referencia.
- No presentar cálculos derivados como “precio normal”.
- Mantener afiliación claramente indicada.
- Mantener CTA apuntando a la landing real.
- No publicar contenido editorial sin registrar tipo, estado y media_id.

### Infraestructura
- RasPi4 actual: 1e39820d-dcdb-4911-84c0-2e9861a6cb0e
- Microserver: 18d36e11-36cb-4a0e-97de-76e694075e77
- Tech: /home/juanjo/telegram-bot-v2
- Hogar: /home/juanjo/ahorroscan-hogar
- Web: /home/juanjo/superofertastech-web
- Backup: /home/juanjo/ahorroscan-backup/backup_to_microserver.sh
- Backup operativo y verificado.

### Regla de continuidad
Antes de modificar arquitectura o automatizaciones:
1. Leer este PROJECT_STATUS.md.
2. Revisar DB/logs/scripts reales.
3. Hacer cambios pequeños y reversibles.
4. Ejecutar pruebas.
5. Comprobar endpoint público si afecta a web.
6. Ejecutar backup.
7. Actualizar PROJECT_STATUS.md.

## 2026-09-21 · Publicación editorial Instagram conectada

- Creado instagram_editorial_publisher.py como publicador independiente del límite de ofertas.
- El flujo editorial usa estados GENERATED -> PUBLISHING -> PUBLISHED o FAILED.
- La tabla editorial añade container_id, attempts y error_message para trazabilidad.
- Se conserva content_type y se registra media_id y published_at al completar la publicación.
- Si existen varias piezas GENERATED, se conserva la más reciente y las anteriores pasan a SUPERSEDED.
- Se mantiene INSTAGRAM_EDITORIAL_MAX_PER_DAY=1 por defecto.
- El publicador incorpora lock local para impedir ejecuciones simultáneas.
- Antes de publicar comprueba que la URL pública devuelve una imagen HTTP 200.
- La cuenta se valida contra INSTAGRAM_USER_ID mediante /me.
- Se mantienen reintentos para el error transitorio "Media ID is not available".
- Publicación real validada el 2026-09-21: editorial id 2, type top3.
- Container ID: 18106845902021148.
- Media ID: 18422393944146905.
- Estado final: PUBLISHED.
- Publicada sin consumir INSTAGRAM_MAX_PER_RUN/MAX_PER_DAY de ofertas individuales.
- La pieza editorial id 1 quedó SUPERSEDED por ser anterior.
- Cron actual:
  - 11:45: genera contenido editorial.
  - 12:00: publica la pieza GENERATED.
- Log del publicador: logs/instagram-editorial-publish.log.
- La API Graph v26.0 responde correctamente para @ahorroscan.
- Imagen pública comprobada: HTTP 200, image/jpeg.
- Compilación de los scripts Instagram relevantes: OK.
- Suite Tech: 16 pruebas pasando.
- Suite Hogar: 168 pruebas pasando.
- Backup Restic posterior al trabajo: OK, 2026-09-21T13:18:01+02:00.
- No se modificaron credenciales ni la política de publicación de ofertas.

### Instagram Insights conectado · 2026-09-21

- Nuevo sincronizador: /home/juanjo/telegram-bot-v2/instagram_insights.py.
- Usa el endpoint /{media_id}/insights de Graph API v26.0.
- Métricas actuales verificadas en producción: views, reach, likes, comments, saved, shares y total_interactions.
- La API moderna ya no debe tratar `impressions` como métrica principal para publicaciones nuevas; se usa `views`.
- La tabla editorial añade views, total_interactions, insights_updated_at e insights_error, manteniendo las columnas históricas existentes.
- La publicación editorial id 2 / media_id 18422393944146905 fue sincronizada correctamente: actualmente todas las métricas devuelven 0, coherente con una publicación recién creada y sin interacción todavía.
- `performance_engine.py` incorpora `instagram_editorial` con agregados y desglose por content_type.
- `status_report.py` expone el bloque `instagram_editorial` para el monitor central.
- Cron Insights: cada 6 horas, minuto 20, con log en logs/instagram-insights.log.
- Tests Tech: 19 pruebas pasando, incluyendo 3 nuevas pruebas del parser de Insights.
- Tests Hogar: 168 pruebas pasando.
- No se cambiaron credenciales ni la política de publicación.

### Próximo objetivo Instagram

- Acumular suficiente histórico de Insights para comparar `content_type` y rendimiento real.
- Incorporar métricas editoriales al feedback loop sin recalibrar pesos con muestras pequeñas.
- Añadir, cuando haya suficiente volumen, señales como tasa de interacción por alcance y rendimiento por formato.
- Mantener separación entre rendimiento editorial y rendimiento de ofertas individuales.

## Ledger producto/canal + redirector · 2026-09-21

- Se añadió `click_attribution` en `data/monetization.db` como ledger normalizado: producto, proyecto, canal, merchant, categoría, external_id, publicación asociada, destino y estado de clic cualificado.
- `monetization.json` ahora expone `product_channel_ledger`, `clicks_by_channel`, `clicks_by_merchant`, `clicks_by_category` y cobertura del ledger.
- El redirector v3 conserva `channel` en `links_v3` y `clicks_v3`; los nuevos enlaces se crean por proyecto + canal para no mezclar atribución entre Telegram/Web/otros canales.
- Telegram Tech usa `telegram_tech`; Telegram Hogar usa `telegram_hogar`; el agregador central usa `telegram_central`.
- Los clics v3 históricos sin canal quedan como `unknown`, sin inventar atribución retroactiva.
- El watchdog del dashboard corregido: el redirector escucha deliberadamente en `172.24.0.1:8790` para el proxy web, por lo que comprobar `127.0.0.1:8790` era un falso negativo del monitor.
- Redirector verificado: health 200 en `172.24.0.1:8790` y enlace público `/go/` devuelve 302 hacia el destino de afiliación.
- Se reforzó el filtro de tráfico sintético para ignorar variantes de `AhorroScan/Ahoroscan` Test/Smoke, curl y python-requests.
- Estado cualificado actual: 0 clics comerciales, 0 transacciones, 0,00 €.
- Tests: Tech 24 passed; Hogar 168 passed; compilación de módulos modificados OK.

## Atribución de comisiones y AWIN · 2026-09-21

- El ledger de monetización ahora conserva `clickref`, `click_id`, método/confianza de atribución y fecha de atribución en `commissions`.
- Los `clickref` AWIN se descomponen en proyecto, merchant, external_id y canal cuando el formato lo permite.
- Se resuelve `external_id -> product_id` y se puede asociar una comisión al último clic cualificado compatible anterior a la venta.
- El informe añade `revenue_by_channel`, `revenue_by_product_channel`, `commission_attribution` y `attributed_transactions`.
- Se añadió normalización de merchants para comparar nombres como `Leroy Merlin` y `leroy-merlin` sin falsos negativos.
- Corrección importante: `affiliate_sync.py` ahora carga también las credenciales AWIN desde `/home/juanjo/ahorroscan-hogar/.env`.
- Prueba real de `affiliate_sync.py` contra AWIN completada correctamente el 2026-09-21: API respondió, 0 transacciones en la ventana consultada, 0 comisiones.
- No se modifica el scoring de productos con muestras pequeñas.

## GO LIVE · 2026-09-21 17:13 +02:00

- AhorroScan pasa oficialmente a **LIVE / PRODUCCIÓN**.
- Canales activos: Tech, Hogar, Telegram, Instagram y Web.
- Monetización activa: Amazon + AliExpress; AWIN integrado y operativo, con anunciantes pendientes/rechazados sin bloquear el lanzamiento.
- Redirector v3 operativo y monitorizado.
- Ledger producto/canal/merchant y atribución de comisiones activos.
- Cron de publicación y monetización activos.
- Primer ciclo manual de producción lanzado como validación del Go Live.
- No se modifica el scoring por falta de muestras comerciales.


## 2026-09-21 · Smartphones reforzados para Tech

- La familia `smartphones` ya existía en el proyecto, pero se auditó y reforzó para evitar contaminación por accesorios que mencionan teléfono/iPhone/Galaxy.
- AliExpress: `smartphone_5g` mantiene las consultas `movil 5g`, `smartphone 5g` e `iphone`, con Quality Gate existente; prueba real actual devolvió 3 candidatas terminales, aunque no aptas para publicación por rating/reseñas insuficientes.
- Centro de Anuncios AliExpress: `_catalog_category()` ahora evita clasificar como smartphone cargadores, soportes, fundas, protectores, cables, adaptadores y repuestos que solo mencionan el móvil objetivo.
- Amazon: las búsquedas de smartphones y el Centro de Ofertas pasan por un filtro específico de títulos para excluir accesorios.
- Selección final: se añadió una barrera independiente `smartphone_no_es_terminal` para impedir que una clasificación errónea de fuente pueda llegar a Telegram.
- Se añadieron pruebas de aceptación/rechazo de terminales y accesorios en `test_mobile_filters.py`.
- Suite Tech: 27 pruebas pasando; compilación de módulos modificados OK.
- La prueba de Amazon de hoy respondió HTTP 200 pero no devolvió candidatas con precio de referencia para `smartphone 5g`; el Centro de Ofertas devolvió 503 transitorio al descubrir el filtro y no se forzó más carga.
- No se publicó ninguna oferta durante esta validación.

## 2026-09-22 · Fase 2 iniciada · Preparación VPS

### 2026-09-22 · Endurecimiento del canal Tech

- Se detectaron dos publicaciones incorrectas en Tech: una lonchera de alimentos clasificada como `laptops` por la palabra "portátil" y un proyector navideño publicado antes de temporada.
- Se añadió una guarda de título para bloquear productos claramente ajenos a Tech aunque una categoría ambigua los haya clasificado mal.
- Se añadió una guarda estacional de publicación: productos con campañas futuras explícitas (Navidad, Nochevieja, San Valentín y Día del Padre/Madre) no llegan a Telegram antes de su ventana comercial.
- La campaña de Navidad queda abierta desde el 1 de noviembre, en lugar del 15 de noviembre, para dar margen a posibles retrasos de envío y asegurar que las compras internacionales puedan llegar a tiempo.
- AliExpress Centro de Anuncios también filtra estos falsos positivos antes de incorporarlos al scoring.
- Se añadieron pruebas de regresión para loncheras y productos navideños prematuros.
- Suite Tech completa: 27 pruebas pasando.
- Backups previos guardados como `selection.py.bak-before-tech-channel-guard-20260922`, `sources/aliexpress.py.bak-before-tech-channel-guard-20260922` y `catalog.py.bak-before-tech-channel-guard-20260922`.


- Se inició la segunda fase de infraestructura: migración de producción Raspberry Pi → VPS cloud.
- La Raspberry Pi continúa siendo producción y NO se ha cambiado DNS/Cloudflare.
- El MicroServer queda como backup/recuperación local y standby.
- Se creó `/home/juanjo/ahorroscan-backup/vps-migration/` con plan de migración y bootstrap Debian 13.
- Bootstrap preparado para instalar Docker, Restic, Git, hardening SSH/firewall y estructura de proyectos; no publica ni activa producción.
- Se revisaron candidatos actuales: OVHcloud VPS-2, IONOS Cloud Basic Cube M y Hetzner CPX32.
- Antes de contratar se debe verificar checkout, IVA español, IPv4, ubicación, backup, tráfico, renovación y cancelación.
- Regla de migración: staging primero, publicadores desactivados, smoke tests, backup VPS→MicroServer, ventana controlada y cambio Cloudflare al final.


## HA Publisher Lease · 2026-09-22

- Coordinación externa de publicación operativa mediante Cloudflare Worker + Durable Object: `ahorroscan-publisher-lease.ahorroscan-lease.workers.dev`.
- Política: VPS rank 1, Raspberry Pi rank 2, MicroServer rank 3; TTL 60 s; promoción diferida 0/20/40 s.
- El endpoint autenticado responde correctamente: VPS obtiene el lease y el endpoint /status confirma `holder=vps`, rank 1 y lease activo.
- Autenticación negativa verificada: credencial incorrecta devuelve HTTP 401.
- `ha_publish_guard.py` está integrado en Telegram e Instagram de Tech y exige simultáneamente nodo PRIMARY, publicación habilitada y lease válido.
- Estado verificado: VPS `telegram=True`, `instagram=True`; Raspberry y MicroServer `False` en ambos canales.
- Agente persistente configurado en VPS y Raspberry mediante systemd de usuario (`lease-agent.service`, `Restart=always`, habilitado en `default.target`).
- Agente persistente configurado en MicroServer mediante `ahorroscan-lease-agent.service` de sistema, habilitado y activo.
- MicroServer revisado tras el fallo previo de 403: `lease.env` existe, usa el mismo secreto configurado y el agente vuelve a ejecutar correctamente; permanece standby mientras VPS posee el lease.
- Se verificó que los tres nodos usan el mismo endpoint y el mismo secreto mediante huella SHA-256, sin exponer el secreto.
- El failover completo VPS→Raspberry ya había sido probado en la fase anterior; en esta sesión se revalidó el fencing y el estado de los tres nodos sin dejar ningún standby habilitado para publicar.
- Failback sigue siendo por expiración del lease, no preempción inmediata.
- Pendiente antes del cierre definitivo: rotar `LEASE_SECRET` y actualizarlo coordinadamente en Worker + tres nodos. No se ha hecho todavía para no dejar producción sin autenticación durante la rotación.
- No se activó ninguna publicación adicional durante esta verificación.

## 2026-09-23 Multicanal
- Arquitectura multicanal preparada: families.json, channels.json, channel_catalogs.json y channel_registry.py.
- Tech y Hogar siguen activos; 8 nuevos verticales están declarados planned y no publican.
- Creada landing comercial /publicidad/ y enlazada desde web principal.
- run_auto.sh usa ahora el healthcheck real del proyecto en lugar de /usr/bin/true.

## 2026-10-18 · Inventario maestro de requisitos

- Fuente de verdad funcional y registro de regresiones: `AhorroScan_MASTER_REQUIREMENTS.md`.
- Antes de cada modificación se debe actualizar el inventario, identificar regresiones posibles, probar los requisitos afectados y verificar producción cuando corresponda.
- Incidencia prioritaria identificada: parte del contenido de Halloween está bloqueado por filtros de Tech e Instagram, pese a la petición expresa de promocionarlo.
- No asumir que una programación está activa sin verificar el scheduler y una ejecución real.


## Actualización 2026-10-18 · Correcciones aplicadas
- **Halloween Tech:** se retiró el bloqueo de categoría global y se añadió una regla específica que solo acepta en Tech la categoría estacional cuando el título identifica electrónica/luz/proyector; disfraces siguen bloqueados. Pruebas de regresión añadidas.
- **Instagram editorial:** eliminado el bloqueo literal de la palabra Halloween en el generador editorial; se conservan bloqueos de elementos irrelevantes. El publicador principal ya no bloqueaba Halloween explícitamente.
- **Tech timer:** restaurado y habilitado con calendario cada dos horas. Próximo disparo comprobado por systemd: 16:00 UTC del 18/10/2026.
- **Price Watch promoción:** creado timer recurrente martes/jueves/domingo a las 19:00 Europe/Madrid. El script registra cada canal por fecha local para permitir recurrencia sin duplicar publicaciones el mismo día.
- **Resumen semanal:** copiado el generador a producción y creado timer domingo 14:00 Europe/Madrid. IMPORTANTE: el generador crea un borrador, no publica automáticamente en Telegram ni Instagram; esa integración queda pendiente, no se considera resuelta.
- **Validación:** pruebas Halloween 3/3; compilación Python y `bash -n run_auto.sh` correctos. La suite completa `test_selection.py` mantiene un fallo previo/no relacionado en `test_smartphone_high_confidence_can_enter_with_moderate_discount` (espera 1 producto y obtiene 0); requiere investigación separada.

## 2026-10-18 · Publicaciones Halloween lanzadas
- Telegram Hogar: 2 publicaciones confirmadas (mensajes 177 y 178).
- Telegram Tech: 1 publicación confirmada (mensaje 1165), solo iluminación LED relevante para el canal.
- Web Hogar: catálogo regenerado con artículos Halloween y precios/enlaces afiliados.
- Estado persistido para no duplicar estos envíos manuales: `data/halloween_manual_publications.json`.
- Pendiente confirmar el fin del escaneo Tech y verificar por separado Instagram/canal general.


## 2026-10-18 · AliExpress discovery expanded (no posts sent)
- Fixed discovery catalog so trend-driven queries complement rather than replace base searches.
- Added V6.3 routes for 19 missing Tech families; 61 discovery query pairs are generated and 55 are routed to AliExpress rules. Six generic audio/microphone queries remain intentionally unrouted pending specific rules.
- Read-only production API probe: 23 raw offers returned across 12 categories; several were noisy or lacked rating/review data, so no publication was attempted. Category-specific accessory guards were tightened.
- TEST full suite passes (36 tests). Production targeted discovery tests pass; the known legacy moderate-discount smartphone test remains failing.
- Next: validate brand/model-specific searches and count offers passing all production guards before applying broader selector changes or adapting other verticals.


## 2026-10-18 · Ampliación de búsquedas AliExpress por marca/modelo
- Añadidas consultas específicas por marcas y modelos de 16 familias Tech para ampliar el descubrimiento sin relajar filtros de calidad.
- Corregido el flujo de consultas: las búsquedas específicas `future_*` se pasan primero a la API y se complementan con consultas genéricas de respaldo; antes el catálogo las enumeraba, pero el conector no las ejecutaba.
- Cambios sincronizados con TEST. Pruebas específicas de descubrimiento, validación y clasificación pasan en ambos entornos; prueba nueva verifica el paso de consulta específica.
- Ninguna publicación enviada durante esta intervención. Pendiente medir ofertas que superan todos los filtros mediante consultas reales de solo lectura.
- Registro anotado también en `AhorroScan_MASTER_REQUIREMENTS.md`; no se encontró un archivo separado de lista de tareas hechas.


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
