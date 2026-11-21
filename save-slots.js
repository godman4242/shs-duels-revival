/* Character slots for this build, kept beside the game's own save.
 *
 * The game holds exactly one character in browser storage:
 *   .../shsd              the index (charname, level)
 *   .../shsd_guest        the character itself
 * Switching characters means swapping both. Two rules were measured, not guessed:
 *   - removing BOTH keys makes the game create a brand-new character and boot;
 *   - removing only the character (leaving the index) leaves it stuck on LOADING.
 * So every path here keeps or clears the pair together.
 *
 * Backups live in one key of our own, "shs-solo/slots", so Ruffle never sees
 * them and they cannot be mistaken for a save object.
 *
 * Works in the browser (window.SaveSlots) and in Node (module.exports).
 */
(function (root) {
  "use strict";

  var PREFIX = "playerio.localhost/shs3_solo.swf/";
  var K_INDEX = PREFIX + "shsd";
  var K_CHAR = PREFIX + "shsd_guest";
  var K_SLOTS = "shs-solo/slots";

  function readSlots(st) {
    try {
      var raw = st.getItem(K_SLOTS);
      if (!raw) return [];
      var list = JSON.parse(raw);
      return Array.isArray(list) ? list.filter(function (e) {
        return e && typeof e.save === "string";
      }) : [];
    } catch (e) {
      return [];
    }
  }

  function writeSlots(st, list) {
    if (!list.length) { st.removeItem(K_SLOTS); return; }
    st.setItem(K_SLOTS, JSON.stringify(list));
  }

  /* The character currently in play, or null if the browser has none. */
  function current(st) {
    var save = st.getItem(K_CHAR);
    if (!save) return null;
    return { save: save, index: st.getItem(K_INDEX) };
  }

  /* Move the character in play into the slot list. Returns the new slot, or
   * null when there was nothing to move. The character is left in place. */
  function stash(st, ts) {
    var cur = current(st);
    if (!cur) return null;
    var list = readSlots(st);
    var slot = {
      ts: ts || new Date().toISOString(),
      save: cur.save,
      index: cur.index
    };
    list.unshift(slot);
    writeSlots(st, list);
    return slot;
  }

  /* Remove the pair together. Measured: this is the only safe way to ask the
   * game for a new character; clearing the character alone wedges the boot. */
  function clearCurrent(st) {
    st.removeItem(K_CHAR);
    st.removeItem(K_INDEX);
  }

  /* Put a slot back in play and take it out of the list. Refuses an incomplete
   * slot (no index) because a character without its index will not load. */
  function restore(st, ts) {
    var list = readSlots(st);
    var i = -1;
    for (var n = 0; n < list.length; n++) {
      if (list[n].ts === ts) { i = n; break; }
    }
    if (i < 0) return null;
    var slot = list[i];
    if (typeof slot.index !== "string" || !slot.index) return null;
    st.setItem(K_CHAR, slot.save);
    st.setItem(K_INDEX, slot.index);
    list.splice(i, 1);
    writeSlots(st, list);
    return slot;
  }

  var api = {
    PREFIX: PREFIX,
    K_INDEX: K_INDEX,
    K_CHAR: K_CHAR,
    K_SLOTS: K_SLOTS,
    readSlots: readSlots,
    current: current,
    stash: stash,
    clearCurrent: clearCurrent,
    restore: restore
  };
  root.SaveSlots = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
