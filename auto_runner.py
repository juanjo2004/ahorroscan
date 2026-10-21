from __future__ import annotations

from datetime import datetime, timezone

import config
from scanner import run, get_last_run_health
from telegram_publisher import publish
from publication_guard import get_publication_stats


def main() -> int:
    started = datetime.now(timezone.utc)

    print("=" * 70)
    print("=== TELEGRAM BOT V2 - AUTO RUN ===")
    print("=" * 70)
    print("Inicio UTC:", started.isoformat())
    print("DRY_RUN:", config.TELEGRAM_DRY_RUN)
    print("Máximo por ejecución:", config.MAX_PUBLICATIONS_PER_RUN)
    print()

    try:
        _, publicable = run(return_publicable=True, mode="discovery")

        health = get_last_run_health()
        amazon_state = health.get("sources", {}).get("amazon", {}).get("state")
        if amazon_state in {"degraded", "unavailable"}:
            source = health.get("sources", {}).get("amazon", {})
            print(
                "Amazon parcialmente disponible; se conservan las ofertas "
                "obtenidas correctamente y se informa del fallo por consulta. "
                f"Fallidas: {source.get('failed', 0)}/{source.get('attempted', 0)}"
            )

        print()
        print("=== RESULTADO DEL SCANNER ===")
        print("Ofertas publicables:", len(publicable))

        if not publicable:
            stats = get_publication_stats()

            print("No hay ofertas para publicar.")
            print(
                f"Publicaciones hoy: "
                f"{stats['today']}/{config.MAX_PUBLICATIONS_PER_DAY}"
            )
            return 0

        print()
        print("=== PUBLICADOR ===")

        results = publish(
            publicable,
            force=False,
        )

        print()
        print("=== RESUMEN DE PUBLICACIÓN ===")

        published = 0
        dry_run = 0
        blocked = 0
        errors = 0

        for result in results:
            status = result.get("status")

            if status == "published":
                published += 1
            elif status == "dry_run":
                dry_run += 1
            elif status == "blocked":
                blocked += 1
            elif status in {"error", "rejected", "unknown_outcome", "published_unrecorded"}:
                errors += 1

            print(result)

        stats = get_publication_stats()

        print()
        print("Publicadas:", published)
        print("Bloqueadas:", blocked)
        print("DRY RUN:", dry_run)
        print("Errores:", errors)
        print()
        print(
            f"Publicaciones hoy: "
            f"{stats['today']}/{config.MAX_PUBLICATIONS_PER_DAY}"
        )
        print(
            f"Publicaciones totales: "
            f"{stats['total_publications']}"
        )

        finished = datetime.now(timezone.utc)

        print()
        print("Fin UTC:", finished.isoformat())
        print("Duración:", finished - started)

        if errors:
            print()
            print("⚠️ La ejecución terminó con errores de publicación.")
            return 2

        print()
        print("✅ AUTO RUN TERMINADO CORRECTAMENTE")
        return 0

    except Exception as exc:
        print()
        print("❌ ERROR FATAL EN AUTO RUN")
        print(type(exc).__name__ + ":", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
