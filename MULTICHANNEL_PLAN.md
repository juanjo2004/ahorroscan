# AhorroScan multicanal y multicomercio

## Objetivo
Escalar AhorroScan desde dos canales a una red de canales verticales sin duplicar el pipeline. Cada canal tendrá una familia, categorías, fuentes, reglas editoriales, límites y destinos propios.

## Canales actuales
- `tech` -> Tecnología -> activo
- `hogar` -> Hogar -> activo

## Próximos verticales preparados
- `moda`
- `belleza`
- `familia`
- `deporte`
- `mascotas`
- `automovil`
- `bricolaje`
- `viajes`

Están declarados como `planned` y no publican. Antes de activar cada uno hay que crear/configurar su canal Telegram, revisar fuentes/afiliación, reglas de calidad, branding y página web.

## Archivos de arquitectura
- `config/families.json`: familias y taxonomía.
- `config/channels.json`: estado y configuración de cada canal.
- `config/channel_catalogs.json`: consultas iniciales por familia/categoría.
- `channel_registry.py`: acceso centralizado al registro.

## Regla de escalado
No crear un bot independiente por canal. El pipeline debe ser común y parametrizable:

`fuentes -> normalización -> clasificación -> scoring -> quality gate -> selección por canal -> tracking -> publicación -> métricas -> monetización`

El canal decide qué categorías acepta y qué reglas aplica. Esto permitirá reutilizar afiliación, histórico de precios, tracking, dashboard y HA.

## Orden previsto
1. Monetizar Tech/Hogar.
2. Activar Moda.
3. Activar Belleza.
4. Activar Familia.
5. Activar Deporte.
6. Activar Mascotas.
7. Activar Automóvil.
8. Activar Bricolaje.
9. Activar Viajes.

La activación debe basarse en disponibilidad de fuentes y programas de afiliación, no simplemente en volumen de productos.
