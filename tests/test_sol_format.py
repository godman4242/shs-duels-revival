#!/usr/bin/env python3
"""Tests for sol-format.js — the .sol reader used by saves.html.

The offsets in that file were once wrong by four bytes, and the page silently
showed "?" instead of level and coins. These pin them.

A synthetic save is built here from the format measured on real files:
    00 BF | u32 (total-6) | "TCSO" | 00 04 00 00 | u32 nameLen | name | records
Records are keyed by a U29 length with no 0x06 marker; string values are
0x06 + U29 length + bytes. playerStats is 45 '|'-separated fields, field 10
(0-based) is the level, field 11 the coins, the last field the checksum
(sum of the others mod 54321).

Run directly:

    python3 tests/test_sol_format.py
"""
import base64
import json
import os
import shutil
import struct
import subprocess
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE = os.path.join(REPO, "sol-format.js")
NODE = shutil.which("node") or shutil.which("nodejs")


def u29(value):
    """Encode as Ruffle writes it: big-endian U29, low bit marks the last byte."""
    v = (value << 1) | 1
    if v < 0x80:
        return bytes([v])
    return bytes([0x80 | (v >> 7), v & 0x7F])


def stat_fields(level=3, coins=4242, n=45):
    fields = ["0"] * n
    fields[10] = str(level)
    fields[11] = str(coins)
    fields[-1] = "0"
    fields[-1] = str(sum(int(f) for f in fields[:-1]) % 54321)
    return fields


def make_sol(name="shsd_guest", level=3, coins=4242):
    stats = "|".join(stat_fields(level, coins))
    records = (u29(len("playerStats")) + b"playerStats"
               + b"\x06" + u29(len(stats)) + stats.encode())
    body = b"\x00\x04\x00\x00" + struct.pack(">I", len(name)) + name.encode() + records
    return b"\x00\xbf" + struct.pack(">I", len(body) + 4) + b"TCSO" + body


def call_parse(sol_bytes):
    """Run the real module under Node and return its parseSol() result."""
    b64 = base64.b64encode(sol_bytes).decode()
    script = (
        "const S = require(process.argv[1]);"
        "process.stdout.write(JSON.stringify(S.parseSol(process.argv[2])));"
    )
    out = subprocess.run(
        [NODE, "-e", script, MODULE, b64],
        capture_output=True, text=True, timeout=30,
    )
    return out


class SolFormatTest(unittest.TestCase):
    def setUp(self):
        if not NODE:
            self.skipTest("node is not installed; cannot exercise sol-format.js")
        self.assertTrue(os.path.isfile(MODULE), "sol-format.js is missing")

    def test_level_and_coins_are_read_from_the_right_fields(self):
        result = call_parse(make_sol(level=3, coins=4242))
        self.assertEqual(result.returncode, 0, result.stderr)
        info = json.loads(result.stdout)
        self.assertEqual(info["level"], "3")
        self.assertEqual(info["coins"], "4242")

    def test_object_name_comes_from_the_header(self):
        info = json.loads(call_parse(make_sol(name="shsd_kenshin")).stdout)
        self.assertEqual(info["name"], "shsd_kenshin")

    def test_size_is_the_byte_length(self):
        sol = make_sol()
        info = json.loads(call_parse(sol).stdout)
        self.assertEqual(info["size"], len(sol))

    def test_non_sol_data_is_rejected(self):
        out = call_parse(b"not a save file at all, not even close")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("header", out.stderr + out.stdout)

    def test_truncated_file_is_rejected(self):
        out = call_parse(make_sol()[:-5])
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("length header", out.stderr + out.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
