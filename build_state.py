import json
import os
import sys

from dotenv import load_dotenv

STORAGE_FILE = "fb_state.json"

REQUIRED_COOKIES = ["c_user", "xs", "datr", "sb"]
OPTIONAL_COOKIES = ["fr", "presence", "ps_l", "ps_n", "wd"]

def build_storage_state():
    # Cargar variables desde .env si existe
    load_dotenv()
    
    cookies = []
    
    for name in REQUIRED_COOKIES + OPTIONAL_COOKIES:
        env_key = f"FB_COOKIE_{name.upper()}"
        value = os.getenv(env_key)
        if not value:
            if name in REQUIRED_COOKIES:
                print(f"❌ Falta cookie requerida: {env_key}")
                sys.exit(1)
            continue
        
        cookie = {
            "name": name,
            "value": value,
            "domain": ".facebook.com",
            "path": "/",
            "expires": -1,
            "httpOnly": name in ("xs", "datr", "sb", "fr", "ps_l", "ps_n"),
            "secure": True,
            "sameSite": "None" if name not in ("ps_l", "wd") else "Lax"
        }
        cookies.append(cookie)
    
    state = {
        "cookies": cookies,
        "origins": []
    }
    
    with open(STORAGE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    
    print(f"✅ Estado de sesión generado en {STORAGE_FILE}")
    print(f"   Cookies incluidas: {', '.join(c['name'] for c in cookies)}")

if __name__ == "__main__":
    build_storage_state()
