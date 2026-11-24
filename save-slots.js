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

  /* The game names the character object after the character: shsd_<charname>.
   * "guest" is only the default name. A build that names the character
   * differently must still be seen, or the start menu calls the game
   * unplayable and offers to delete the index. */
  function allKeys(st) {
    if (typeof st.length === "number" && typeof st.key === "function") {
      var out = [];
      for (var i = 0; i < st.length; i++) out.push(st.key(i));
      return out;
    }
    return typeof st.keys === "function" ? st.keys() : [];
  }

  /* The index (shsd) records the active character's name; that name is the
   * suffix of the object the game will load. Reading it is the only way to
   * know which shsd_<name> wins when more than one exists. */
  function indexCharname(st) {
    var b64 = st.getItem(K_INDEX);
    if (!b64) return null;
    try {
      var raw = (typeof atob === "function") ? atob(b64) : null;
      if (!raw) return null;
      var at = raw.indexOf("charname");
      if (at < 0) return null;
      var p = at + "charname".length;
      if (raw.charCodeAt(p) !== 6) return null;   // AMF3 string marker
      p += 1;
      var u = raw.charCodeAt(p), len;
      if (u < 0x80) { len = u >> 1; p += 1; }
      else { len = (((u & 0x7f) << 7) | raw.charCodeAt(p + 1)) >> 1; p += 2; }
      var name = raw.substr(p, len);
      return name || null;
    } catch (e) {
      return null;
    }
  }

  function charKey(st) {
    var name = indexCharname(st);
    if (name) {
      var key = PREFIX + "shsd_" + name;
      if (st.getItem(key)) return key;
    }
    if (st.getItem(K_CHAR)) return K_CHAR;
    var found = null;
    var keys = allKeys(st);
    for (var i = 0; i < keys.length; i++) {
      var k = keys[i];
      if (k && k.indexOf(PREFIX + "shsd_") === 0 && k !== K_CHAR) {
        if (found) return null;   // more than one character; never guess
        found = k;
      }
    }
    return found;
  }

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

  /* The character currently in play, or null if the browser has none.
   * `complete` is false when the index is missing — a character without its
   * index is not a loadable state, so callers must not offer it. */
  function current(st) {
    var key = charKey(st);
    var save = key ? st.getItem(key) : null;
    if (!save) return null;
    var index = st.getItem(K_INDEX);
    return { save: save, index: index, complete: !!index };
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
    /* Starting a new character twice without playing in between must not
       leave two identical entries: refresh the newest one instead. */
    if (list.length && list[0].save === slot.save && list[0].index === slot.index) {
      list[0].ts = slot.ts;
      writeSlots(st, list);
      return list[0];
    }
    list.unshift(slot);
    writeSlots(st, list);
    return slot;
  }

  /* Remove the pair together. Measured: this is the only safe way to ask the
   * game for a new character; clearing the character alone wedges the boot. */
  function clearCurrent(st) {
    var key = charKey(st);
    if (key) st.removeItem(key);
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
    st.setItem(charKey(st) || K_CHAR, slot.save);
    st.setItem(K_INDEX, slot.index);
    list.splice(i, 1);
    writeSlots(st, list);
    return slot;
  }

  /* Put a saved character back in play, filing whatever is in play now.
   * The start menu and the saves page both switch characters, so the swap is
   * written here once instead of twice. Nothing moves when the slot is gone
   * or incomplete: a failed switch must not file the current character.
   * Returns the restored slot, or null. */
  function activate(st, ts) {
    var list = readSlots(st);
    var target = null;
    for (var i = 0; i < list.length; i++) {
      if (list[i].ts === ts) { target = list[i]; break; }
    }
    if (!target || typeof target.index !== "string" || !target.index) return null;
    var cur = current(st);
    if (cur && cur.complete) stash(st);
    return restore(st, ts);
  }

  /* Drop one slot for good. Returns it, or null when it was not there. */
  function forget(st, ts) {
    var list = readSlots(st);
    for (var i = 0; i < list.length; i++) {
      if (list[i].ts === ts) {
        var gone = list.splice(i, 1)[0];
        writeSlots(st, list);
        return gone;
      }
    }
    return null;
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
    restore: restore,
    activate: activate,
    forget: forget
  };
  root.SaveSlots = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
