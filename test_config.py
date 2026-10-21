import os
import config

print("OK: config importado")
print("AMAZON_TAG disponible:", bool(os.getenv("AMAZON_TAG")))
print("ALIASES disponibles:", all(k in os.environ for k in ("ALI_APP_KEY", "ALI_APP_SECRET", "ALI_TRACKING_ID")))
