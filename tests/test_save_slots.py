#!/usr/bin/env python3
"""Tests for save-slots.js — the character switcher behind the start menu.

The rules these pin were measured in a real browser, not assumed:

  * the game keeps one character in two keys, `shsd` (index) and `shsd_guest`;
  * removing BOTH makes the game create a new character and boot;
  * removing only the character leaves it stuck on LOADING.

The last one is why `clearCurrent` must never touch one key alone.

Run directly:

    python3 tests/test_save_slots.py
"""
import json
import os
import shutil
import subprocess
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE = os.path.join(REPO, "save-slots.js")
NODE = shutil.which("node") or shutil.which("nodejs")

# A Map-backed stand-in for localStorage.
HARNESS = r"""
function mk(init) {
  const m = new Map(Object.entries(init || {}));
  return {
    getItem: k => (m.has(k) ? m.get(k) : null),
    setItem: (k, v) => { m.set(k, String(v)); },
    removeItem: k => { m.delete(k); },
    keys: () => [...m.keys()],
  };
}
"""


def run_js(body, init=None):
    """Execute `body` with `S` (the module) and `st` (fake storage) in scope."""
    script = (
        "const S = require(process.argv[1]);" + HARNESS +
        "const st = mk(" + json.dumps(init or {}) + ");" +
        "const out = (() => {" + body + "})();" +
        "process.stdout.write(JSON.stringify({out: out, keys: st.keys(),"
        " vals: Object.fromEntries(st.keys().map(k => [k, st.getItem(k)]))}));"
    )
    return subprocess.run(
        [NODE, "-e", script, MODULE], capture_output=True, text=True, timeout=30
    )


K_INDEX = "playerio.localhost/shs3_solo.swf/shsd"
K_CHAR = "playerio.localhost/shs3_solo.swf/shsd_guest"
SLOTS = "shs-solo/slots"


class SaveSlotsTest(unittest.TestCase):
    def setUp(self):
        if not NODE:
            self.skipTest("node is not installed; cannot exercise save-slots.js")
        self.assertTrue(os.path.isfile(MODULE), "save-slots.js is missing")

    def call(self, body, init=None):
        res = run_js(body, init)
        self.assertEqual(res.returncode, 0, res.stderr)
        return json.loads(res.stdout)

    def test_current_reads_both_keys(self):
        got = self.call("return S.current(st);", {K_INDEX: "idx", K_CHAR: "char"})
        self.assertEqual(got["out"], {"save": "char", "index": "idx"})

    def test_current_is_null_without_a_character(self):
        got = self.call("return S.current(st);", {K_INDEX: "idx"})
        self.assertIsNone(got["out"])

    def test_clear_removes_index_and_character_together(self):
        # Removing only the character wedges the game on LOADING (measured).
        got = self.call("S.clearCurrent(st); return 'ok';",
                        {K_INDEX: "idx", K_CHAR: "char", "other": "keep"})
        self.assertEqual(got["keys"], ["other"])

    def test_stash_keeps_the_character_in_play(self):
        got = self.call("return S.stash(st, '2026-11-21T10:00:00Z');",
                        {K_INDEX: "idx", K_CHAR: "char"})
        self.assertEqual(got["out"]["save"], "char")
        self.assertIn(K_CHAR, got["keys"])          # still playing
        self.assertIn(K_INDEX, got["keys"])

    def test_restore_swaps_both_keys_and_drops_the_slot(self):
        init = {
            K_INDEX: "new-index", K_CHAR: "new-char",
            SLOTS: json.dumps([{"ts": "t1", "save": "old-char", "index": "old-index"}]),
        }
        got = self.call("return S.restore(st, 't1');", init)
        self.assertEqual(got["out"]["save"], "old-char")
        self.assertNotIn(SLOTS, got["keys"])        # last slot consumed
        self.assertEqual(got["vals"][K_CHAR], "old-char")
        self.assertEqual(got["vals"][K_INDEX], "old-index")

    def test_restore_refuses_an_incomplete_slot(self):
        init = {
            K_CHAR: "keep-me",
            SLOTS: json.dumps([{"ts": "t1", "save": "orphan", "index": None}]),
        }
        got = self.call("return S.restore(st, 't1');", init)
        self.assertIsNone(got["out"])
        self.assertEqual(got["keys"], [K_CHAR, SLOTS])   # nothing moved

    def test_corrupt_slot_data_reads_as_empty(self):
        got = self.call("return S.readSlots(st);", {SLOTS: "{not json"})
        self.assertEqual(got["out"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
