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
SERVER = os.path.join(REPO, "solo_server.py")
STATE = os.path.join(REPO, ".solo_state.json")
PORT = 8799
ORIGIN_OK = "http://playerio.localhost:%d" % PORT
ORIGIN_BAD = "http://evil.example"


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


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Never leave the operator's save file altered, even on a crash.
        cls.backup = None
        if os.path.isfile(STATE):
            fd, cls.backup = tempfile.mkstemp(prefix="solo_state_backup_")
            os.close(fd)
            shutil.copy2(STATE, cls.backup)

        cls.proc = subprocess.Popen(
            [sys.executable, SERVER, str(PORT)],
            cwd=REPO,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", PORT), timeout=0.2):
                    return
            except OSError:
                if cls.proc.poll() is not None:
                    break
                time.sleep(0.1)
        cls.proc.kill()
        raise RuntimeError("solo_server.py did not start on port %d" % PORT)

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.proc.kill()
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
