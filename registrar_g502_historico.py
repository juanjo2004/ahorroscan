import sqlite3
from datetime import datetime, timezone

DB = "data/ofertas.db"

PRODUCT_ID = 8
SOURCE = "amazon"
EXTERNAL_ID = "B07GS6ZB7T"
TELEGRAM_MESSAGE_ID = 403

PRICE = 27.99
REFERENCE_PRICE = 59.99
DISCOUNT = (REFERENCE_PRICE - PRICE) / REFERENCE_PRICE * 100.0
SCORE = 68.54

print("=== REGISTRO DE PUBLICACIÓN REAL HISTÓRICA ===")

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

product = conn.execute(
    """
    SELECT *
    FROM products
    WHERE id = ?
      AND source = ?
      AND external_id = ?
    """,
    (PRODUCT_ID, SOURCE, EXTERNAL_ID),
).fetchone()

if product is None:
    conn.close()
    raise SystemExit("ERROR: no se encontró el producto G502.")

existing = conn.execute(
    """
    SELECT id
    FROM publications
    WHERE origin = 'tech'
      AND product_id = ?
      AND telegram_message_id = ?
    """,
    (PRODUCT_ID, TELEGRAM_MESSAGE_ID),
).fetchone()

if existing is not None:
    print(
        f"El registro ya existe. publication_id={existing['id']}"
    )
    conn.close()
    raise SystemExit(0)

published_at = datetime.now(timezone.utc).isoformat()

cur = conn.execute(
    """
    INSERT INTO publications (
        product_id,
        source,
        external_id,
        title,
        category,
        price,
        discount_pct,
        score,
        telegram_message_id,
        published_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    (
        PRODUCT_ID,
        SOURCE,
        EXTERNAL_ID,
        product["title"],
        product["category"],
        PRICE,
        DISCOUNT,
        SCORE,
        TELEGRAM_MESSAGE_ID,
        published_at,
    ),
)

publication_id = cur.lastrowid
conn.commit()

print()
print("Registro creado:")
print("  publication_id:", publication_id)
print("  product_id:", PRODUCT_ID)
print("  external_id:", EXTERNAL_ID)
print("  telegram_message_id:", TELEGRAM_MESSAGE_ID)
print(f"  precio: {PRICE:.2f} €")
print(f"  descuento: {DISCOUNT:.1f}%")
print(f"  score: {SCORE:.2f}")
print("  published_at:", published_at)

print()
print("=== VERIFICACIÓN ===")

row = conn.execute(
    """
    SELECT
        id,
        product_id,
        source,
        external_id,
        price,
        discount_pct,
        score,
        telegram_message_id,
        published_at
    FROM publications
    WHERE origin = 'tech'
      AND id = ?
    """,
    (publication_id,),
).fetchone()

for key in row.keys():
    print(f"  {key}: {row[key]}")

count = conn.execute(
    "SELECT COUNT(*) FROM publications WHERE origin='tech'"
).fetchone()[0]

print()
print("Total publicaciones registradas:", count)

conn.close()

print()
print("OK: PUBLICACIÓN REAL HISTÓRICA REGISTRADA")
