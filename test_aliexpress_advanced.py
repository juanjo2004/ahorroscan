from sources.aliexpress import buscar


KEYWORD = "nvme 1tb"

print(f"Probando AliExpress Affiliate Product Query con: '{KEYWORD}'")
offers = buscar(KEYWORD, limite=3, category="storage")
print(f"Productos recibidos: {len(offers)}")

for idx, offer in enumerate(offers, 1):
    print(f"{idx}. {offer.title[:90]}")
    print(f"   id={offer.external_id} | precio={offer.current_price} € | referencia={offer.reference_price} €")
    print(f"   rating={offer.rating} | reviews={offer.reviews}")
    print(f"   url={'OK' if offer.url else 'NO'} | afiliado={'OK' if offer.affiliate_url else 'NO'} | imagen={'OK' if offer.image_url else 'NO'}")

if not offers:
    raise SystemExit("ERROR: la API no devolvió productos. Revisa el mensaje [ALIEXPRESS] anterior.")

print("OK: consulta real de AliExpress y adaptación a Offer")
