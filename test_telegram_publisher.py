import config
from telegram_publisher import check_connection, publish


def main():
    print("=== TEST TELEGRAM V2 ===")
    print(f"chat_configurado={bool(config.TELEGRAM_CHAT_ID)}")
    print(f"token_configurado={bool(config.TELEGRAM_BOT_TOKEN)}")
    print(f"dry_run={config.TELEGRAM_DRY_RUN}")
    print(f"max_publicaciones={config.MAX_PUBLICATIONS_PER_RUN}")

    if not config.TELEGRAM_BOT_TOKEN:
        print("SIN TOKEN: configura TELEGRAM_BOT_TOKEN en .env")
        return

    data = check_connection()
    user = data.get("result", {})
    print(f"getMe OK: @{user.get('username', '<sin username>')}")

    # Nunca publica en este test.
    if config.TELEGRAM_DRY_RUN:
        print("SEGURIDAD OK: TELEGRAM_DRY_RUN=1, no se publica.")
    else:
        print("ADVERTENCIA: TELEGRAM_DRY_RUN=0. Este test NO publica igualmente.")


if __name__ == "__main__":
    main()
