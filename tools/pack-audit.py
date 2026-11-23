#!/usr/bin/env python3
"""pack-audit — does the game agree with every pack we ship it?

The game reads four kinds of pack:
  data/*.xml        item, npc, quest, room, skill, achievement tables
  lang/*.xml        the text strings those tables point at, by number
  res/*.swf         the art, sound and music libraries (obfuscated, decrypted
                    with the same per-file key the game uses)
  res-server1/      a second copy of the resource libraries

A name that the data or the code asks for but a pack does not contain is the
class of bug that black-screened Hiroshi's hut: nothing is missing from the
game, but two names disagree.

    python3 -I tools/pack-audit.py                # audit, exit 1 on a new gap
    python3 -I tools/pack-audit.py --self-test    # prove every check can go red
    python3 -I tools/pack-audit.py --write-baseline

tools/pack-audit-baseline.json pins today's known gaps (missing art we cannot
invent); a gap that is NOT in the baseline fails, and a pinned gap that
disappears is reported so the baseline cannot rot.
"""
import argparse
import json
import os
import re
import struct
import sys
import xml.etree.ElementTree as ET
import zlib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(REPO, "tools", "pack-audit-baseline.json")


# ---------------------------------------------------------------- resource SWFs

def _swf_body(path):
    """Decrypted, decompressed body of a resource SWF, or None."""
    raw = open(path, "rb").read()
    if not raw.startswith(b"CWS"):
        return None
    key = ord(os.path.basename(path)[1])       # second character of the filename
    body = bytearray(raw)
    for i in range(3, min(256, len(body))):
        if i % 11 == 0 and i + 256 < len(body):
            body[i], body[i + 256] = body[i + 256], body[i]
        body[i] ^= key
    for candidate in (bytes(body), bytes(raw)):   # library packs are obfuscated,
        try:                                      # the game build is not
            return zlib.decompress(candidate[8:])
        except zlib.error:
            pass
    return None


def swf_symbols(body):
    """Every name a library exports (its SymbolClass tag), e.g. BG_HutInside."""
    if not body:
        return set()
    nbits = body[0] >> 3
    i = (5 + 4 * nbits + 7) // 8 + 4          # skip frame size/rate/count
    names = set()
    while i + 2 <= len(body):
        v = struct.unpack_from("<H", body, i)[0]
        i += 2
        code, ln = v >> 6, v & 0x3F
        if ln == 0x3F:
            ln = struct.unpack_from("<I", body, i)[0]
            i += 4
        if code == 76:                        # SymbolClass
            n = struct.unpack_from("<H", body, i)[0]
            p, end = i + 2, i + ln
            for _ in range(n):
                p += 2
                e = body.index(b"\x00", p, end)
                names.add(body[p:e].decode("latin1"))
                p = e + 1
        i += ln
        if code == 0:
            break
    return names


def pack_symbols(path):
    return swf_symbols(_swf_body(path))


def numbered(symbols):
    """{'item': {2100, ...}, 'hat': {4031, ...}} from names like 'item2100'."""
    out = {}
    for s in symbols:
        m = re.match(r"^([a-z]+)(\d+)$", s)
        if m:
            out.setdefault(m.group(1), set()).add(int(m.group(2)))
    return out


# ---------------------------------------------------------------- data / lang

def load_xml(path):
    return ET.parse(path).getroot()


def text_ids(root, fields):
    """Every numeric text reference under the given `element/field` paths."""
    ids = set()
    for path in fields:
        el, _, fld = path.partition("/")
        for node in root.iter(el):
            v = (node.findtext(fld) or "").strip()
            if v.isdigit():
                ids.add(int(v))
    return ids


def lang_ids(path):
    raw = open(path, "rb").read()
    txt = raw.decode("utf-16") if raw[:2] == b"\xff\xfe" else raw.decode("utf-8", "replace")
    return {int(m.group(1)) for m in re.finditer(r'<trans-unit id="(\d+)"', txt)}


# ---------------------------------------------------------------- the checks
# Each check takes plain sets/dicts and returns (bad_set, detail); it never
# touches the disk, so --self-test can plant a fault and watch it go red.

def check_lang_ids(needed, have):
    return needed - have


def check_bg_classes(names, symbols):
    return names - symbols


def check_room_bg(used, defined):
    return used - defined


def check_item_sprites(items, num):
    """items: {id: type}; num: {'item': {..}, 'hat': {..}} from the pack."""
    have = set()
    for ids in num.values():
        have |= ids
    return {i for i in items if i not in have}


def check_npc_gear(ids, num):
    have = set()
    for s in num.values():
        have |= s
    return {i for i in ids if i not in have}


def check_quest_portraits(values, portraits, images):
    """A quest <img> resolves as portrait_<v> or image<v> (the episode stills)."""
    return {v for v in values if "portrait_" + v not in portraits and "image" + v not in images}


def check_achievement_images(imgs, symbols):
    return {i for i in imgs if "achievement%d" % i not in symbols}


# ---------------------------------------------------------------- audit

def audit(packs="res", baseline=None):
    """Run every check. Returns (results, current) where current is the raw
    findings so --write-baseline can record them."""
    root = REPO
    res = os.path.join(root, packs)
    results, current = [], {}

    def add(name, bad, detail=""):
        current[name] = sorted(bad) if isinstance(bad, (set, list, tuple)) else bad
        pinned = (baseline or {}).get(name)
        if not bad:
            note = ""
            if pinned:
                note = "baseline pins %d gap(s), now 0 — update the baseline" % len(pinned)
            results.append((name, True, note, []))
            return
        bad = sorted(bad)
        unpinned = [b for b in bad if b not in (pinned or [])]
        note = "%d gap(s)" % len(bad)
        if pinned and set(pinned) - set(bad):
            note += "; %d pinned gap(s) now resolved — update the baseline" % len(set(pinned) - set(bad))
        results.append((name, not unpinned, note, unpinned[:12]))

    # text ids the data points at
    fields = {
        "itemdata": ["item/name"],
        "skilldata": ["skill/displayname", "skill/desc", "level/desc"],
        "achievementdata": ["achievement/name", "achievement/desc"],
        "nodedata": ["node/name"],
        "npcdata": ["npc/name"],
    }
    needed = set()
    for f, paths in fields.items():
        needed |= text_ids(load_xml(os.path.join(root, "data", f + ".xml")), paths)
    add("lang-ids", check_lang_ids(needed, lang_ids(os.path.join(root, "lang", "shs3_en.xml"))))

    bg_pack = pack_symbols(os.path.join(res, "bgresource.swf"))
    bgdata = load_xml(os.path.join(root, "data", "bgdata.xml"))
    bg_names = {(e.findtext("name") or "").strip() for e in bgdata.findall("bg")}
    add("bg-classes", check_bg_classes(bg_names, bg_pack))

    # backgrounds the game build itself asks for that the pack does not have —
    # the hut bug's shape. Exclude names the build defines itself, all-caps
    # constants (BG_HUTINSIDE) and the game's own loader class.
    game = _swf_body(os.path.join(root, "shs3_solo.swf"))
    if game:
        own = swf_symbols(game)
        lits = {m.group(0).decode("latin1")
                for m in re.finditer(rb"(?<![A-Za-z0-9_])BG_[A-Za-z0-9_]+", game)}
        wanted = {n for n in lits - own if n != "BG_Loader" and not n.isupper()}
        add("game-bg-literals", check_bg_classes(wanted, bg_pack))

    used = set()
    for room in load_xml(os.path.join(root, "data", "nodedata.xml")).iter("room"):
        v = (room.findtext("bg") or "").strip()
        if v.isdigit():
            used.add(int(v))
    add("room-bg", check_room_bg(used, {int(e.findtext("id")) for e in bgdata.findall("bg")}))

    shs_num = numbered(pack_symbols(os.path.join(res, "shs3resource.swf")))
    items = {(int(e.findtext("id")), (e.findtext("type") or "").strip())
             for e in load_xml(os.path.join(root, "data", "itemdata.xml")).findall("item")}
    add("item-sprites", check_item_sprites({i for i, _ in items}, shs_num))

    gear = set()
    for npc in load_xml(os.path.join(root, "data", "npcdata.xml")).findall("npc"):
        mcs = npc.find("mcs")
        if mcs is None:
            continue
        for part in mcs:
            v = (part.text or "").strip()
            if v.isdigit():
                gear.add(int(v))
    add("npc-gear-sprites", check_npc_gear(gear, shs_num))

    img_pack = pack_symbols(os.path.join(res, "imageresource.swf"))
    quest = open(os.path.join(root, "data", "questdata.xml")).read()
    values = {v for v in re.findall(r"<img>([^<]*)</img>", quest) if v and not v.isdigit()}
    add("quest-portraits", check_quest_portraits(values, img_pack, img_pack))

    imgs = {int(e.findtext("img")) for e in
            load_xml(os.path.join(root, "data", "achievementdata.xml")).findall("achievement")
            if (e.findtext("img") or "").strip().isdigit()}
    ach_symbols = {"achievement%d" % i for i in shs_num.get("achievement", set())}
    add("achievement-images", check_achievement_images(imgs, ach_symbols))

    # two copies of one pack: report the divergence as a number, pin it
    other = os.path.join(root, "res-server1")
    if os.path.isdir(other):
        for lib in ("shs3resource", "imageresource"):
            a = pack_symbols(os.path.join(res, lib + ".swf"))
            b = pack_symbols(os.path.join(other, lib + ".swf"))
            current["copy-" + lib] = {"res": len(a), "res-server1": len(b),
                                      "only_res": len(a - b), "only_server1": len(b - a)}
            results.append(("copy-" + lib, current["copy-" + lib] == (baseline or {}).get("copy-" + lib),
                            "res=%d res-server1=%d (only res %d / only server1 %d)"
                            % (len(a), len(b), len(a - b), len(b - a)), []))

    return results, current


def selftest():
    """Plant one fault per check; every check must notice."""
    fails = []

    def expect(name, got, want_nonempty=True):
        ok = bool(got) == want_nonempty
        print("%-20s %s" % (name, "red as planted OK" if ok else "STAYED GREEN"))
        if not ok:
            fails.append(name)

    expect("lang-ids", check_lang_ids({1, 2, 3}, {1, 2}))
    expect("bg-classes", check_bg_classes({"BG_Forest"}, {"BG_Forest2"}))
    expect("room-bg", check_room_bg({4}, {5}))
    expect("item-sprites", check_item_sprites({2100, 9999}, {"item": {2100}}))
    expect("npc-gear-sprites", check_npc_gear({4031}, {"armor": {4032}}))
    expect("quest-portraits", check_quest_portraits({"kojiro"}, {"portrait_hiroshi"}, set()))
    expect("achievement-images", check_achievement_images({1}, {"achievement0"}))
    # and the SWF symbol reader itself, on a hand-built SymbolClass tag
    body = b"\x00" + b"\x00\x18\x00\x01"
    name = b"BG_Foo\x00"
    ln = 2 + 2 + len(name)
    body += struct.pack("<H", (76 << 6) | ln) + struct.pack("<HH", 1, 1) + name + b"\x00\x00"
    got = swf_symbols(body)
    print("%-20s %s" % ("swf-symbol-reader", "OK" if got == {"BG_Foo"} else "BROKEN %r" % got))
    if got != {"BG_Foo"}:
        fails.append("swf-symbol-reader")
    print("\nself-test:", "PASS" if not fails else "FAIL " + ", ".join(fails))
    return 0 if not fails else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packs", default="res", help="resource folder (default res)")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--write-baseline", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return selftest()

    base = json.load(open(BASELINE)) if os.path.exists(BASELINE) else None
    results, current = audit(args.packs, base)
    if args.write_baseline:
        json.dump(current, open(BASELINE, "w"), indent=1, sort_keys=True)
        print("baseline written:", BASELINE)

    red = 0
    for name, ok, note, detail in results:
        print("%-20s %-4s %s" % (name, "PASS" if ok else "FAIL", note))
        if detail:
            print("            ", detail)
        red += not ok
    print("\n%d check(s) red" % red)
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
