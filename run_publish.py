from scanner import run
from telegram_publisher import publish

if __name__ == "__main__":
    print("=== V2 TELEGRAM PUBLISH ===")
    print(f"DRY_RUN={'1' if __import__('config').TELEGRAM_DRY_RUN else '0'}")
    scored, publicable = run(return_publicable=True)
    print(f"Candidatos publicables: {len(publicable)}")
    publish(publicable)
