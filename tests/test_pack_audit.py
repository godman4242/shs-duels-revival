"""The pack-audit gate must be green, and must be able to go red.

See tools/pack-audit.py — it checks that the data packs, the language pack and
the five resource libraries name the same things. A red audit means a name the
game asks for is absent from a pack: the Hiroshi's-hut failure mode.
"""
import os
import subprocess
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, "tools", "pack-audit.py")


def run(*args):
    return subprocess.run([sys.executable, "-I", TOOL, *args], cwd=REPO,
                          capture_output=True, text=True)


class PackAuditTest(unittest.TestCase):
    def test_audit_is_green(self):
        p = run()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("0 check(s) red", p.stdout)

    def test_every_check_can_go_red(self):
        p = run("--self-test")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("self-test: PASS", p.stdout)


if __name__ == "__main__":
    unittest.main()
