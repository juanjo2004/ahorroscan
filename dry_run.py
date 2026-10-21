from scanner import run
from telegram_sender import build_dry_run

if __name__ == "__main__":
    _, publicable = run(return_publicable=True)
    print("\n=== TELEGRAM DRY RUN ===")
    print(build_dry_run(publicable) if publicable else "No hay publicaciones candidatas.")
