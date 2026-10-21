from sources.aliexpress_hotproduct import query

KEYWORD = "nvme 1tb"
print(f"Probando AliExpress Hot Product Query con: '{KEYWORD}'")
products = query(KEYWORD, limit=3)
print(f"Productos recibidos: {len(products)}")

for idx, p in enumerate(products, 1):
    print(f"{idx}. {str(p.get('product_title') or '')[:100]}")
    print(
        "   id={id} | precio={price} EUR | original={original} EUR | descuento={discount}".format(
            id=p.get("product_id"),
            price=p.get("target_sale_price") or p.get("app_sale_price") or p.get("sale_price"),
            original=p.get("target_original_price") or p.get("original_price"),
            discount=p.get("discount"),
        )
    )
    print(f"   rating/valoración={p.get('evaluate_rate')} | ventas recientes={p.get('lastest_volume')}")
    print(f"   url={'OK' if p.get('product_detail_url') else 'NO'} | afiliado={'OK' if p.get('promotion_link') else 'NO'} | imagen={'OK' if p.get('product_main_image_url') else 'NO'}")

if not products:
    raise SystemExit(
        "ERROR: Hot Product Query no devolvió productos. Revisa el mensaje [ALIEXPRESS HOTPRODUCT] anterior."
    )

print("OK: Hot Product Query responde y devuelve productos")
