# Straw Hat Samurai: Duels — User Guide

## 1. Quick start

1. Clone the repo
2. Run the launcher for your OS
3. Your browser opens the game
4. Click **Play as Guest**

That is it. You do not need to install Flash or anything else — the browser player (Ruffle) is included.

## 2. Commands

**macOS / Linux:**
```bash
./play.sh
```

**Windows:**
```bat
play.bat
```

To stop the game, close the launcher terminal/window.

## 3. First-time hosts-file fix (rare)

The game checks that its URL contains `playerio`. We use `http://playerio.localhost:8765/`, and on most modern computers `*.localhost` already points to `127.0.0.1`.

If your browser says it cannot find `playerio.localhost`, add one line to your hosts file:

```
127.0.0.1  playerio.localhost
```

- **macOS / Linux:** `sudo nano /etc/hosts`, paste the line, save (Ctrl+O, Enter, Ctrl+X).
- **Windows:** run Notepad as Administrator, open `C:\Windows\System32\drivers\etc\hosts`, paste the line, save.

Then re-run `./play.sh` / `play.bat`.

## 4. What you will see

After clicking **Play as Guest**, the game auto-logs you in and drops you into the overworld. You can:
- move around,
- talk to NPCs,
- enter quests,
- use skills and shops,
- close and reopen the game — your Guest save is still there.

## 5. Saves

Your progress is kept by your browser, for the game's address (`playerio.localhost:8765`).
It is not a file next to `play.py`, and deleting `.solo_state.json` does not touch it.
Clearing this site's data wipes the character.

Open **Save Manager** by right-clicking the game. Besides an `analytics` entry, the list
has two rows that matter:

- `shsd` — the save index (the character's name). **Keep it**: without any save the
  Save Manager menu entry disappears.
- `shsd_<name>` — the character itself (level, coins, items, quests).

**Back up** — click the **download arrow** on the `shsd_<name>` row. That writes a `.sol`
file you can keep. Do not use "Download all save files": it writes a zip this build
cannot read back.

You can keep **as many `.sol` backups as you like** and restore whichever one you want;
only one character is active in the game at a time.

**Restore** — click the **file icon** on the same row, choose the `.sol`, confirm the
reload prompt, then reload the page. The backup replaces whatever progress is there now.

**Delete** — click the **trash icon**. It asks first, and it cannot be undone, so
download a backup before you delete. With the character row gone, the next reload starts
a fresh level-1 character (the bare `shsd` row keeps the menu reachable).

**All saves on one page** — open `http://playerio.localhost:8765/saves.html`. It lists
every save in this browser (name, level, coins), downloads any of them as a `.sol`, and
imports one back — including when the save is gone from the list. Close the game tab
before importing: a running game writes its own copy back over the import.

### Characters — new character, and switching back

Once there is a character in this browser, the game page opens on a **start menu**:

- **Continue** — plays the character that is loaded now; its level and coins are on the button.
- **Start a new character** — files the current character under *Saved characters* and
  starts a fresh level-1 game. Nothing is lost.
- **Saved characters** — one entry per filed character, with level, coins and when it was
  saved. Click one to put it back in play; whatever was in play is filed away instead.

The first visit in a clean browser skips the menu and goes straight into the game.

*Saved characters* live in this browser. They are not the same thing as **Download**ed
`.sol` files, which are separate copies you keep on disk.

## 6. Troubleshooting

| Problem | Fix |
|---|---|
| Browser says “Site-locked” | Make sure the URL is `http://playerio.localhost:8765/`, not `http://localhost:8765/`. |
| Browser cannot connect | The server might not have started. Re-run `./play.sh` / `play.bat`. |
| `python3` not found (Windows) | Install Python 3 from https://python.org and make sure “Add Python to PATH” is checked. |
| Game looks small / off-centre | Press F11 for full-screen, or click the Ruffle fullscreen button. |

## 7. What does not work

- **PvP / multiplayer:** the original PlayerIO backend is dead.
- **Premium purchases:** the payment server is dead; the game just pretends you have 0 coins.

If you only want to explore the solo world and quests, this build does exactly that.
