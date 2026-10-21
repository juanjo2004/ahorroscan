#!/usr/bin/env python3
from __future__ import annotations
import hashlib, hmac, json, secrets, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from config import ALI_APP_KEY, ALI_APP_SECRET

HOST="127.0.0.1"
PORT=8787
PUBLIC_BASE="https://raspi4.tail8794f8.ts.net"
CALLBACK="/aliexpress/callback"
START="/aliexpress/start"
AUTH_URL="https://api-sg.aliexpress.com/oauth/authorize"
TOKEN_URL="https://api-sg.aliexpress.com/rest/auth/token/create"
STATE=Path("data/aliexpress_oauth_state.json")
TOKENS=Path("data/aliexpress_token.json")

def save_private(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    path.chmod(0o600)

def signature(params: dict[str,str]) -> str:
    canonical="".join(k+str(params[k]) for k in sorted(params) if str(params[k])!="")
    canonical="/auth/token/create"+canonical
    return hmac.new(ALI_APP_SECRET.encode(), canonical.encode(), hashlib.sha256).hexdigest().upper()

def exchange(code: str) -> dict:
    params={"app_key":str(ALI_APP_KEY),"sign_method":"sha256","timestamp":str(int(time.time()*1000)),"code":code}
    params["sign"]=signature(params)
    req=Request(TOKEN_URL,data=urlencode(params).encode(),method="POST",
               headers={"Content-Type":"application/x-www-form-urlencoded;charset=utf-8"})
    with urlopen(req,timeout=30) as r:
        return json.loads(r.read().decode())

class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): print("[OAUTH]", fmt%args)
    def html(self, code, title, body):
        b=f"<!doctype html><html lang='es'><meta charset='utf-8'><title>{title}</title><body style='font-family:sans-serif;max-width:720px;margin:60px auto;padding:20px'>{body}</body></html>".encode()
        self.send_response(code); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        p=urlparse(self.path)
        if p.path=="/health":
            return self.html(200,"OK","<h1>AliExpress OAuth OK</h1>")
        if p.path==START:
            if not ALI_APP_KEY or not ALI_APP_SECRET:
                return self.html(500,"Config","<h1>Falta configuración.</h1>")
            st=secrets.token_urlsafe(32)
            save_private(STATE,{"state":st,"created_at":int(time.time())})
            q={"response_type":"code","force_auth":"true","redirect_uri":PUBLIC_BASE+CALLBACK,"client_id":str(ALI_APP_KEY),"state":st}
            self.send_response(302); self.send_header("Location",AUTH_URL+"?"+urlencode(q)); self.end_headers(); return
        if p.path==CALLBACK:
            q=parse_qs(p.query)
            code=q.get("code",[None])[0]; state=q.get("state",[None])[0]
            if not code: return self.html(400,"OAuth","<h1>No se recibió code.</h1>")
            try: expected=json.loads(STATE.read_text()).get("state")
            except Exception: expected=None
            if not expected or not state or not secrets.compare_digest(expected,state):
                return self.html(400,"OAuth","<h1>Estado OAuth inválido.</h1>")
            try: data=exchange(code)
            except Exception as e:
                print("[OAUTH] token exchange:",type(e).__name__,str(e))
                return self.html(500,"OAuth","<h1>Error al obtener el token.</h1><p>Revisa el log local.</p>")
            save_private(TOKENS,data)
            try: STATE.unlink()
            except OSError: pass
            print("[OAUTH] token guardado correctamente")
            return self.html(200,"Completado","<h1>✅ Autorización completada</h1><p>Los tokens se han guardado en la Raspberry. Ya puedes cerrar esta ventana.</p>")
        return self.html(404,"404","<h1>404</h1>")

if __name__=="__main__":
    ThreadingHTTPServer((HOST,PORT),H).serve_forever()
