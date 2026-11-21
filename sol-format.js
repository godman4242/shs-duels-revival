/* Reader for the .sol files Ruffle keeps in localStorage for this game.
 *
 * A .sol ("local shared object", the Flash save-file format) starts with:
 *   00 BF | u32 (total length - 6) | "TCSO" | 00 04 00 00 | u32 nameLen | name | records
 * Records are AMF3-like; we only need one string record, playerStats.
 *
 * Works in the browser (window.SolFormat) and in Node (module.exports) so the
 * offsets can be pinned by a test instead of by eye.
 */
(function (root) {
  "use strict";

  function u32(bin, o) {
    return ((bin.charCodeAt(o) << 24) >>> 0) +
           (bin.charCodeAt(o + 1) << 16) +
           (bin.charCodeAt(o + 2) << 8) +
            bin.charCodeAt(o + 3);
  }

  /* Describe a save from its base64 form. Throws on anything that is not a
     well-formed .sol. playerStats is a '|'-separated field list; field 10
     (0-based) is the level and field 11 is the on-screen COINS counter. */
  function parseSol(b64) {
    var bin;
    try { bin = atob(b64.trim()); } catch (e) { throw new Error("not base64 data"); }
    if (bin.length < 19) throw new Error("file is too short");
    if (bin.charCodeAt(0) !== 0 || bin.charCodeAt(1) !== 0xBF) throw new Error("missing .sol header");
    if (u32(bin, 2) + 6 !== bin.length) throw new Error("length header does not match the file (truncated?)");
    if (bin.substr(6, 4) !== "TCSO") throw new Error("missing TCSO marker");

    var nameLen = u32(bin, 14);
    if (nameLen > 200 || 18 + nameLen > bin.length) throw new Error("corrupt object name");
    var info = { name: bin.substr(18, nameLen), size: bin.length, level: null, coins: null };

    var at = bin.indexOf("playerStats");
    if (at >= 0) {
      var p = at + "playerStats".length;
      if (bin.charCodeAt(p) === 6) {
        p += 1;
        var u = bin.charCodeAt(p), len;
        if (u < 0x80) { len = u >> 1; p += 1; }
        else { len = (((u & 0x7f) << 7) | bin.charCodeAt(p + 1)) >> 1; p += 2; }
        var f = bin.substr(p, len).split("|");
        if (f.length > 11) { info.level = f[10]; info.coins = f[11]; }
      }
    }
    return info;
  }

  function bytesToB64(bytes) {
    var s = "", chunk = 0x8000;
    for (var i = 0; i < bytes.length; i += chunk) {
      s += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
    }
    return btoa(s);
  }

  var api = { parseSol: parseSol, bytesToB64: bytesToB64 };
  root.SolFormat = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
