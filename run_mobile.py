from mobile_scanner import scan
from mobile_publisher import publish_mobile


if __name__ == "__main__":
    print("=== AHORROSCAN MÓVILES ===")
    print("DRY_RUN:", __import__("mobile_publisher").DRY_RUN)
    _, publicable = scan()
    print("Publicables:", len(publicable))
    publish_mobile(publicable)