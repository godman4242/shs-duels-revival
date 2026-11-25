#!/usr/bin/env python3
"""Gate: every command listed in README must exist in the game build.

The README table is generated from the game's chat parser, but it is plain
text that a later edit can corrupt. This test takes each `/command` row and
checks the token really appears inside `shs3_solo.swf` (CWS = zlib from byte
8). A typo or an invented command fails the suite.

It also fails if the table looks truncated (fewer than 50 rows).

Run directly:

    python3 tests/test_readme_commands.py
"""
import os
import re
import unittest
import zlib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(REPO, "README.md")
SWF = os.path.join(REPO, "shs3_solo.swf")


def readme_commands():
    with open(README, encoding="utf-8") as fh:
        text = fh.read()
    return re.findall(r"^\| `(/[a-z]+)`", text, re.M)


def swf_bytes():
    with open(SWF, "rb") as fh:
        blob = fh.read()
    if blob[:3] == b"CWS":
        return zlib.decompress(blob[8:])
    if blob[:3] == b"FWS":
        return blob[8:]
    return b""


class ReadmeCommandsTest(unittest.TestCase):
    def setUp(self):
        if not os.path.isfile(README):
            self.skipTest("README.md is missing")
        if not os.path.isfile(SWF):
            self.skipTest("shs3_solo.swf is missing")

    def test_every_readme_command_exists_in_the_build(self):
        cmds = readme_commands()
        self.assertEqual(len(cmds), len(set(cmds)),
                         "README lists the same command more than once")
        self.assertEqual(len(cmds), 81,
                         "README should list 81 commands; found %d" % len(cmds))
        raw = swf_bytes()
        self.assertTrue(raw, "could not read the SWF")
        missing = [c for c in cmds if c.encode() not in raw]
        self.assertEqual(
            missing, [],
            "README lists commands the build does not contain: %r" % missing)


if __name__ == "__main__":
    unittest.main(verbosity=2)
