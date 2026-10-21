from database import init_db, get_history_stats, upsert_product
from scanner import run

# Este script vuelve a escanear y muestra el estado histórico de las ofertas publicables.
# No publica nada en Telegram.

if __name__ == '__main__':
    init_db()
    scored, publicable = run(return_publicable=True)
    print('\n=== ESTADO HISTÓRICO DE PUBLICABLES ===')
    for score, offer, history, breakdown, classification in publicable:
        current = offer.current_price
        avg = history.get('average')
        minimum = history.get('minimum')
        vs_avg = ((avg - current) / avg * 100.0) if avg and avg > 0 else None
        vs_min = ((minimum - current) / minimum * 100.0) if minimum and minimum > 0 else None
        avg_text = f'{avg:.2f} €' if avg is not None else 'n/d'
        min_text = f'{minimum:.2f} €' if minimum is not None else 'n/d'
        avg_pct = f'{vs_avg:+.1f}%' if vs_avg is not None else 'n/d'
        min_pct = f'{vs_min:+.1f}%' if vs_min is not None else 'n/d'
        print(f'{offer.title[:70]}')
        print(f'  Muestras 30d: {history.get("count", 0)} | media: {avg_text} ({avg_pct}) | mínimo previo: {min_text} ({min_pct})')
        print(f'  Confianza histórico: {history.get("confidence", 0.0):.2f} | score histórico activo: {"SÍ" if history.get("count", 0) >= 3 else "NO"}')
