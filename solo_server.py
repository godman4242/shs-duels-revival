#!/usr/bin/env python3
"""
Straw Hat Samurai Duels - local solo server.

Serves the game assets AND emulates the dead PHP backend so the game can be
played offline in a single-player "guest" session.

WHY THE URL PATCH IS NEEDED
---------------------------
The game hardcodes its backend base URL in the SWF:
    http://www.strawhatsamuraiduels.com/server/     (43 bytes, NXDOMAIN today)
We byte-patch that exact-length string to:
    http://playerio.localhost:8765/solo/server/      (also 43 bytes)
"playerio" is kept in the replacement because the game's own anti-piracy gate
(GameEngine.checkSiteLock) only accepts URLs containing playerio,
strawhatsamuraiduels.com or explosivebarrel.net.
macOS resolves *.localhost -> 127.0.0.1, so no sudo / /etc/hosts edit needed.

VERIFIED DEAD (2026-10-30)
--------------------------
  strawhatsamuraiduels.com   -> DNS NXDOMAIN
  r.playerio.com (connect)   -> HTTP 500
  whipflash.com/api.php      -> HTTP 502 (payments only, not on boot path)
  cdn.playerio.com GameFS    -> bucket LOCKED (403 AccessDenied 2026-11-11; was HTTP 200 on 2026-10-30). Gameplay needs nothing from it: data is embedded in the SWF or already mirrored locally.
"""
import http.server
import json
import os
import socketserver
import sys
import urllib.parse
from urllib.parse import urlencode

ROOT = os.path.dirname(os.path.abspath(__file__))
ROOT_REAL = os.path.realpath(ROOT)
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
STATE_FILE = os.path.join(ROOT, ".solo_state.json")
MAX_BODY = 10 * 1024 * 1024  # 10 MB — anything larger is refused unread


def allowed_origin() -> str:
    return "http://playerio.localhost:%d" % PORT


LOCAL_HOSTS = ("playerio.localhost", "localhost", "127.0.0.1")


def allowed_hosts() -> set:
    """Host headers we answer to. Anything else is a DNS-rebinding attempt:
    the attacker's page resolves its own name to 127.0.0.1, so the browser
    treats it as same-origin and CORS never gets a say."""
    names = set()
    for name in LOCAL_HOSTS:
        names.add(name)
        names.add("%s:%d" % (name, PORT))
    return names


def allowed_launch_origins() -> set:
    """Origins the launcher can legitimately produce. This gates state-mutating
    requests only (CORS stays stricter above), so the game keeps working
    whichever localhost spelling the player opened."""
    return {"http://%s:%d" % (name, PORT) for name in LOCAL_HOSTS}


MUTATING_EPS = {"login", "login_internal", "register"}

# Guest character: name,level -> charstring format is "name,level"
GUEST_CHAR = "Kenshin,1"

CHAR_FIELDS = (
    "charname playerlevel playerxp playermoney playergold playerexp "
    "playerhonor playerreputation playerhealth playermana playerenergy "
    "playermaxhealth playermaxmana playermaxenergy playergun ammo item0 "
    "item1 item2 item3 item4 item5 item6 item7 item8 item9 item10 item11 "
    "item12 item13 item14 item15 item16 item17 item18 item19 item20 "
    "item21 item22 item23 item24 item25 item26 item27 item28 item29 "
    "item30 item31 item32 item33 item34 item35 item36 item37 item38 "
    "item39 item40 item41 item42 item43 item44 item45 item46 item47 "
    "item48 item49 item50 item51 item52 item53 item54 item55 item56 "
    "item57 item58 item59 item60 item61 item62 item63 item64 item65 "
    "item66 item67 item68 item69 item70 item71 item72 item73 item74 "
    "item75 item76 item77 item78 item79 item80 item81 item82 item83 "
    "item84 item85 item86 item87 item88 item89 item90 item91 item92 "
    "item93 item94 item95 item96 item97 item98 item99"
).split()


def default_player() -> dict:
    p = {f: "0" for f in CHAR_FIELDS}
    p["charname"] = GUEST_CHAR.split(",")[0]
    p["playerlevel"] = "1"
    p["playerxp"] = "0"
    p["playermoney"] = "5000"
    p["playergold"] = "25"
    p["playerexp"] = "0"
    p["playerhonor"] = "0"
    p["playerreputation"] = "0"
    p["playerhealth"] = "100"
    p["playermana"] = "100"
    p["playerenergy"] = "100"
    p["playermaxhealth"] = "100"
    p["playermaxmana"] = "100"
    p["playermaxenergy"] = "100"
    p["playergun"] = "0"
    p["ammo"] = "0"
    return p


def load_state() -> dict:
    try:
        with open(STATE_FILE) as fh:
            return json.load(fh)
    except Exception:
        return {"player": default_player(), "chars": GUEST_CHAR,
                "username": "Guest", "town": {},
                "gold": "25", "unlocked": []}


def save_state(state: dict) -> None:
    try:
        with open(STATE_FILE, "w") as fh:
            json.dump(state, fh, indent=1)
    except Exception:
        pass


STATE = load_state()


def player_row() -> str:
    """The game parses the player row as a comma-separated list in a fixed
    field order. Build it from CHAR_FIELDS."""
    p = STATE["player"]
    return ",".join(str(p.get(f, "0")) for f in CHAR_FIELDS)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, fmt, *args):
        sys.stderr.write("  [solo] " + (fmt % args) + "\n")

    def log_request(self, code="-", size="-"):
        sys.stderr.write("  [solo] REQ %s %s (%s bytes)\n" % (self.command, self.path, size))

    def _send(self, code, body, ctype="text/plain"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        # Only the game's own origin is granted CORS. Same-origin GETs carry
        # no Origin header at all, so an absent header must stay valid.
        origin = self.headers.get("Origin")
        if origin and origin == allowed_origin():
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_OPTIONS(self):
        self._route("OPTIONS")

    def do_GET(self):
        self._route("GET")

    def do_HEAD(self):
        # Without this, SimpleHTTPRequestHandler's own HEAD path would answer
        # for dotfiles and skip the confinement checks entirely.
        self._route("HEAD")

    def do_POST(self):
        self._route("POST")

    def _body(self) -> str:
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        n = max(0, min(n, MAX_BODY))
        if not n:
            return ""
        raw = self.rfile.read(n)
        # The game posts form-encoded data with a JSON payload.
        try:
            from urllib.parse import parse_qs
            q = parse_qs(raw.decode("utf-8", "replace"))
            for v in q.values():
                if v and v[0].strip().startswith("{"):
                    return v[0]
            return raw.decode("utf-8", "replace")
        except Exception:
            return raw.decode("utf-8", "replace")

    def _route(self, method):
        # DNS rebinding: a foreign name pointed at 127.0.0.1 would otherwise be
        # same-origin with this server and could read the local-only trees.
        host = (self.headers.get("Host") or "").lower()
        if host not in allowed_hosts():
            return self._send(403, b"forbidden")
        if method == "OPTIONS":
            return self._send(200, b"")

        # Refuse an oversized body before reading a single byte of it.
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length > MAX_BODY:
            return self._send(413, b"payload too large")

        # Decode percent-escapes FIRST, so %2e%2e%2f is seen as "../" by the
        # confinement check below rather than slipping past it as a filename.
        path = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)

        # --- PHP emulation -------------------------------------------------
        if "/server/" in path:
            ep = os.path.basename(path).replace(".php", "")
            return self._php(ep, method)

        # --- static ---------------------------------------------------------
        rel = path.lstrip("/")
        if not rel:
            rel = "index.html"
        # GameFS asset route: /r/<gameid>/<path> -> local mirror
        if rel.startswith("r/"):
            parts = rel.split("/", 2)
            if len(parts) == 3:
                rel = parts[2]

        # Dot-segments are never public: no dotfiles, no .git, no "..".
        segments = [s for s in rel.split("/") if s not in ("", ".")]
        if any(s.startswith(".") for s in segments):
            return self._send(403, b"forbidden")

        fs = os.path.realpath(os.path.join(ROOT, rel))
        if fs != ROOT_REAL and not fs.startswith(ROOT_REAL + os.sep):
            return self._send(403, b"forbidden")
        if os.path.isfile(fs):
            with open(fs, "rb") as fh:
                data = fh.read()
            return self._send(200, data, self.guess_type(fs))
        return self._send(404, b"not found")

    def _php(self, ep, method):
        body = self._body()
        sys.stderr.write("  [solo] PHP %s %s body=%r\n" % (method, ep, body[:400]))

        # CORS governs who may READ a response; it does not stop the request.
        # A hostile page can still POST here as a "simple request", so the
        # endpoints that write state verify the caller's Origin themselves.
        if ep in MUTATING_EPS:
            origin = self.headers.get("Origin")
            if origin and origin not in allowed_launch_origins():
                return self._send(403, b"forbidden")

        # ---- LOGIN -------------------------------------------------------
        if ep in ("login", "login_internal"):
            # The game parses this response as URL variables
            # (QueryManagerBase.loginComplete), NOT as JSON.
            STATE["chars"] = GUEST_CHAR
            save_state(STATE)
            params = {
                "status": "0",
                "chars": GUEST_CHAR,
                "username": "Guest",
                "id": "1",
                "motd": "Welcome to Straw Hat Samurai Duels (local solo build).",
                "magicnum": "0",
                "email": "solo@localhost",
                "verified": "1",
                "playertoken": "solo-token",
                "playerrow": player_row(),
                "gold": "25",
                "town": "",
                "unlocked": "",
            }
            return self._send(200, urlencode(params),
                              "application/x-www-form-urlencoded")

        # ---- REGISTER ----------------------------------------------------
        if ep == "register":
            STATE["chars"] = GUEST_CHAR
            save_state(STATE)
            params = {
                "status": "0", "chars": GUEST_CHAR,
                "username": "Guest", "id": "1", "motd": "Welcome to Straw Hat Samurai Duels (local solo build).",
                "magicnum": "0", "email": "solo@localhost", "verified": "1",
                "playertoken": "solo-token", "playerrow": player_row(),
                "gold": "25", "town": "", "unlocked": "",
            }
            return self._send(200, urlencode(params),
                              "application/x-www-form-urlencoded")

        # ---- GENERIC -----------------------------------------------------
        # Unknown endpoint: keep answering (the client ignores what it does
        # not parse) but SAY SO on the console. An unmapped hit is a finding,
        # not silence — Ch 7 of REVIVAL-COURSE.md: never guess blindly.
        print(f"[solo] unmapped {method} {self.path}", file=sys.stderr)
        return self._send(200, urlencode({"status": "0", "message": "ok"}),
                          "application/x-www-form-urlencoded")


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    os.chdir(ROOT)
    print(f"[solo] serving {ROOT}")
    print(f"[solo] game   : http://playerio.localhost:{PORT}/shs3_solo.swf")
    print(f"[solo] php    : http://playerio.localhost:{PORT}/solo/server/*.php")
    print(f"[solo] guest  : {GUEST_CHAR}")
    with Server(("127.0.0.1", PORT), Handler) as httpd:
        httpd.serve_forever()
