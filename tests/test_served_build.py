#!/usr/bin/env python3
"""Gate: the SWF being served must be the build committed to git.

Why this exists (measured 2026-11-24): a local byte-patch to the rebuilt SWF
silently changed its ActionScript class set, and the game then hung on its
loading screen. A local SWF patch is easy to forget, so this test compares
the bytes on disk with the blob at HEAD. If they differ, the suite fails
before a player meets a build that does not boot.

Run directly:

    python3 tests/test_served_build.py
"""
import os
import subprocess
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWF = "shs3_solo.swf"


class ServedBuildTest(unittest.TestCase):
    def setUp(self):
        if not os.path.isdir(os.path.join(REPO, ".git")):
            self.skipTest("not a git checkout; cannot compare with HEAD")
        if not os.path.isfile(os.path.join(REPO, SWF)):
            self.skipTest("%s is missing" % SWF)

    def git(self, *args):
        return subprocess.run(["git", "-C", REPO] + list(args),
                              capture_output=True, text=True)

    def test_served_swf_is_the_committed_build(self):
        head = self.git("rev-parse", "HEAD:" + SWF)
        if head.returncode != 0:
            self.skipTest("%s is not tracked at HEAD" % SWF)
        on_disk = self.git("hash-object", SWF)
        self.assertEqual(
            on_disk.stdout.strip(), head.stdout.strip(),
            "%s differs from the committed build. A local byte-patch can "
            "corrupt the build and hang the boot. Commit the rebuilt SWF, or "
            "restore it with `git checkout -- %s`."
            % (SWF, SWF))


if __name__ == "__main__":
    unittest.main(verbosity=2)
