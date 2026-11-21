# Straw Hat Samurai: Duels Revival

**Straw Hat Samurai: Duels Revival** — searchable as "shs: d" — the 2015 PlayerIO Flash game, playable offline again. The original client, patched to run without its servers, plus a small local stand-in server.

## Play it (any OS)

You only need **Git** and **Python 3**.

**macOS / Linux:**
```bash
git clone https://github.com/godman4242/shs-duels-revival.git
cd shs-duels-revival
./play.sh
```

**Windows:**
```bat
git clone https://github.com/godman4242/shs-duels-revival.git
cd shs-duels-revival
play.bat
```

Your default browser opens to the game. Click **Play as Guest** — it runs entirely on your machine; nothing phones home.

If `playerio.localhost` does not load, add `127.0.0.1 playerio.localhost` to your hosts file once:
- **macOS/Linux:** `sudo nano /etc/hosts`
- **Windows:** edit `C:\Windows\System32\drivers\etc\hosts` as Administrator

## What works vs. what does not

| Feature | Status |
|---|---|
| Solo overworld, quests, NPCs, shops, skills | ✅ works |
| Saves (Guest character) | ✅ works — kept in this browser, for this site |
| Sound, music, art, UI | ✅ works |
| PvP / multiplayer | ❌ retired — the PlayerIO backend is gone for good |
| Premium currency / payments | ❌ the payment server is dead — ignored |

Your character lives in this browser, for the site `playerio.localhost:8765` — clearing
this site's data wipes it. Right-click the game → **Save Manager** to back up, restore or
delete a character: the download arrow writes a `.sol` file, the file icon restores one,
the trash icon deletes one (see `USER_GUIDE.md` §5 for the exact steps).

## Project layout

| Path | What it is |
|---|---|
| `shs3_solo.swf` | The patched game (URL redirect + offline-logic patches — see `patches/`) |
| `shs3_decoded.swf` | Uncompressed original game data the patched build was made from (study copy — not needed to play) |
| `solo_server.py` | Tiny Python server that pretends to be the dead PHP backend and serves the assets |
| `play.py` / `play.sh` / `play.bat` | One-click launcher for your OS |
| `index.html` + `ruffle.js` + `*.wasm` | Browser-based Flash player (Ruffle) — no separate install needed |
| `res/`, `data/`, `lang/` | Game assets mirrored locally |
| `patches/` | The exact source changes made to the game to make it run offline |

## Need more detail?

See **[USER_GUIDE.md](<USER_GUIDE.md>)** for setup, controls, what you will see on screen, and troubleshooting.

### How we did it — full course

Want the whole story? **[Reviving a Dead Game](<REVIVAL-COURSE.md>)** is a build-along course on exactly how this rebuild was made — diagnosing the death, decompiling the client, reading the dead server's protocol out of the game's own parsing code, the 43-character byte patch, the two emulators, honest limits, and a reusable 7-step playbook for reviving other dead games.

- **Read on GitHub:** [REVIVAL-COURSE.md](<REVIVAL-COURSE.md>)
- **Download (PDF, recordings-free):** [REVIVAL-COURSE.pdf](<REVIVAL-COURSE.pdf>)

## Technical preservation notes

This repo preserves the compiled SWF and the surviving assets so the game can still be played after the original servers shut down. The PHP backend (`strawhatsamuraiduels.com`) is NXDOMAIN and the PlayerIO RPC backend returns HTTP 500, so the online features are gone. The local server emulates just enough of the login/data API to make the solo portion of the game work.

This is a fan preservation copy, not an official release, and it is not affiliated
with the original studio. The game and its assets are not open source; only this
repository's own code is (see `LICENSE`). The bundled Flash player is Ruffle, under
its own licence (`RUFFLE-LICENSE.txt`).

For the exact source changes that make the game run offline, see `patches/`; for
setup, controls and troubleshooting, see `USER_GUIDE.md`.
