from models import Offer
from database import history_stats_from_rows
from scoring import score_offer


def offer(price=27.99, ref=59.99):
    return Offer('amazon', 'TEST', 'Producto', price, ref, 'https://example.com', 'https://example.com/tag', rating=4.6, reviews=10000, category='mice')


# Sin histórico: el precio no recibe bonus histórico.
o = offer()
s0, b0 = score_offer(o, history_stats_from_rows([]))
assert b0['history_count'] == 0
assert b0['deal_parts']['vs_average'] == 0.0
assert b0['deal_parts']['vs_prior_minimum'] == 0.0

# 2 muestras: todavía no se considera histórico fiable.
rows2 = [(35.0, '2026-09-01'), (34.0, '2026-09-02')]
s2, b2 = score_offer(o, history_stats_from_rows(rows2))
assert b2['history_count'] == 2
assert b2['deal_parts']['vs_average'] == 0.0

# 5 muestras: el precio actual, claramente por debajo de la media, gana señal histórica.
rows5 = [(40.0, '2026-08-28'), (39.0, '2026-08-29'), (41.0, '2026-08-30'), (38.0, '2026-08-31'), (37.0, '2026-09-01')]
s5, b5 = score_offer(o, history_stats_from_rows(rows5))
assert b5['history_count'] == 5
assert b5['history_confidence'] == 0.5
assert b5['deal_parts']['vs_average'] > 0.0
assert s5 > s0

# Nuevo mínimo previo: recibe además señal de mínimo.
rows6 = [(40.0, '2026-08-28'), (39.0, '2026-08-29'), (41.0, '2026-08-30'), (38.0, '2026-08-31'), (37.0, '2026-09-01'), (35.0, '2026-09-02')]
_, b6 = score_offer(o, history_stats_from_rows(rows6))
assert b6['deal_parts']['vs_prior_minimum'] > 0.0

print('OK: histórico conservador, confianza progresiva y señales vs media/mínimo')
