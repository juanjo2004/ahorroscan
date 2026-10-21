from catalog import CATALOG, query_count, iter_queries

assert len(CATALOG) >= 25
assert query_count() >= 50
items = list(iter_queries())
assert len(items) == query_count()
assert all(category and query for category, query in items)
print(f"OK: catálogo amplio con {len(CATALOG)} categorías y {query_count()} consultas")
