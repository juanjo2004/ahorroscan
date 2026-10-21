#!/usr/bin/env python3
"""Run one V2 scan for historical price collection, without Telegram publishing."""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "history_collector.log"


def log(message: str) -> None:
    line = f"[{datetime.now().astimezone().isoformat(timespec='seconds')}] {message}"
    print(line, flush=True)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def main() -> int:
    os.chdir(BASE_DIR)
    log("INICIO scan histórico V2")

    cmd = [sys.executable, str(BASE_DIR / "dry_run.py")]
    env = os.environ.copy()
    env["SCAN_MODE"] = "full"
    log("Ejecutando dry_run.py en modo no-publicación")

    result = subprocess.run(cmd, cwd=BASE_DIR, text=True, capture_output=True, env=env)

    with LOG_FILE.open("a", encoding="utf-8") as fh:
        if result.stdout:
            fh.write(result.stdout)
        if result.stderr:
            fh.write("\n[STDERR]\n")
            fh.write(result.stderr)

    if result.returncode == 0:
        log("FIN OK scan histórico V2")
        return 0

    log(f"FIN ERROR scan histórico V2, código={result.returncode}")
    if result.stderr:
        log(result.stderr.strip().splitlines()[-1])
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
