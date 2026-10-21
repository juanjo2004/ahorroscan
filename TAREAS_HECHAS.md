# AhorroScan · Tareas hechas

Registro persistente de cambios verificados. Última actualización: 2026-10-18.

## AliExpress / descubrimiento y calidad Tech
- [x] Corregir catálogo para combinar consultas dinámicas y catálogo base sin duplicados.
- [x] Añadir rutas de descubrimiento para familias Tech que no llegaban a reglas AliExpress.
- [x] Ampliar consultas por marca/modelo para tablets, portátiles, mini-PC, monitores, TV, networking, SSD, componentes, CPU, placas base, periféricos, smart home, wearables, gaming, power banks y proyectores.
- [x] Corregir el paso de consultas específicas desde catálogo al conector AliExpress.
- [x] Aislar consultas específicas de marca/modelo de los aliases genéricos cuando no coinciden con las consultas propias de la regla.
- [x] Añadir controles de coincidencia de marca/modelo en el clasificador.
- [x] Reforzar guardas contra accesorios, cargadores, adaptadores y repuestos presentados como producto principal.
- [x] Añadir pruebas de regresión para enrutado, aislamiento de consultas, marcas incorrectas y accesorios.
- [x] Validar compilación y pruebas dirigidas en producción y TEST.
- [x] Validar suite completa de TEST: 36 pruebas pasan antes del último ajuste de guardas.
- [x] Ejecutar búsquedas reales AliExpress en solo lectura, sin publicar. Confirmado que siguen llegando resultados ruidosos y muchos productos sin suficientes reseñas/valoración.
- [x] Repetir suite completa TEST después del último ajuste de guardas: 36 pruebas pasan.
- [x] Repetir muestra de búsquedas reales; se confirmó que el selector AliExpress devuelve accesorios/repuestos en algunas categorías y se añadieron guardas adicionales; queda pendiente una nueva muestra post-guardas.
- [x] Medir candidatos reales en el predicado editorial final: HONOR Pad X8a (score 60, pasa pase relajado; 64% descuento, 5.0/364 reseñas) y robot aspirador ABIR X9 (score 70, pasa pase estricto; 63% descuento, 4.67/205 reseñas). Esta comprobación no ejecuta deduplicación ni publica.

## Seguridad editorial
- [x] Mantener umbrales de descuento, valoración y reseñas; no rebajarlos para aumentar artificialmente el volumen.
- [x] No enviar publicaciones durante las pruebas de diagnóstico.

- [x] Detectar y corregir el techo de puntuación de familias `future_*` que impedía alcanzar el umbral relajado aunque hubiera producto válido.
- [x] Validar el predicado editorial final con dos candidatos reales y registrar score, descuento, rating, reseñas y guarda de categoría. La deduplicación y el envío siguen reservados al ciclo normal de publicación.


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
