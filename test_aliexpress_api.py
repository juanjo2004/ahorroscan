from sources.aliexpress import buscar

print("OK: configuración AliExpress cargada; ejecutando consulta real...")
offers = buscar("nvme 1tb", limite=5, categoria="storage")
print("PRODUCTOS:", len(offers))
for i, offer in enumerate(offers, 1):
    print(i, offer.source, offer.external_id, offer.title[:90], offer.current_price, offer.reference_price, offer.discount_pct, offer.affiliate_url)
