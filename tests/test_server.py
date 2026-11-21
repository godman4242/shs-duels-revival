#!/usr/bin/env python3
"""Black-box tests for solo_server.py.

The server is started as a subprocess on its own port; nothing here imports
solo_server. Run directly:

    python3 tests/test_server.py
"""
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# SOLO_SERVER lets a red-proof run point at an older copy of the server.
SERVER = os.environ.get("SOLO_SERVER") or os.path.join(REPO, "solo_server.py")
STATE = os.path.join(REPO, ".solo_state.json")
PORT = 8799
ORIGIN_OK = "http://playerio.localhost:%d" % PORT
ORIGIN_BAD = "http://evil.example"


def raw_status(method, path, headers, body=b""):
    """Send a hand-built request so the Host header can be forged."""
    sock = socket.create_connection(("127.0.0.1", PORT), timeout=10)
    try:
        head = "%s %s HTTP/1.0\r\n" % (method, path)
        for key, value in headers:
            head += "%s: %s\r\n" % (key, value)
        if body:
            head += "Content-Length: %d\r\n" % len(body)
        head += "\r\n"
        sock.sendall(head.encode("latin-1") + body)
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
    finally:
        sock.close()
    return data.split(b"\r\n", 1)[0].decode("latin-1")


def get(path, origin=None):
    """GET a path verbatim; return (status, Allow-Origin header, body)."""
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path))
    if origin:
        req.add_header("Origin", origin)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.headers.get("Access-Control-Allow-Origin"), resp.read()
    except urllib.error.HTTPError as err:
        return err.code, err.headers.get("Access-Control-Allow-Origin"), err.read()


def post(path, body, origin=None):
    """POST a form body; return (status, Allow-Origin header, body)."""
    req = urllib.request.Request(
        "http://127.0.0.1:%d%s" % (PORT, path),
        data=body.encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    if origin:
        req.add_header("Origin", origin)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.headers.get("Access-Control-Allow-Origin"), resp.read()
    except urllib.error.HTTPError as err:
        return err.code, err.headers.get("Access-Control-Allow-Origin"), err.read()


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Never leave the operator's save file altered, even on a crash.
        # addClassCleanup runs even when setUpClass itself raises, where
        # tearDownClass would not.
        cls.backup = None
        if os.path.isfile(STATE):
            fd, cls.backup = tempfile.mkstemp(prefix="solo_state_backup_")
            os.close(fd)
            shutil.copy2(STATE, cls.backup)
        cls.addClassCleanup(cls._restore_state)

        probe = socket.socket()
        probe.settimeout(0.2)
        in_use = probe.connect_ex(("127.0.0.1", PORT)) == 0
        probe.close()
        if in_use:
            raise RuntimeError("port %d is already in use; stop the other server" % PORT)

        # An ordinary-looking link that resolves outside the repo: only the
        # realpath confinement check can refuse it.
        cls.link = os.path.join(REPO, "escape_link_%d" % os.getpid())
        try:
            os.symlink("/etc/passwd", cls.link)
            cls.addClassCleanup(os.unlink, cls.link)
        except (OSError, NotImplementedError):
            cls.link = None

        cls.proc = subprocess.Popen(
            [sys.executable, SERVER, str(PORT)],
            cwd=REPO,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        cls.addClassCleanup(cls._stop_server)

        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", PORT), timeout=0.2):
                    if cls.proc.poll() is None:
                        return
                    break
            except OSError:
                if cls.proc.poll() is not None:
                    break
                time.sleep(0.1)
        raise RuntimeError("solo_server.py did not start on port %d" % PORT)

    @classmethod
    def _stop_server(cls):
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.proc.kill()

    @classmethod
    def _restore_state(cls):
        if cls.backup:
            shutil.copy2(cls.backup, STATE)
            os.unlink(cls.backup)
        elif os.path.isfile(STATE):
            os.unlink(STATE)

    def test_traversal_is_refused(self):
        # /etc/passwd exists outside the repo, so a 404 would be the wrong reason.
        status, _, _ = get("/../../../../etc/passwd")
        self.assertEqual(status, 403)

    def test_encoded_traversal_is_refused(self):
        # Proves unquote-then-realpath: un-decoded, this path has no dot segment.
        status, _, _ = get("/%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2fetc/passwd")
        self.assertEqual(status, 403)

    def test_symlink_escape_is_refused(self):
        # The dot rule cannot see this one: the name is ordinary and the path
        # holds no dot segment, so only realpath confinement can catch it.
        if not self.link:
            self.skipTest("symlinks unavailable on this platform")
        status, _, _ = get("/" + os.path.basename(self.link))
        self.assertEqual(status, 403)

    def test_hidden_file_is_refused(self):
        status, _, _ = get("/.solo_state.json")
        self.assertEqual(status, 403)

    def test_head_hidden_file_is_refused(self):
        # HEAD must not become a side door around the dot-segment rule.
        req = urllib.request.Request(
            "http://127.0.0.1:%d/.solo_state.json" % PORT, method="HEAD"
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                status = resp.status
        except urllib.error.HTTPError as err:
            status = err.code
        self.assertEqual(status, 403)

    def test_evil_origin_gets_no_cors_grant(self):
        status, allow_origin, _ = get("/index.html", origin=ORIGIN_BAD)
        self.assertEqual(status, 200)
        self.assertIsNone(allow_origin)

    def test_allowed_origin_is_echoed(self):
        status, allow_origin, _ = get("/index.html", origin=ORIGIN_OK)
        self.assertEqual(status, 200)
        self.assertEqual(allow_origin, ORIGIN_OK)

    def test_foreign_host_is_refused(self):
        # A name pointed at 127.0.0.1 (DNS rebinding) must not be served.
        status_line = raw_status(
            "GET", "/index.html", [("Host", "evil.example:%d" % PORT)]
        )
        self.assertIn(" 403 ", status_line)

    def test_cross_origin_save_is_refused(self):
        # CORS only hides the reply; a hostile page can still POST here.
        # login.php is a live state-writing endpoint (the guest flow never
        # calls it, but the account flow does).
        status, _, _ = post(
            "/solo/server/login.php",
            "charname=guest",
            origin=ORIGIN_BAD,
        )
        self.assertEqual(status, 403)

    def test_removed_endpoint_falls_through_to_generic(self):
        # The five dead PHP handlers were deleted; an unknown endpoint must
        # still answer with the generic OK rather than a 404 or an error.
        status, _, body = get("/solo/server/getgold.php")
        self.assertEqual(status, 200)
        self.assertIn(b"message=ok", body)

    def test_oversized_body_is_rejected_before_read(self):
        # Headers only: the server must answer 413 without waiting for the body.
        sock = socket.create_connection(("127.0.0.1", PORT), timeout=10)
        try:
            sock.sendall(
                b"POST /index.html HTTP/1.0\r\n"
                b"Host: 127.0.0.1\r\n"
                b"Content-Type: application/x-www-form-urlencoded\r\n"
                b"Content-Length: 11534336\r\n\r\n"
            )
            data = b""
            while b"\r\n\r\n" not in data:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
        finally:
            sock.close()
        status_line = data.split(b"\r\n", 1)[0].decode("latin-1")
        self.assertIn(" 413 ", status_line)


if __name__ == "__main__":
    unittest.main(verbosity=2)
