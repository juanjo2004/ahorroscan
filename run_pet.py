from pet_scanner import scan
from pet_publisher import publish_pet

if __name__ == "__main__":
    scored, publicable = scan()
    print("[PET-RUNNER]", publish_pet(publicable))