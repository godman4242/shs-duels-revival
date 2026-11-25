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

Your default browser opens to a start menu where you choose **Guest** or **Admin**
(Admin unlocks the dev commands — see [Roles](#roles-guest-or-admin)). It runs
entirely on your machine; nothing phones home.

If `playerio.localhost` does not load, add `127.0.0.1 playerio.localhost` to your hosts file once:
- **macOS/Linux:** `sudo nano /etc/hosts`
- **Windows:** edit `C:\Windows\System32\drivers\etc\hosts` as Administrator

## What works vs. what does not

| Feature | Status |
|---|---|
| Solo overworld, quests, NPCs, shops, skills | ✅ works |
| Saves (Guest or Admin character) | ✅ works — kept in this browser, for this site |
| Sound, music, art, UI | ✅ works |
| PvP / multiplayer | ❌ retired — the PlayerIO backend is gone for good |
| Premium currency / payments | ❌ the payment server is dead — ignored |

Your character lives in this browser, for the site `playerio.localhost:8765` — clearing
this site's data wipes it. Once a character exists, opening the game shows a start menu:
**Continue**, **Start a new character**, or pick one of your **saved characters** (each
keeps its level and coins; switching files the current one away).

For copies on disk, right-click the game → **Save Manager** (the download arrow writes a
`.sol` file, the file icon restores one), or open `/saves.html`: one page listing your saved
characters and the one in play, with Make active, Download, Forget and Import. See
`USER_GUIDE.md` §5 for the exact steps.

## Roles: Guest or Admin

Opening the game always shows a start menu with **Choose Guest or Admin**; you can also
open `/roles.html` directly.

| Role | What it is |
|---|---|
| **Guest** | The character in play, named `guest`. No dev commands. |
| **Admin** | The character in play, renamed `admin`. Unlocks the dev commands below. |

Switching roles **renames the character in play**, so it keeps its level, items and quests.
If a character already exists under the other name, it is kept in **Saved characters**
rather than overwritten. The choice sticks: the game always creates a Guest, so about ten
seconds after a new character appears the page reloads itself once, renames the character,
and drops you straight back into the game — you do not land on the start menu.

In game, type `/enableconsole dragon` in the chat box, then `/help`.

## Dev commands

These are the game's own commands, read from its chat parser. `[square brackets]` are
arguments. Commands marked *server-side* or *moderator only* needed the dead PlayerIO
backend and do nothing offline.

<!-- 81 in-game commands, taken from the game's own chat parser -->

### Dev commands (Admin only)

| Command | Arguments | What it does |
|---|---|---|
| `/aggro` | — | Enemies notice you again. |
| `/banplayer` | [name] [pass] | Bans a player (server-side; inert offline). |
| `/breakweapon` | — | Breaks the equipped weapon. |
| `/buffplayer` | [name] [buff] [duration] | Applies a buff to a player (server-side; inert offline). |
| `/changesex` | — | Flips the character's sex. |
| `/changestat` | [statid] [value] | Adds to an internal stat (negative values subtract). |
| `/clearquests` | — | Clears active and completed quests. |
| `/createrecallstone` | — | Gives a recall stone bound to this node. |
| `/createredeemcode` | [itemid] [times] [pass] | Creates a redeem code (server-side; inert offline). |
| `/createroomobject` | [objid] [props] [objname] | Spawns an object in the room. |
| `/disableconsole` | — | Turns the dev console off. |
| `/dropall` | — | Empties the inventory and quest items. |
| `/enablechikako` | — | Completes quest 20 (enables Chikako). |
| `/forgesword` | [level] | Generates a random sword. |
| `/getnodeid` | — | Prints the current node id. |
| `/getnodelevel` | — | Prints the current node's level. |
| `/getpos` | — | Prints your x position in the room. |
| `/getroomid` | — | Prints the current room id. |
| `/getroomobjects` | — | Lists the objects in the current room. |
| `/getroomwidth` | — | Prints the current room's width. |
| `/getterritoryid` | — | Prints the current territory id. |
| `/giveitem` | [itemid] [level] | Puts a specific item in the loot window (level defaults to yours). |
| `/givelegendaryitem` | [itemid] [level] | Generated legendary item in the loot window. |
| `/givequestitem` | — | Gives the latest NPC quest item. |
| `/giverandomlegendaryitem` | [level] | A random legendary item. |
| `/giverandomrareitem` | [level] | A random rare item. |
| `/giverareitem` | [itemid] [level] | Generated rare item in the loot window. |
| `/givetradequestitem` | — | Gives the latest trade quest item. |
| `/kickplayer` | [name] | Kicks a player (server-side; inert offline). |
| `/noaggro` | — | Enemies ignore you until /aggro. |
| `/refund` | [any] | Opens the Chikako refund window (the argument is required but ignored). |
| `/removeroomobject` | [objname] | Removes a room object by name. |
| `/replay` | [recording id] | Plays a recorded duel. |
| `/setdate` | [date] | Sets the in-game date. |
| `/setlevel` | [level] | Jumps your level to the number given. |
| `/setquest` | [questid] [step] | Sets a quest's active step. |
| `/setstat` | [statid] [value] | Sets an internal stat to a value. |
| `/sharedueltv` | — | Shares a duel to the TV feed (server-side; inert offline). |
| `/showbank` | — | Opens the bank. |
| `/teleport` | [tx] [ty] [nx] [ny] [room] | Teleports to a territory/node/room coordinate. |
| `/teleportplayer` | [name] | Pulls a player to you (server-side; inert offline). |
| `/testbg` | [bgid] | Loads a background id in the current room. |
| `/testcutscene` | — | Plays a test cutscene. |
| `/tteleport` | [tx] [ty] | Teleports to the town of a territory. |
| `/warcron` | [pass] | Triggers the war scheduler (server-side; inert offline). |
| `/whereis` | [territoryname] | Prints where a named territory is. |
| `/whereisplayer` | [name] | Asks where a player is (server-side; inert offline). |
| `/worldsim` | [pass] | Triggers the world simulation (server-side; inert offline). |

### Always available

| Command | Arguments | What it does |
|---|---|---|
| `/ally` | [npc] | Adds an NPC ally. |
| `/ban` | [name] | Bans a player from the channel (inert offline). |
| `/bow` | — | Emote: bow. |
| `/createprivate` | [channel] | Creates a private chat channel (inert offline). |
| `/emotes` | — | Lists the emotes. |
| `/enableconsole` | dragon | Unlocks the dev console (needs the character named admin). |
| `/fart` | — | Emote/sound: fart. |
| `/fullmuteplayer` | [name] | Fully mutes a player. Moderator buff only (inert offline). |
| `/gangnamstyle` | — | Emote: dance, with music. |
| `/gotohell` | — | Teleports you to the hell room. Moderator + special weapon only. |
| `/help` | — | Prints the command list. |
| `/hidehud` | — | Hides the HUD (cutscene mode). |
| `/invite` | [name] | Invites a player to the channel (inert offline). |
| `/join` | [channel] | Joins or creates a chat channel (inert offline). |
| `/kick` | [name] | Kicks a player from the channel (inert offline). |
| `/kneel` | — | Emote: kneel. |
| `/leave` | — | Leaves the chat channel (inert offline). |
| `/list` | — | Lists chat channels (server-side; inert offline). |
| `/muteplayer` | [name] | Mutes a player. Moderator buff only (inert offline). |
| `/recall` | — | Returns you to the nearest dojo (level 3+). |
| `/rest` | — | Emote: lie down. |
| `/sendtohell` | [name] | Sends a player to the hell room. Moderator + special weapon only. |
| `/seppuku` | — | Emote: seppuku. |
| `/shoulderweapon` | — | Emote: shoulder the weapon. |
| `/showallonline` | — | Lists all online players (inert offline). |
| `/showally` | — | Lists your allies. |
| `/sit` | — | Emote: sit (random variant). |
| `/stand` | — | Emote: stand up. |
| `/stopally` | [npc] | Removes an NPC ally. |
| `/unban` | [name] | Unbans a player from the channel (inert offline). |
| `/waterfall` | — | Teleports to the waterfall node. Moderator only. |
| `/whois` | [name] | Shows player info. Moderator buff only (inert offline). |
| `/whoisonline` | — | Lists players in the channel (inert offline). |


## Project layout

| Path | What it is |
|---|---|
| `shs3_solo.swf` | The patched game (URL redirect + offline-logic patches — see `patches/`) |
| `shs3_decoded.swf` | Uncompressed original game data the patched build was made from (study copy — not needed to play) |
| `solo_server.py` | Tiny Python server that pretends to be the dead PHP backend and serves the assets |
| `play.py` / `play.sh` / `play.bat` | One-click launcher for your OS |
| `index.html` + `ruffle.js` + `*.wasm` | Browser-based Flash player (Ruffle) — no separate install needed |
| `roles.html` | Choose Guest or Admin at startup (Admin unlocks the dev commands) |
| `saves.html` + `save-slots.js` | Characters & saves page: switch character, download and import `.sol` files |
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
