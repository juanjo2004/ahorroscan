from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "ofertas.db"
CLICK_DB = BASE_DIR / "redirector" / "clicks.db"

HOST = "0.0.0.0"
PORT = 8790


def connect_main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def connect_clicks():
    CLICK_DB.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(CLICK_DB)
    conn.row_factory = sqlite3.Row

    # Sistema nuevo de producción
    conn.execute("""
        CREATE TABLE IF NOT EXISTS links_v2 (
            code TEXT PRIMARY KEY,
            product_id INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS clicks_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            clicked_at TEXT NOT NULL,
            user_agent TEXT,
            source_ip TEXT,
            channel TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS links_v3 (
            code TEXT PRIMARY KEY,
            project TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            destination_url TEXT NOT NULL,
            created_at TEXT NOT NULL,
            channel TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_links_v3_product
        ON links_v3(project, product_id)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS clicks_v3 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            project TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            clicked_at TEXT NOT NULL,
            user_agent TEXT,
            source_ip TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_clicks_v3_product_time
        ON clicks_v3(project, product_id, clicked_at)
    """)
    if "channel" not in {r[1] for r in conn.execute("PRAGMA table_info(links_v3)")}:
        conn.execute("ALTER TABLE links_v3 ADD COLUMN channel TEXT")
    if "channel" not in {r[1] for r in conn.execute("PRAGMA table_info(clicks_v3)")}:
        conn.execute("ALTER TABLE clicks_v3 ADD COLUMN channel TEXT")

    if "channel" not in {r[1] for r in conn.execute("PRAGMA table_info(links_v3)")}: 
        conn.execute("ALTER TABLE links_v3 ADD COLUMN channel TEXT")
    if "channel" not in {r[1] for r in conn.execute("PRAGMA table_info(clicks_v3)")}: 
        conn.execute("ALTER TABLE clicks_v3 ADD COLUMN channel TEXT")
    for col in ("referrer", "country", "device", "browser"):
        if col not in {r[1] for r in conn.execute("PRAGMA table_info(clicks_v3)")}: 
            conn.execute("ALTER TABLE clicks_v3 ADD COLUMN " + col + " TEXT")
    conn.execute("CREATE TABLE IF NOT EXISTS pageviews (id INTEGER PRIMARY KEY AUTOINCREMENT, path TEXT NOT NULL, viewed_at TEXT NOT NULL, referrer TEXT, country TEXT, device TEXT, browser TEXT, utm_source TEXT, utm_medium TEXT, utm_campaign TEXT)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pageviews_time ON pageviews(viewed_at)")
    conn.commit()
    return conn


def get_redirect_v3(code: str):
    """Busca un enlace trackeable v3 y devuelve (project, product_id, destination_url, channel)."""
    conn = connect_clicks()
    try:
        row = conn.execute(
            """
            SELECT project, product_id, destination_url, channel
            FROM links_v3
            WHERE code = ?
            LIMIT 1
            """,
            (code,),
        ).fetchone()
        if row is None:
            return None
        return (
            str(row["project"]),
            int(row["product_id"]),
            row["destination_url"],
            row["channel"],
        )
    finally:
        conn.close()


def get_redirect_v2(code: str):
    """
    Busca un código nuevo y devuelve:
    (product_id, affiliate_url)
    """

    conn_clicks = connect_clicks()

    try:
        row = conn_clicks.execute(
            """
            SELECT product_id
            FROM links_v2
            WHERE code = ?
            """,
            (code,),
        ).fetchone()

        if row is None:
            return None

        product_id = int(row["product_id"])

        conn_main = connect_main()

        try:
            product = conn_main.execute(
                """
                SELECT affiliate_url
                FROM products
                WHERE id = ?
                LIMIT 1
                """,
                (product_id,),
            ).fetchone()
        finally:
            conn_main.close()

        if product is None:
            return None

        affiliate_url = product["affiliate_url"]

        if not affiliate_url:
            return None

        return product_id, affiliate_url

    finally:
        conn_clicks.close()


def record_click_v3(code, project, product_id, user_agent, source_ip, channel=None,
                    referrer=None, country=None, device=None, browser=None):
    conn = connect_clicks()
    try:
        conn.execute(
            """
            INSERT INTO clicks_v3 (
                code, project, product_id, clicked_at,
                user_agent, source_ip, channel, referrer, country, device, browser
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                code,
                project,
                product_id,
                datetime.now(timezone.utc).isoformat(),
                user_agent,
                source_ip,
                channel,
                referrer,
                country,
                device,
                browser,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def record_click_v2(code, product_id, user_agent, source_ip):
    conn = connect_clicks()
    try:
        conn.execute(
            """
            INSERT INTO clicks_v2 (
                code, product_id, clicked_at,
                user_agent, source_ip
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                code,
                product_id,
                datetime.now(timezone.utc).isoformat(),
                user_agent,
                source_ip,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def classify_device(ua):
    ua=(ua or "").lower()
    if "ipad" in ua or "tablet" in ua:
        return "tablet"
    if "mobile" in ua or "android" in ua or "iphone" in ua:
        return "mobile"
    return "desktop"


def classify_browser(ua):
    ua=(ua or "").lower()
    if "edg/" in ua:
        return "edge"
    if "chrome/" in ua or "crios/" in ua:
        return "chrome"
    if "firefox/" in ua or "fxios/" in ua:
        return "firefox"
    if "safari/" in ua and "chrome/" not in ua:
        return "safari"
    if "instagram" in ua:
        return "instagram"
    return "other"


def record_pageview(payload, user_agent, country):
    conn=connect_clicks()
    try:
        conn.execute("INSERT INTO pageviews (path,viewed_at,referrer,country,device,browser,utm_source,utm_medium,utm_campaign) VALUES (?,?,?,?,?,?,?,?,?)", (
            str(payload.get("path") or "/")[:500],
            datetime.now(timezone.utc).isoformat(),
            str(payload.get("referrer") or "")[:1000] or None,
            country,
            classify_device(user_agent),
            classify_browser(user_agent),
            str(payload.get("utm_source") or "")[:100] or None,
            str(payload.get("utm_medium") or "")[:100] or None,
            str(payload.get("utm_campaign") or "")[:150] or None,
        ))
        conn.commit()
    finally:
        conn.close()


class Handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        return

    def send_text(self, status, text):
        body = text.encode("utf-8")

        self.send_response(status)
        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )
        self.send_header(
            "Content-Length",
            str(len(body))
        )
        self.end_headers()

        self.wfile.write(body)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path.rstrip("/") != "/track/pageview":
            self.send_text(404, "Not found")
            return
        try:
            import json
            length=int(self.headers.get("Content-Length", "0"))
            payload=json.loads(self.rfile.read(min(length, 10000)).decode("utf-8")) if length else {}
            ua=self.headers.get("User-Agent", "")
            country=(self.headers.get("CF-IPCountry") or self.headers.get("X-Country") or "").upper()[:2] or None
            record_pageview(payload, ua, country)
            self.send_text(204, "")
        except Exception:
            self.send_text(400, "Bad request")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        # Health check local
        if path == "/health":
            self.send_text(200, "OK")
            return

        # Compatibilidad local + Tailscale Funnel
        if path.startswith("/go/"):
            code = path[len("/go/"):]
        elif path.count("/") == 1 and path.startswith("/"):
            code = path[1:]
        else:
            self.send_text(404, "Not found")
            return

        if not code:
            self.send_text(404, "Not found")
            return

        result_v3 = get_redirect_v3(code)

        if result_v3 is not None:
            project, product_id, affiliate_url, channel = result_v3
            ua=self.headers.get("User-Agent", "")
            real_ip=(self.headers.get("CF-Connecting-IP") or self.headers.get("X-Real-IP") or self.client_address[0])
            country=(self.headers.get("CF-IPCountry") or "").upper()[:2] or None
            referrer=self.headers.get("Referer")
            record_click_v3(code, project, product_id, ua, real_ip, channel,
                            referrer=referrer, country=country,
                            device=classify_device(ua), browser=classify_browser(ua))
        else:
            result_v2 = get_redirect_v2(code)

            if result_v2 is None:
                self.send_text(404, "Link not found")
                return

            product_id, affiliate_url = result_v2
            record_click_v2(
                code,
                product_id,
                self.headers.get("User-Agent", ""),
                self.client_address[0],
            )

        self.send_response(302)

        self.send_header(
            "Location",
            affiliate_url
        )

        self.send_header(
            "Cache-Control",
            "no-store"
        )

        self.end_headers()


if __name__ == "__main__":
    print(
        f"Redirector escuchando en http://{HOST}:{PORT}"
    )

    server = ThreadingHTTPServer(
        (HOST, PORT),
        Handler,
    )

    server.serve_forever()
