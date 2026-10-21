#!/usr/bin/env python3
"""AhorroScan destination orchestrator.

The registry controls which destinations run. Specialized scanners remain behind
small adapters; catalog-driven verticals use one generic scanner and publisher.
Publishing is opt-in on the command line so an invocation without --publish is
safe for staging and diagnostics.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from channel_registry import active_destinations

ROOT = Path(__file__).resolve().parent
METRICS_PATH = ROOT / "logs" / "unified_channel_cycles.jsonl"
TELEGRAM_ACCEPTED_STATES = {"published", "published_unrecorded", "published_claim_retained"}
ERROR_STATES = {
    "error",
    "rejected",
    "unknown_outcome",
    "published_unrecorded",
    "published_claim_retained",
    "invalid_identity",
    "history_unavailable",
    "guard_unavailable",
}
DRY_RUN_ENV = {
    "tech": "TELEGRAM_DRY_RUN",
    "hogar": "HOGAR_TELEGRAM_DRY_RUN",
    "moviles": "MOVILES_TELEGRAM_DRY_RUN",
    "mascotas": "MASCOTAS_TELEGRAM_DRY_RUN",
    "moda": "MODA_TELEGRAM_DRY_RUN",
    "deportes": "DEPORTE_TELEGRAM_DRY_RUN",
    "central": "AHOROSCAN_DRY_RUN",
}


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _python_legacy():
    candidate = ROOT / "venv" / "bin" / "python"
    return str(candidate) if candidate.is_file() else sys.executable


@contextmanager
def _temporary_env(values):
    old = {key: os.environ.get(key) for key in values}
    try:
        os.environ.update(values)
        yield
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _result_counts(results):
    outcomes = Counter(str(item.get("status", "unknown")) for item in results)
    published = sum(outcomes.get(state, 0) for state in TELEGRAM_ACCEPTED_STATES)
    errors = sum(outcomes.get(state, 0) for state in ERROR_STATES)
    recording_errors = sum(
        outcomes.get(state, 0)
        for state in ("published_unrecorded", "published_claim_retained")
    )
    return {
        "outcomes": dict(sorted(outcomes.items())),
        "published": published,
        "publication_errors": errors,
        "recording_errors": recording_errors,
    }


def _run_python_channel(channel, publishing):
    dry_env = DRY_RUN_ENV.get(channel)
    selection_rejections = None
    with _temporary_env({dry_env: "0" if publishing else "1"} if dry_env else {}):
        if channel == "moviles":
            from mobile_scanner import scan
            from mobile_publisher import publish_mobile
            scored, eligible = scan()
            results = publish_mobile(eligible, force=publishing)
        elif channel == "mascotas":
            from pet_scanner import scan
            from pet_publisher import publish_pet
            scored, eligible = scan()
            results = publish_pet(eligible, force=publishing)
        else:
            from vertical_channel import CHANNELS, last_selection_rejections
            if channel not in CHANNELS:
                raise ValueError("No existe perfil/catálogo para el canal registrado")
            from vertical_scanner import scan
            from vertical_publisher import publish
            scored, eligible = scan(channel)
            selection_rejections = last_selection_rejections(channel)
            results = publish(channel, eligible, force=publishing)
    summary = _result_counts(results)
    summary.update({"unique_candidates": len(scored), "eligible": len(eligible)})
    if selection_rejections is not None:
        summary["selection_rejection_reasons"] = selection_rejections
    return summary


def _redact(text):
    text = re.sub(r"https?://api\.telegram\.org/bot[^/\s]+", "[telegram-api-redacted]", text)
    text = re.sub(r"\b\d{7,12}:[A-Za-z0-9_-]{30,}\b", "[token-redacted]", text)
    return text


def _subprocess_summary(destination, output):
    summary = {}
    patterns = {
        "aggregator": {
            "ranked": r"candidatos_ranked=(\d+)",
            "eligible": r"seleccionados=(\d+)",
            "published": r"PUBLICADAS=(\d+)",
        },
        "instagram": {
            "eligible": r"candidatos=(\d+)",
        },
    }
    handler = "aggregator" if destination == "central" else destination
    for key, pattern in patterns.get(handler, {}).items():
        match = re.search(pattern, output)
        if match:
            summary[key] = int(match.group(1))
    if destination == "instagram":
        summary["published"] = len(re.findall(r"\[INSTAGRAM\] PUBLICADO", output))
    return summary


def _read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _tech_brand_metrics_7d():
    database = ROOT / "data" / "ofertas.db"
    if not database.is_file():
        return {}
    from brand_identity import extract_brand

    try:
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
            titles = [
                row[0] or ""
                for row in connection.execute(
                    """
                    SELECT title
                    FROM publications
                    WHERE origin = 'tech'
                      AND datetime(published_at) >= datetime('now', '-7 days')
                    """
                )
            ]
    except sqlite3.Error:
        return {}

    brands = Counter(
        brand for title in titles if (brand := extract_brand(title))
    )
    recognized = sum(brands.values())
    return {
        "posts_7d": len(titles),
        "recognized_brand_posts_7d": recognized,
        "recognized_brand_rate_7d": round(100 * recognized / len(titles), 1) if titles else None,
        "recognized_brands_7d": dict(sorted(brands.items())),
    }


def _tech_log_summary():
    log = ROOT / "logs" / "auto_runner.log"
    if not log.exists():
        return {}
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    starts = [i for i, line in enumerate(lines) if "[AUTO] INICIO" in line]
    if not starts:
        return {}
    start = starts[-1]
    end = next((i for i in range(start + 1, len(lines)) if "[AUTO] FIN" in lines[i]), len(lines))
    block = lines[start:end]
    summary = {}
    for key, pattern in {
        "scanned_candidates": r"Candidatas encontradas:\s*(\d+)",
        "unique_candidates": r"Válidas:\s*(\d+)",
        "eligible": r"Ofertas publicables:\s*(\d+)",
        "published": r"Publicadas:\s*(\d+)",
        "publication_errors": r"Errores:\s*(\d+)",
    }.items():
        values = [re.search(pattern, line) for line in block]
        values = [match for match in values if match]
        if values:
            summary[key] = int(values[-1].group(1))
    reasons = Counter()
    for line in block:
        match = re.search(r"Filtro: NO elegible \(([^)]*)\)", line)
        if match:
            reasons.update(part.strip() for part in match.group(1).split(",") if part.strip())
    if reasons:
        summary["rejection_reasons"] = dict(sorted(reasons.items()))
    return summary


def _read_child_status(destination):
    if destination == "tech":
        health = _read_json(ROOT / "data" / "source_health.json")
        sources = health.get("sources", {})
        result = _tech_log_summary()
        result.update(_tech_brand_metrics_7d())
        result["source_health"] = {
            source: {
                key: info.get(key)
                for key in ("state", "attempted", "failed", "succeeded", "candidates")
                if key in info
            }
            for source, info in sources.items()
        }
        result["source_candidates"] = sum(
            int(info.get("candidates", 0) or 0) for info in sources.values()
        )
        return result
    if destination == "hogar":
        status = _read_json(ROOT.parent / "ahorroscan-hogar" / "data" / "production_status.json")
        catalog = status.get("catalog", {})
        telegram = status.get("telegram", {})
        return {
            "eligible": catalog.get("selected"),
            "unique_candidates": catalog.get("selected"),
            "published": telegram.get("published"),
            "publication_errors": telegram.get("errors"),
            "outcomes": telegram.get("outcomes", {}),
            "blocked_reasons": telegram.get("blocked_reasons", {}),
        }
    return {}


def _run_subprocess(destination, publishing):
    env = os.environ.copy()
    if destination == "hogar" and publishing:
        from ha_publish_guard import publishing_enabled
        if not publishing_enabled("hogar"):
            return {
                "status": "error",
                "error_type": "PublicationGuardBlocked",
                "publication_errors": 1,
                "published": 0,
            }
    dry_key = DRY_RUN_ENV.get(destination)
    if dry_key:
        env[dry_key] = "0" if publishing else "1"
    if destination == "tech":
        env["AHOROSCAN_TECH_PYTHON"] = str(ROOT / "venv" / "bin" / "python") if (ROOT / "venv" / "bin" / "python").is_file() else sys.executable
        command = ["bash", str(ROOT / "run_auto.sh")]
        cwd = ROOT
    elif destination == "hogar":
        hogar_root = ROOT.parent / "ahorroscan-hogar"
        env["AHOROSCAN_HOGAR_PYTHON"] = str(hogar_root / ".venv" / "bin" / "python") if (hogar_root / ".venv" / "bin" / "python").is_file() else sys.executable
        command = ["bash", str(hogar_root / "run_production_cycle.sh")]
        cwd = hogar_root
    elif destination == "central":
        command = [_python_legacy(), str(ROOT / "aggregator.py")]
        cwd = ROOT
    elif destination == "instagram":
        command = [_python_legacy(), str(ROOT / "instagram_auto.py")]
        if publishing:
            command.append("--publish")
        cwd = ROOT
    else:
        raise ValueError("Destino auxiliar no soportado")

    timeout = 2400 if destination in {"tech", "hogar"} else 600
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    output = completed.stdout or ""
    error_output = completed.stderr or ""
    summary = _subprocess_summary(destination, output)
    summary.update(_read_child_status(destination))
    # Preserve a bounded, secret-redacted diagnostic when a child process fails.
    # Previously stderr was captured but silently discarded, hiding the cause of
    # recurring Instagram failures from both metrics and the watchdog.
    if completed.returncode != 0 and error_output.strip():
        summary["error_detail"] = _redact(error_output.strip())[-4000:]
    if destination == "central" and completed.returncode == 0 and "PUBLICADAS" not in output:
        summary.setdefault("published", 0)
    if destination == "instagram" and completed.returncode == 0:
        summary.setdefault("published", 0)
    summary["exit_code"] = completed.returncode
    summary["status"] = "success" if completed.returncode == 0 else "error"
    if completed.returncode != 0:
        summary["error_type"] = "ChildProcessExit"
    return summary


def _dispatch(destination, config, publishing):
    if destination in {"tech", "hogar", "central", "instagram"}:
        return _run_subprocess(destination, publishing)
    return _run_python_channel(destination, publishing)


def _write_metric(record):
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with METRICS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _website_catalog_audit():
    """Read-only audit of website catalogs and API endpoints; never publishes."""
    database = ROOT / "data" / "ofertas.db"
    web_root = ROOT.parent / "superofertastech-web"
    catalog_tables = {
        "tech": ("publications", "origin = 'tech'"),
        "moviles": ("mobile_publications", None),
        "mascotas": ("pet_publications", None),
        "moda": ("fashion_publications", None),
        "deportes": ("sports_publications", None),
    }
    audit = {"checked_at": _utc_now(), "status": "success", "catalogs": {}, "http": {}}
    try:
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True, timeout=5) as connection:
            available = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for name, (table, where) in catalog_tables.items():
                if table not in available:
                    audit["catalogs"][name] = {"status": "error", "error": "missing_table"}
                    audit["status"] = "error"
                    continue
                columns = {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}
                time_column = next((col for col in ("published_at", "created_at") if col in columns), None)
                sql = f'SELECT COUNT(*), MAX("{time_column}") FROM "{table}"'
                if where:
                    sql += " WHERE " + where
                count, latest = connection.execute(sql).fetchone()
                catalog = {"status": "success" if count else "empty", "rows": count, "latest_publication": latest}
                if latest:
                    try:
                        published_at = datetime.fromisoformat(str(latest).replace("Z", "+00:00"))
                        if published_at.tzinfo is None:
                            published_at = published_at.replace(tzinfo=timezone.utc)
                        age_hours = round(max(0.0, (datetime.now(timezone.utc) - published_at.astimezone(timezone.utc)).total_seconds() / 3600), 1)
                        catalog["age_hours"] = age_hours
                        catalog["freshness"] = "stale" if age_hours > 48 else "fresh"
                        if age_hours > 48 and audit["status"] == "success":
                            audit["status"] = "warning"
                    except (TypeError, ValueError):
                        catalog["freshness"] = "unknown"
                audit["catalogs"][name] = catalog
    except (OSError, sqlite3.Error) as exc:
        audit["status"] = "error"
        audit["database_error"] = type(exc).__name__

    hogar_path = web_root / "hogar" / "data" / "offers.json"
    try:
        hogar = json.loads(hogar_path.read_text(encoding="utf-8"))
        offers = hogar.get("offers", []) if isinstance(hogar, dict) else []
        audit["catalogs"]["hogar"] = {
            "status": "success" if isinstance(offers, list) else "error",
            "rows": len(offers) if isinstance(offers, list) else None,
            "generated_at": hogar.get("generated_at") if isinstance(hogar, dict) else None,
        }
        if not isinstance(offers, list):
            audit["status"] = "error"
    except (OSError, ValueError) as exc:
        audit["catalogs"]["hogar"] = {"status": "error", "error": type(exc).__name__}
        audit["status"] = "error"

    import urllib.error
    import urllib.request
    for name, path in {
        "health": "/api/health", "tech": "/api/offers",
        "moviles": "/api/mobile-offers", "mascotas": "/api/pet-offers",
        "moda": "/api/moda-offers", "deportes": "/api/deporte-offers",
    }.items():
        try:
            request = urllib.request.Request("http://127.0.0.1:8082" + path, headers={"Accept": "application/json"})
            with urllib.request.urlopen(request, timeout=4) as response:
                payload = json.loads(response.read(2_000_000).decode("utf-8"))
                ok = response.status == 200 and payload.get("ok") is True
                audit["http"][name] = {"status": response.status, "ok": ok, "count": payload.get("count")}
                if not ok:
                    audit["status"] = "error"
        except (OSError, ValueError, urllib.error.URLError) as exc:
            audit["http"][name] = {"status": "error", "error": type(exc).__name__}
            audit["status"] = "error"
    return audit


def _check_config(active):
    from vertical_channel import CHANNELS as vertical_channels
    known = {"tech", "hogar", "moviles", "mascotas", "central", "instagram"} | set(vertical_channels)
    missing = sorted(set(active) - known)
    if missing:
        print("Destinos activos sin adaptador/catálogo:", ", ".join(missing))
        return 2
    print("Configuración válida; destinos activos:", ", ".join(active))
    print("Canales verticales configurables:", ", ".join(sorted(vertical_channels)))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Ejecuta los destinos AhorroScan desde un registro común.")
    parser.add_argument("--publish", action="store_true", help="Autoriza el envío real de publicaciones.")
    parser.add_argument("--channel", action="append", help="Limita el ciclo a uno o varios destinos registrados.")
    parser.add_argument("--check-config", action="store_true", help="Valida destinos y adaptadores sin ejecutar escáneres.")
    args = parser.parse_args(argv)

    configured = active_destinations()
    selected = list(configured)
    if args.channel:
        unknown = sorted(set(args.channel) - set(configured))
        if unknown:
            parser.error("Destino inactivo o desconocido: " + ", ".join(unknown))
        selected = args.channel
    if args.check_config:
        return _check_config(selected)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    failures = 0
    for destination in selected:
        started = time.monotonic()
        record = {
            "run_id": run_id,
            "destination": destination,
            "started_at": _utc_now(),
            "mode": "publish" if args.publish else "dry_run",
        }
        try:
            summary = _dispatch(destination, configured[destination], args.publish)
            record.update(summary)
            if summary.get("status") == "error" or int(summary.get("publication_errors", 0) or 0) > 0:
                failures += 1
                record["status"] = "error"
            else:
                record["status"] = "success"
        except Exception as exc:
            failures += 1
            record.update({"status": "error", "error_type": type(exc).__name__})
        record["finished_at"] = _utc_now()
        record["duration_seconds"] = round(time.monotonic() - started, 3)
        _write_metric(record)
        print(
            "[UNIFIED]"
            f" destination={destination} status={record['status']}"
            f" duration={record['duration_seconds']}s"
            f" published={record.get('published', 0)}"
            f" errors={record.get('publication_errors', 0)}"
            + (f" error_type={record['error_type']}" if record.get("error_type") else "")
        )
    audit_started = time.monotonic()
    try:
        audit = _website_catalog_audit()
        audit_record = {
            "run_id": run_id,
            "destination": "website_catalog_audit",
            "started_at": audit.get("checked_at", _utc_now()),
            "finished_at": _utc_now(),
            "mode": "read_only",
            "status": audit.get("status", "error"),
            "duration_seconds": round(time.monotonic() - audit_started, 3),
            "catalogs": audit.get("catalogs", {}),
            "http": audit.get("http", {}),
        }
        if audit_record["status"] == "error":
            failures += 1
        _write_metric(audit_record)
        stale_catalogs = sorted(
            name for name, item in audit_record["catalogs"].items()
            if item.get("freshness") == "stale"
        )
        print("[UNIFIED] website_catalog_audit"
              f" status={audit_record['status']}"
              f" duration={audit_record['duration_seconds']}s"
              f" catalogs={len(audit_record['catalogs'])}"
              f" http_checks={len(audit_record['http'])}"
              f" stale={','.join(stale_catalogs) if stale_catalogs else 'none'}")
    except Exception as exc:
        failures += 1
        _write_metric({
            "run_id": run_id,
            "destination": "website_catalog_audit",
            "started_at": _utc_now(),
            "finished_at": _utc_now(),
            "mode": "read_only",
            "status": "error",
            "error_type": type(exc).__name__,
        })
        print(f"[UNIFIED] website_catalog_audit status=error error_type={type(exc).__name__}")
    print(f"[UNIFIED] run_id={run_id} destinations={len(selected)} failures={failures}")
    return 2 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
