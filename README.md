# AliExpress V6.1 integration patch

Integra el motor de relevancia V6.1 en `sources/aliexpress.py` de V2.

## V6.1
- Activa únicamente familias validadas: ratones, SSD NVMe, monitores 4K y teclados mecánicos.
- Usa consultas especializadas de producción.
- Devuelve solo candidatos con relevancia >= 70.
- Mantiene intactos SQLite, histórico, scoring, Quality Gate, selección y Telegram.
- No modifica `.env`, `data/ofertas.db` ni el token OAuth.
- Añade detección conservadora de paneles/pantallas de sustitución.
- No usa `teclado gaming mecanico` como query de producción porque devuelve demasiados switches/interruptores.
- Hace backup automático de `sources/aliexpress.py` antes de sustituirlo.

## Instalar

1. Copia `telegram-bot-v2-aliexpress-v61-integration.zip` a la Raspberry.
2. Ejecuta:

```bash
cd /home/juanjo/telegram-bot-v2
unzip -o ~/telegram-bot-v2-aliexpress-v61-integration.zip -d /tmp/ali-v61
cd /tmp/ali-v61/aliexpress_v61_patch
chmod +x apply_aliexpress_v61.sh
./apply_aliexpress_v61.sh
```

El script copia automáticamente los archivos a V2 y crea un backup fechado.

## Prueba live, sin publicar Telegram

```bash
cd /home/juanjo/telegram-bot-v2
source venv/bin/activate
python test_aliexpress_v61_integration.py
```

Después, para la prueba del pipeline completo:

```bash
python dry_run.py
```

`dry_run.py` no publica en Telegram.

## Qué esperamos ver

- `mice`: ratones reales arriba, adaptadores/dongles abajo.
- `storage`: SSD M.2/NVMe reales, carcasas/adaptadores fuera.
- `monitors`: monitores 4K reales; paneles/repuestos fuera.
- `peripherals` + consulta de teclado: teclados mecánicos reales; switches/keycaps fuera.
- El resto de categorías AliExpress se omite por ahora de manera segura hasta validarlas.

## Rollback

El backup generado por el script se llama:

```text
sources/aliexpress.py.pre-v61-YYYYMMDD-HHMMSS
```

Para volver atrás:

```bash
cp sources/aliexpress.py.pre-v61-YYYYMMDD-HHMMSS sources/aliexpress.py
rm -f aliexpress_classifier.py test_aliexpress_v61_integration.py
```

