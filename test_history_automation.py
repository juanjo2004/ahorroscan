from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).resolve().parent
for name in ("history_collector.py", "run_history_scan.sh", "install_history_cron.sh", "uninstall_history_cron.sh"):
    p = BASE / name
    assert p.exists(), name
    assert p.stat().st_size > 0, name

subprocess.run([sys.executable, str(BASE / "history_collector.py"), "--help"], check=False)
print("OK: estructura de automatización histórica preparada")
