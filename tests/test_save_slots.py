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
# The game names the character object after the character, so a build whose
# default name is not "guest" writes shsd_<name> instead.
K_ADMIN = "playerio.localhost/shs3_solo.swf/shsd_admin"
# Minimal indexes (base64 of AMF3 "charname" -> the name).
INDEX_ADMIN = "Y2hhcm5hbWUGC2FkbWlu"
INDEX_GUEST = "Y2hhcm5hbWUGC2d1ZXN0"
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
        self.assertEqual(got["out"], {"save": "char", "index": "idx", "complete": True})

    def test_current_is_null_without_a_character(self):
        got = self.call("return S.current(st);", {K_INDEX: "idx"})
        self.assertIsNone(got["out"])

    def test_current_flags_a_character_without_its_index(self):
        # The state a saves.html import used to be able to create: a character
        # whose index is missing, which the game will not load.
        got = self.call("return S.current(st);", {K_CHAR: "orphan"})
        self.assertEqual(got["out"]["complete"], False)

    def test_current_reads_a_character_saved_under_another_name(self):
        # A build whose default character name is not "guest" writes
        # shsd_<name>; the switcher must see it instead of calling the game
        # unplayable and offering to delete the index.
        got = self.call("return S.current(st);", {K_INDEX: "idx", K_ADMIN: "char"})
        self.assertEqual(got["out"], {"save": "char", "index": "idx", "complete": True})

    def test_current_prefers_the_character_named_in_the_index(self):
        # The index is authoritative: if it names "admin", the game loads
        # shsd_admin even when a stale shsd_guest also exists.
        got = self.call("return S.current(st);",
                        {K_INDEX: INDEX_ADMIN, K_ADMIN: "admin-char", K_CHAR: "guest-char"})
        self.assertEqual(got["out"],
                         {"save": "admin-char", "index": INDEX_ADMIN, "complete": True})

    def test_clear_removes_the_alternate_character_and_index(self):
        got = self.call("S.clearCurrent(st); return 'ok';",
                        {K_INDEX: "idx", K_ADMIN: "char", "other": "keep"})
        self.assertEqual(got["keys"], ["other"])

    def test_restore_writes_to_the_alternate_name(self):
        # Restoring must land on the key the game actually reads.
        init = {
            K_INDEX: "idx", K_ADMIN: "old",
            SLOTS: json.dumps([{"ts": "t1", "save": "new", "index": "newidx"}]),
        }
        got = self.call("return S.restore(st, 't1');", init)
        self.assertEqual(got["vals"][K_ADMIN], "new")
        self.assertNotIn(K_CHAR, got["keys"])

    def test_get_charname_reads_the_index(self):
        got = self.call("return S.getCharname(st);", {K_INDEX: INDEX_ADMIN})
        self.assertEqual(got["out"], "admin")

    def test_use_role_copies_the_character_and_sets_the_index(self):
        got = self.call(
            "return {ok: S.useRole(st, 'admin'), name: S.getCharname(st)};",
            {K_INDEX: INDEX_GUEST, K_CHAR: "guest-char"})
        self.assertTrue(got["out"]["ok"])
        self.assertEqual(got["out"]["name"], "admin")
        self.assertEqual(got["vals"][K_ADMIN], "guest-char")

    def test_use_role_fails_without_a_character(self):
        got = self.call("return S.useRole(st, 'admin');", {K_INDEX: INDEX_GUEST})
        self.assertFalse(got["out"])
        self.assertNotIn(K_ADMIN, got["keys"])

    def test_set_and_get_role(self):
        got = self.call("S.setRole(st, 'admin'); return S.getRole(st);", {})
        self.assertEqual(got["out"], "admin")

    def test_apply_role_renames_the_active_character(self):
        got = self.call(
            "S.setRole(st, 'admin'); return {ok: S.applyRole(st), name: S.getCharname(st)};",
            {K_INDEX: INDEX_GUEST, K_CHAR: "guest-char"})
        self.assertTrue(got["out"]["ok"])
        self.assertEqual(got["out"]["name"], "admin")
        self.assertEqual(got["vals"][K_ADMIN], "guest-char")

    def test_use_role_removes_the_old_character_after_renaming(self):
        """A leftover shsd_guest makes a cleared game look like it still has a
        character: charKey() falls back to it and the menu then claims the save
        is unloadable. The rename must move the character, not copy it."""
        got = self.call(
            "return S.useRole(st, 'admin');",
            {K_INDEX: INDEX_GUEST, K_CHAR: "guest-char"})
        self.assertTrue(got["out"])
        self.assertEqual(got["vals"][K_ADMIN], "guest-char")
        self.assertNotIn(K_CHAR, got["keys"])

    def test_role_needs_apply_when_the_game_created_a_guest(self):
        got = self.call(
            "S.setRole(st, 'admin'); return S.roleNeedsApply(st);",
            {K_INDEX: INDEX_GUEST, K_CHAR: "guest-char"})
        self.assertTrue(got["out"])

    def test_role_needs_apply_is_false_when_the_name_matches(self):
        got = self.call(
            "S.setRole(st, 'admin'); return S.roleNeedsApply(st);",
            {K_INDEX: INDEX_ADMIN, K_ADMIN: "admin-char"})
        self.assertFalse(got["out"])

    def test_role_needs_apply_is_false_without_a_chosen_role(self):
        got = self.call(
            "return S.roleNeedsApply(st);",
            {K_INDEX: INDEX_GUEST, K_CHAR: "guest-char"})
        self.assertFalse(got["out"])

    def test_role_needs_apply_is_false_without_a_character(self):
        got = self.call(
            "S.setRole(st, 'admin'); return S.roleNeedsApply(st);",
            {K_INDEX: INDEX_GUEST})
        self.assertFalse(got["out"])

    def test_use_role_files_the_character_it_replaces(self):
        got = self.call(
            "return S.useRole(st, 'admin');",
            {K_INDEX: INDEX_GUEST, K_CHAR: "guest-char", K_ADMIN: "old-admin"})
        self.assertTrue(got["out"])
        self.assertEqual(got["vals"][K_ADMIN], "guest-char")
        slots = json.loads(got["vals"][SLOTS])
        self.assertEqual(slots[0]["save"], "old-admin")

    def test_forget_drops_only_the_named_slot(self):
        init = {SLOTS: json.dumps([
            {"ts": "t1", "save": "one", "index": "i1"},
            {"ts": "t2", "save": "two", "index": "i2"},
        ])}
        got = self.call("return S.forget(st, 't1');", init)
        self.assertEqual(got["out"]["save"], "one")
        left = json.loads(got["vals"][SLOTS])
        self.assertEqual([s["ts"] for s in left], ["t2"])

    def test_forget_of_an_unknown_slot_changes_nothing(self):
        init = {SLOTS: json.dumps([{"ts": "t1", "save": "one", "index": "i1"}])}
        got = self.call("return S.forget(st, 'nope');", init)
        self.assertIsNone(got["out"])
        self.assertEqual(len(json.loads(got["vals"][SLOTS])), 1)

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

    def test_stashing_the_same_character_twice_keeps_one_entry(self):
        # "Start a new character" twice without playing in between.
        init = {
            K_INDEX: "idx", K_CHAR: "char",
            SLOTS: json.dumps([{"ts": "old", "save": "char", "index": "idx"}]),
        }
        got = self.call("return S.stash(st, 'new');", init)
        slots = json.loads(got["vals"][SLOTS])
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]["ts"], "new")

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

    # The start menu and the saves page both offer "switch character". Both
    # must do the same swap, so the rule lives in one function, `activate`.

    def test_activate_swaps_a_saved_character_into_play(self):
        init = {
            K_INDEX: "cur-index", K_CHAR: "cur-char",
            SLOTS: json.dumps([{"ts": "t1", "save": "old-char", "index": "old-index"}]),
        }
        got = self.call("return S.activate(st, 't1');", init)
        self.assertEqual(got["out"]["save"], "old-char")
        self.assertEqual(got["vals"][K_CHAR], "old-char")
        self.assertEqual(got["vals"][K_INDEX], "old-index")
        filed = json.loads(got["vals"][SLOTS])      # what was in play is kept
        self.assertEqual([s["save"] for s in filed], ["cur-char"])

    def test_activate_over_an_unloadable_character_discards_it(self):
        # A character without its index cannot load; filing it would only
        # offer a broken slot back to the player.
        init = {
            K_CHAR: "orphan",
            SLOTS: json.dumps([{"ts": "t1", "save": "good", "index": "good-index"}]),
        }
        got = self.call("return S.activate(st, 't1');", init)
        self.assertEqual(got["vals"][K_CHAR], "good")
        self.assertNotIn(SLOTS, got["keys"])

    def test_activate_of_an_unknown_slot_changes_nothing(self):
        # A stale page (another tab forgot the slot) must not file the
        # character in play on its way to a failure.
        init = {K_INDEX: "idx", K_CHAR: "char"}
        got = self.call("return S.activate(st, 'nope');", init)
        self.assertIsNone(got["out"])
        self.assertEqual(got["vals"][K_CHAR], "char")
        self.assertNotIn(SLOTS, got["keys"])

    def test_corrupt_slot_data_reads_as_empty(self):
        got = self.call("return S.readSlots(st);", {SLOTS: "{not json"})
        self.assertEqual(got["out"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
