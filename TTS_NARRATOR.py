# ============================================================
#   Player2 TTS Narrator Proxy  -  v3.9
#   Original by REGGIE  -  v3.2
#   Mount & Blade II Bannerlord + AI Influence Mod
#
#   v4.0 changes:
#     - TAKEOVER MODE for AI Influence 7.0, which ignores the mod's own Player2
#       URL setting and talks straight to 127.0.0.1:4315. The proxy takes that
#       address (a specific bind beats Player2's wildcard one on Windows) and
#       forwards to Player2 on 127.0.0.2:4315, which it also answers on. No mod
#       edit, no administrator rights, nothing leaves the machine. OFF by
#       default: set TAKEOVER_MODE = True for 7.0, leave False for 6.x.
#     - 7.0 asks for the AUDIO instead of asking us to play it (/tts/speak with
#       play_in_app false — Player2 has no "bytes" endpoint). Answering "ok"
#       with nothing attached would leave characters mute, so AUDIO_REPLY_MODE
#       decides: "background" hands back a moment of silence and voices the line
#       on our own queue, so the mod unlocks the dialogue at once and you can
#       read ahead; "compose" builds one clip (narrated actions, character
#       speech) for the mod to play, keeping its timing and lip-sync honest.
#     - 7.0 still strips the *actions* before asking for speech (measured: a 526
#       character line arrived as 406), so compose mode recovers the whole line
#       from the save file first, with the same speaker-by-text matching the
#       playback worker uses, and applies our pins and delivery notes.
#   v3.9 changes:
#     - Our own speech-speed dial, because the mod's does nothing: the proxy
#       does read the MCM "TTS Speed" slider out of its settings file, but the
#       stored value sits at normal however the dial is dragged. Ours lives in
#       tts_speed.txt, is set from the tray icon under "Speech speed" (named
#       settings, not numbers), is re-read on change with no restart, and
#       overrides the slider — delete the file to hand it back. The characters
#       take the dial in full; the narrator follows half as far and stays inside
#       NARRATOR_SPEED_BAND, since a rushed narrator drops pitch and slurs.
#     - Narrator accent drift (swinging between a southern drawl and neutral).
#       The instruction no longer forbids accents by name: this TTS reads its
#       instruction as language and does not reliably apply a "not", so naming
#       accents and dialects could suggest the very drawl it was meant to
#       suppress. It now names one positive target (General American, as a news
#       anchor speaks it) and lists nothing to avoid, and the anti-performance
#       rule no longer gives whispering or a cracking voice as examples.
#       WORLD_EVENT_CHUNK_CHARS raised 240 -> 480 as well: every call is an
#       independent roll of the voice, so a long event or letter read in one
#       call cannot shift partway through.
#     - Letters can be read aloud (READ_LETTERS, LETTER_HOTKEY, numpad -). A
#       letter never reaches the TTS by itself: it shows as a popup and is only
#       stored in the sender's save file. The mod asks the LLM to write it
#       through this proxy, so each one is captured as it passes and kept in
#       letters.json. The sender is named by matching the text against
#       LastDynamicResponse in the save files.
#     - Within a day, events are read oldest first (WORLD_EVENT_DAY_ORDER), so a
#       cause is spoken before its consequence. The mod's window lists newest at
#       the top, which read them backwards.
#     - The world-event hotkey reads every event from the same campaign day in
#       one go (WORLD_EVENT_READ_WHOLE_DAY), since the mod posts a handful
#       together and its own window groups them that way. Pressing again moves
#       back a day rather than an event.
#     - Pressing the world-event hotkey again now cuts off the reading in
#       progress and starts the next event, instead of queueing behind it
#       (WORLD_EVENT_INTERRUPT). Only event readings are cut; a conversation
#       playing at the time is left to finish.
#     - Tiny narrator asides no longer get their own TTS call
#       (SHORT_NARRATOR_ACTION). With Gemini TTS every request is generated
#       afresh, and a two-word fragment gives it nothing to anchor on, so the
#       narrator kept arriving as a different person. Short actions are folded
#       into the line's next narration instead.
#     - Read a world event aloud on a hotkey (READ_WORLD_EVENTS). AI Influence
#       keeps its World Events in dynamic_events inside
#       aiinfluence_campaign_diplomacy.json, in the save folder next to the NPC
#       files; sorting on creation_time reproduces the window's own order.
#       Nothing is narrated automatically — press WORLD_EVENT_HOTKEY for the
#       newest, press again to step back through older ones.
#     - Shorter waits. The Player2 timeout now scales with text length (20s for
#       short narrator lines, up to 60s for long speeches) — REVERTED to a flat 60s after it made waits longer
#       that let one stalled call freeze a conversation for a minute — ~882s of
#       such waiting in the log. NARRATOR_SPEED is 1.1, between the clean 1.0
#       and the characters' slider speed.
#     - Hardened narrator. 17% of narrator lines are delivery stage directions
#       ("my voice drops to a whisper", "a shaky breath") that Player2's
#       instruction-following TTS can act out — whispering, garbling, distorting.
#       The constant narrator instruction now also says to read such words, not
#       perform them. The narrator is fixed at NARRATOR_SPEED 1.0 so the MCM
#       slider only speeds up characters, and narrator text has its typographic
#       punctuation (dashes, semicolons, curly quotes, ellipses) normalized.
#     - Speakers are identified by WHAT they said, not by voice id. The mod gives
#       the same voice to many characters; in a Cersei/Joffrey group scene the
#       voice guess named Ser Osbert Tempest and Mina Tyrell (whose files had
#       never been read, so every old line looked new), announced those wrong
#       names, and — since the wrong file never held the line — dropped the
#       *actions*. find_speaker_by_text() searches recently written save files
#       for the line itself (every listener's file carries it, tagged with the
#       speaker's id, actions intact). Voice matching is now only a fallback, and
#       a speaker it can't confirm is never announced or voice-pinned.
#
#   v3.8 changes:
#     - Most of the dead air between segments was self-inflicted. The wait after
#       each segment is estimated from SPEECH_CHARS_PER_SECOND, which was 11.0;
#       measuring the real audio (play_in_app:false returns the mp3, whose frame
#       headers give an exact duration) put Player2 at 15.5-21.6 ch/s, mean 18.4.
#       The log showed the cost: 1104 padded segments, 6645s of waiting, 6.0s
#       each, 55% pinned at the 8s cap. Replaying that log at 15.0 cuts the
#       waiting by ~80%. Under-waiting a little is cheap, because the next
#       segment still has to generate (3-15s) before its audio starts.
#     - New: TTS_NARRATOR.py --calibrate measures the rate on your own voices
#       and writes speech_rate.txt, which overrides the constant with no restart.
#       It also reports what the accent anchor costs in generation time.
#     - The accent anchor is now just the accent ("Neutral American English
#       accent."). The long form looked like it cost 26-71% more generation time
#       in a small sample; length was never what made it work, being identical
#       on every call is.
#
#   v3.7 changes:
#     - Characters keep their voice. AI Influence sends a different voice id for
#       the same character across turns (18 of 64 characters in the log had been
#       voiced by 2-4 different voices), so resolve_voice — deterministic on the
#       id it is given — kept producing a new one. The first voice a character is
#       heard with is now pinned to their StringId in npc_voices.json and reused
#       for every later line. Clear the pins from the tray if you want a recast.
#     - Characters keep their accent. NPC lines were sent to Player2 with no
#       conditioning at all (LastTTSInstructions is empty in every save file), so
#       its TTS free-ran and the accent wandered between calls — the narrator,
#       which always sends a fixed instruction, was the only steady voice. Each
#       voice now carries a CONSTANT accent anchor built from its own language,
#       byte-identical on every call. Per-turn LLM tone notes stay off; a note
#       that is rewritten each turn is itself a drift source.
#     - Adjacent segments sharing a voice are spoken as one call, so a line has
#       fewer independent generations to drift across.
#
#   v3.6 changes:
#     - Speed investigation: Player2's local TTS barely honors the `speed` field
#       (measured: nominal 2x ≈ 9% shorter, its 4.0 max ≈ 16%), and AI Influence
#       doesn't forward its MCM "TTS Speed" slider into the request anyway. So no
#       speed control is exposed here — speed is left at whatever the mod requests.
#       The only narrator pacing aid kept is NARRATOR_FORCE_PUNCTUATION: short
#       unpunctuated actions get a trailing period so some voices rush them less.
#     - Group-conversation ordering fix. All lines are now voiced by a SINGLE
#       playback worker in strict arrival order (an ordered FIFO queue) instead
#       of each request racing in its own thread. In AI Influence group
#       conversations several lines fire in quick succession; the old racing
#       model could start a later line's audio before an earlier one's, so a
#       reply was sometimes spoken before the line it answered. Serializing
#       playback guarantees lines play in the order the mod sent them, and also
#       removes the audio overlap that used to drop/silence lines (so the old
#       per-line "generation" supersede is no longer needed).
#     - Handle **double-asterisk** actions (not just *single*): split_text and
#       strip_actions now match runs of asterisks, so no stray "*" leaks through.
#     - Trimmed the word-replacement table to entries that actually transform a
#       word; ~190 self-mapping no-ops and a few dead group-pattern entries were
#       removed. The profanity respellings are unchanged in effect.
#
#   v3.5 changes:
#     - Recover dropped character speech. Player2's TTS can 500 on long/slow
#       generations, silently losing that segment (usually the dialogue, leaving
#       only the narrator). Failed segments are now retried, and if they still
#       fail they're spoken as shorter sentence chunks that generate in time.
#
#   v3.4 changes (AI Influence 5.0.3):
#     - Never voice the "I am unable to respond / check if Player2 is running"
#       LLM-failure fallback (5.0.3 stores it as a normal NPC line).
#     - Read the spoken line from ConversationHistory (which keeps *action*
#       asterisks) instead of LastAIResponseSummary, which 5.0.3 strips of
#       asterisks and can leave stale.
#     - Stop relying on LastTTSPlayedText for fallback text (often empty in 5.0.3).
#     - Speaker detection unchanged: still keyed on the backtick StringId, so the
#       new English "I (...)" NPC prefix (was Cyrillic "Я (...)") needs no change.
#
#   v3.3 changes:
#     - FIX: narrator no longer reads the player's lines. Speaker detection
#       now uses the StringId embedded in each ConversationHistory entry
#       (matched against the NPC's own StringId / player_bind_string_id)
#       instead of the obsolete "Player:" text prefix, which the AI Influence
#       update broke.
#     - Removed the embedded/obfuscated Player2 game key and the revenue-share
#       health-ping. Local TTS now relies on your running, signed-in Player2
#       app. To attribute usage to your OWN registered mod, set GAME_CLIENT_ID.
# ============================================================

from flask import Flask, request, jsonify, Response, stream_with_context
import requests
import re
import time
import os
import sys
import json
import threading
import glob
import hashlib
import base64
import collections
import io

app = Flask(__name__)

# --- Reading the mod's files without getting in its way ---------------------
#
# AI Influence saves a character by writing a new file and swapping it in for
# the old one (File.Replace). Python's open() does not let another program
# delete or rename a file it has open, so if the narrator happened to be
# reading a character at that instant, the swap failed and the mod logged
# "Save failed ... being used by another process" - that update to the
# character was lost. Found in the mod's log on 2026-11-24.
#
# open_shared() opens with every share flag, DELETE included, reads the whole
# file in one go and closes it at once; the caller gets the text in memory.
# The swap can always go through, even mid-read.

def _read_shared_bytes(path):
    if os.name != "nt":
        with open(path, "rb") as f:
            return f.read()
    import ctypes
    import msvcrt
    from ctypes import wintypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                                wintypes.HANDLE]
    GENERIC_READ, SHARE_ALL, OPEN_EXISTING = 0x80000000, 0x7, 3
    h = k32.CreateFileW(os.path.abspath(path), GENERIC_READ, SHARE_ALL, None,
                        OPEN_EXISTING, 0x80, None)
    if h in (None, wintypes.HANDLE(-1).value):
        err = ctypes.get_last_error()
        if err in (2, 3):
            raise FileNotFoundError(2, "file not found (being saved?)", path)
        if err in (5, 32):
            raise PermissionError(13, "file busy (being saved?)", path)
        raise ctypes.WinError(err)
    fd = msvcrt.open_osfhandle(h, os.O_RDONLY | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "rb") as f:
        return f.read()


def open_shared(path, encoding="utf-8-sig"):
    """A text 'file' holding the whole of path, read without blocking a save."""
    return io.StringIO(_read_shared_bytes(path).decode(encoding))


# ============================================================
#  CONFIGURATION  —  Edit these settings
# ============================================================

REAL_PLAYER2  = "http://127.0.0.1:4315"   # Player2 app address (don't change)
PROXY_PORT    = 4316                        # Port this proxy runs on

# ============================================================
#  TAKEOVER MODE  (for AI Influence 7.0 and later)
# ============================================================
# 7.0 ignores the mod's own "Player2 API URL" setting and talks straight to
# Player2 at 127.0.0.1:4315. That address is built at runtime inside an
# obfuscated assembly and the author will not make it configurable, so there is
# nothing to repoint. Instead the proxy TAKES the address: on Windows a socket
# bound to one specific address beats a socket bound to every address, so we can
# hold 127.0.0.1:4315 while Player2 keeps its own listener. The mod then talks
# to us without knowing, and we forward to Player2 on a second loopback address,
# which it also answers on. Measured working 2026-11-11: no administrator
# rights, nothing leaves the machine, and no edit to the mod.
#
# OFF again (2026-11-11, same day): the takeover works as plumbing but 7.0 will
# not talk to a port anything else is bound to, so it breaks the mod. Watch mode
# below is what replaced it. Kept here because it is sound for any mod that
# honours a URL setting, and because 6.x works through it unchanged.
TAKEOVER_MODE     = False
TAKEOVER_LISTEN   = "127.0.0.1"             # the address 7.0 hardcodes
TAKEOVER_PORT     = 4315
TAKEOVER_UPSTREAM = "http://127.0.0.2:4315" # where Player2 still answers us

# How to answer when the mod asks for the AUDIO ITSELF instead of asking us to
# play it. 7.0 generates a whole line up front, plays it itself, and holds the
# dialogue locked for its full length — which is why a line no longer finishes
# in the background while you type your reply.
#   "background" - hand back a moment of silence and play the line ourselves on
#                  our own queue. The mod releases its lock at once, so you can
#                  read ahead and answer. Risk: in a group scene the mod may run
#                  ahead of what is still being spoken. If voices fall behind
#                  what is on screen, switch to "compose".
#   "compose"    - build ONE clip (actions in the narrator's voice, speech in
#                  the character's) and hand it back for the mod to play. Keeps
#                  the mod's timing and lip-sync honest, but keeps its lock.
AUDIO_REPLY_MODE = "background"
# The moment of silence handed back in "background" mode — long enough that the
# mod does not read it as a failed generation.
SILENT_REPLY_SECONDS = 0.25
# 7.0 sends its own delivery note with every line ("Speak with weary disdain…"),
# a different one each time. Ours are constant per character, which is what
# stops a voice wandering, so ours win. True to use the mod's instead.
USE_MOD_INSTRUCTIONS = False

# ============================================================
#  WATCH MODE  (the way in that works with 7.0)
# ============================================================
# Proven 2026-11-11: AI Influence 7.0 refuses to use its Player2 address as soon
# as ANYTHING else is bound to it — not just this proxy, but a relay that copies
# bytes and changes nothing. The mod never connects to the second listener at
# all, and reports its AI service as unavailable or unverified. Player2's new
# per-mod arrangement evidently will not tolerate company on that port, so there
# is no sitting in the middle of it.
#
# So we stop trying. In watch mode the proxy is not in the mod's path at all: it
# WATCHES the save folder, and when a character says something new it speaks the
# line itself as an ordinary Player2 client, on the address that works. The mod
# is never touched, never delayed, and can never be broken by us.
#
# Turn the mod's own TTS OFF in its settings when using this, or every line is
# spoken twice. In exchange you lose the mod's lip-sync, and gain back the
# narrator, the pins, the speed dial, the banned voices, the announcements, and
# a line that plays on while you read ahead and type.
WATCH_MODE = True
# How often to look for a new line. Cheap: only files whose timestamp moved are
# re-read.
WATCH_POLL_SECONDS = 0.4
# Speak lines that were already in the save files when the proxy started. Off:
# a restart mid-conversation does not replay the backlog at you.
WATCH_SPEAK_BACKLOG = False
# Time to the first sound is all that is felt. Player2 returns a line only when
# the WHOLE of it has been generated, and generation time grows with length: a
# long speech with no *action* to break it up is one call, and one long wait
# (measured 2026-11-11: a single 700-character segment took 27 seconds before a
# word was heard). So a long segment is broken at sentence boundaries and spoken
# piece by piece, the first piece deliberately short so the voice starts quickly,
# the rest longer so the line is not chopped into fragments. Set
# WATCHED_CHUNK_CHARS to 0 to go back to one call per segment.
WATCHED_FIRST_CHUNK_CHARS = 150
WATCHED_CHUNK_CHARS = 420

# The two cannot both be on: watch mode exists precisely because 7.0 refuses to
# use its address while anything else holds it, so taking that address would
# break the very mod we are narrating.
if WATCH_MODE and TAKEOVER_MODE:
    print("  [watch] Takeover turned off — it would stop the mod talking to "
          "Player2, which is why watch mode exists.")
    TAKEOVER_MODE = False

# With the takeover on, Player2 is no longer at the address we hold — we reach
# it on the second loopback address instead, and everything we forward goes
# there. Done here so it holds however the proxy is started.
if TAKEOVER_MODE:
    REAL_PLAYER2 = TAKEOVER_UPSTREAM
    PROXY_PORT = TAKEOVER_PORT

NARRATOR_VOICE = "01955d76-ed5b-748c-8d98-0fb708ef0fbd"  # Ethan (en_US) - narrator voice

# Player2 game key — intentionally left blank.
# The Player2 desktop app, when running and signed in, authorizes local TTS
# calls on its own, so a personal narrator proxy does not need a game key.
# If you register your OWN mod with Player2 and want usage attributed to it,
# paste your own key here.
GAME_CLIENT_ID = ""

# >>> OPTIONAL: set a specific save folder path, or leave as "" to auto-detect <<<
NPC_FOLDER = ""  # leave empty to auto-detect
# Follow whichever campaign the game is writing to: at start-up, and while
# running (the narrator switches when you load another campaign). False keeps
# the folder saved in proxy_config.txt until that file is deleted.
FOLLOW_ACTIVE_CAMPAIGN = True

# ============================================================
#  GAME KEY HELPER
# ============================================================

def _game_headers(extra=None):
    """
    Build headers for requests sent to the real Player2 API.
    Always includes player2-game-key if GAME_CLIENT_ID is set.
    This makes TTS/STT calls free for approved mods.
    """
    headers = {}
    if extra:
        headers.update(extra)
    if GAME_CLIENT_ID:
        headers["player2-game-key"] = GAME_CLIENT_ID
    return headers


# ============================================================
#  AUTO-DETECT NPC_FOLDER
# ============================================================

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "proxy_config.txt")


def _get_steam_library_paths():
    """
    Read Steam's libraryfolders.vdf to get ALL library paths the user has configured.
    This is the only reliable way to find games regardless of where Steam is installed.
    Returns a list of 'steamapps/common' paths.
    """
    vdf_locations = []

    if sys.platform == "win32":
        program_files  = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        program_files2 = os.environ.get("ProgramFiles",      r"C:\Program Files")
        vdf_locations += [
            os.path.join(program_files,  "Steam", "steamapps", "libraryfolders.vdf"),
            os.path.join(program_files2, "Steam", "steamapps", "libraryfolders.vdf"),
        ]
        # Scan all drives for custom Steam installs (e.g. E:\Games\Steam)
        for drive in [f"{d}:\\" for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{d}:\\")]:
            for stem in ["Steam", "Games\\Steam", "SteamLibrary", "Games\\SteamLibrary"]:
                vdf_locations.append(os.path.join(drive, stem, "steamapps", "libraryfolders.vdf"))
    else:
        home = os.path.expanduser("~")
        vdf_locations += [
            os.path.join(home, ".steam", "steam", "steamapps", "libraryfolders.vdf"),
            os.path.join(home, ".local", "share", "Steam", "steamapps", "libraryfolders.vdf"),
        ]

    library_paths = []
    seen = set()

    for vdf_path in vdf_locations:
        if not os.path.isfile(vdf_path):
            continue
        try:
            with open(vdf_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            # VDF format has lines like:  "path"   "E:\\Games\\SteamLibrary"
            for match in re.finditer(r'"path"\s+"([^"]+)"', content):
                raw = match.group(1).replace("\\\\", "\\")
                common = os.path.join(raw, "steamapps", "common")
                if common not in seen:
                    seen.add(common)
                    library_paths.append(common)
            # Also treat the VDF's own steamapps folder as a library
            common = os.path.join(os.path.dirname(os.path.dirname(vdf_path)), "common")
            if common not in seen:
                seen.add(common)
                library_paths.append(common)
        except Exception:
            pass

    return library_paths


def _find_save_data_bases():
    """Return all existing AIInfluence save_data base folders found on this machine."""
    candidates = set()

    # Primary: use Steam's own library list (catches every custom install location)
    for common in _get_steam_library_paths():
        path = os.path.join(common, "Mount & Blade II Bannerlord", "Modules", "AIInfluence", "save_data")
        candidates.add(path)
        # Subscribed on the Steam Workshop instead: the mod lives under
        # steamapps\workshop\content\261550\<item id>\ (2026-11-23, for release)
        workshop = os.path.join(os.path.dirname(common), "workshop", "content", "261550")
        try:
            for item in os.listdir(workshop):
                if _is_aiinfluence_module(os.path.join(workshop, item)):
                    candidates.add(os.path.join(workshop, item, "save_data"))
        except OSError:
            pass

    # Other stores' usual install folders (GOG, Xbox / Game Pass), on every drive
    if sys.platform == "win32":
        for drive in "CDEFGHIJ":
            for game in (r"GOG Games\Mount & Blade II Bannerlord",
                         r"Program Files (x86)\GOG Galaxy\Games\Mount & Blade II Bannerlord",
                         r"XboxGames\Mount & Blade II- Bannerlord\Content",
                         r"Games\Mount & Blade II Bannerlord"):
                candidates.add(os.path.join(drive + ":\\", game, "Modules", "AIInfluence", "save_data"))

    # Fallback: Documents folder (some mod setups write there)
    if sys.platform == "win32":
        userprofile = os.environ.get("USERPROFILE", "")
        if userprofile:
            candidates.add(os.path.join(userprofile, "Documents", "Mount and Blade II Bannerlord", "Modules", "AIInfluence", "save_data"))
    else:
        home = os.path.expanduser("~")
        candidates.add(os.path.join(home, "Documents", "Mount and Blade II Bannerlord", "Modules", "AIInfluence", "save_data"))

    return [c for c in candidates if os.path.isdir(c)]


def _is_aiinfluence_module(folder):
    """A Workshop item folder that holds AI Influence (its SubModule.xml says so)."""
    try:
        with open(os.path.join(folder, "SubModule.xml"), "r", encoding="utf-8-sig",
                  errors="replace") as f:
            return 'value="AIInfluence"' in f.read(4000)
    except OSError:
        return False


# Folders the mod keeps in save_data that are not campaigns.
NOT_A_CAMPAIGN = ("default",)


def campaign_last_written(folder):
    """When the game last wrote a character file in this campaign (0 if never)."""
    newest = 0.0
    try:
        with os.scandir(folder) as it:
            for e in it:
                if e.name.endswith(".json"):
                    try:
                        newest = max(newest, e.stat().st_mtime)
                    except OSError:
                        pass
    except OSError:
        return 0.0
    return newest


def find_all_save_subfolders():
    """Return list of all campaign folders found, the one played last first."""
    all_saves = []
    for base in _find_save_data_bases():
        try:
            for d in os.listdir(base):
                full = os.path.join(base, d)
                if (os.path.isdir(full) and not d.startswith(("_", "."))
                        and d.lower() not in NOT_A_CAMPAIGN):
                    all_saves.append(full)
        except Exception:
            pass
    # The campaign whose character files were written last is the one being
    # played; a folder's own date moves only when files are added or removed.
    all_saves.sort(key=campaign_last_written, reverse=True)
    return all_saves


def _load_config():
    """Load saved NPC folder path from config file, or return None."""
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if os.path.isdir(line):
                            return line
                        else:
                            print(f"  Config file path no longer valid: {line}")
        except Exception:
            pass
    return None


def _save_config(folder):
    """Save NPC folder path to config file next to this script."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write("# Player2 Proxy - auto-saved NPC folder\n")
            f.write("# Delete this file to re-run save detection\n")
            f.write(folder + "\n")
        print(f"  Saved to config: {CONFIG_FILE}")
    except Exception as e:
        print(f"  Could not save config: {e}")


def _pick_save_interactive(saves):
    """
    Show user a numbered list of found saves and let them pick one.
    Returns chosen folder path or None.
    """
    import time as _time
    print()
    print("  ┌─────────────────────────────────────────────────────────────┐")
    print("  │           FOUND MULTIPLE SAVES — PLEASE PICK ONE           │")
    print("  └─────────────────────────────────────────────────────────────┘")
    print()
    for i, path in enumerate(saves, 1):
        try:
            mtime = _time.strftime("%Y-%m-%d %H:%M", _time.localtime(os.path.getmtime(path)))
        except Exception:
            mtime = "unknown"
        save_id = os.path.basename(path)
        print(f"    [{i}] {save_id}   (last used: {mtime})")
        print(f"        {path}")
        print()
    print(f"    [0] Enter path manually")
    print()
    while True:
        try:
            choice = input("  Enter number: ").strip()
        except EOFError:
            return None
        if choice == "0":
            return None
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(saves):
                return saves[idx - 1]
        print(f"  Please enter a number between 0 and {len(saves)}")


def resolve_npc_folder():
    """
    Resolve NPC folder with this priority:
      1. NPC_FOLDER hardcoded in script (if set and valid)
      2. proxy_config.txt saved next to script
      3. Auto-detect: if exactly one save found → use it silently
      4. Auto-detect: multiple saves found → show pick list
      5. Ask user to enter path manually
    Saves result to proxy_config.txt for next run.
    """
    # 1. Hardcoded
    folder = NPC_FOLDER.strip()
    if folder:
        if os.path.isdir(folder):
            print(f"  NPC folder (hardcoded): {folder}")
            return folder
        print(f"  WARNING: NPC_FOLDER set but not found: {folder}")

    # 2. Config file - unless another campaign has been played since, which is
    # what a new campaign looks like: the old folder is still there, so without
    # this the narrator kept watching a campaign nobody was playing.
    saved = _load_config()
    if saved:
        if FOLLOW_ACTIVE_CAMPAIGN:
            saves = find_all_save_subfolders()
            if saves and os.path.normcase(saves[0]) != os.path.normcase(saved) \
                    and campaign_last_written(saves[0]) > campaign_last_written(saved):
                print(f"  A newer campaign is being played: {os.path.basename(saves[0])}")
                _save_config(saves[0])
                return saves[0]
        print(f"  NPC folder (from config): {saved}")
        return saved

    # 3 & 4. Auto-detect
    print("  Searching for Bannerlord AIInfluence save folders...")
    saves = find_all_save_subfolders()

    if len(saves) == 1:
        print(f"  Auto-detected: {saves[0]}")
        _save_config(saves[0])
        return saves[0]

    if len(saves) > 1:
        print(f"  Found {len(saves)} save(s).")
        chosen = _pick_save_interactive(saves)
        if chosen:
            _save_config(chosen)
            return chosen

    # 5. Manual entry
    if not saves:
        print()
        print("  Could not find any AIInfluence save folders automatically.")
    print()
    print("  Please paste your save folder path below.")
    print(r"  Example: C:\Games\Steam\steamapps\common\Mount & Blade II Bannerlord\Modules\AIInfluence\save_data\kUi17JRGXPnR")
    print()
    try:
        user_path = input("  Path: ").strip().strip('"').strip("'")
    except EOFError:
        user_path = ""

    if user_path and os.path.isdir(user_path):
        _save_config(user_path)
        return user_path

    print("  ERROR: Path not found or not entered. NPC matching will be disabled.")
    print(f"  Fix: delete '{CONFIG_FILE}' and restart, or set NPC_FOLDER in the script.")
    return user_path or ""


# Resolve once at startup
_RESOLVED_NPC_FOLDER = None

def get_npc_folder():
    global _RESOLVED_NPC_FOLDER
    if _RESOLVED_NPC_FOLDER is None:
        _RESOLVED_NPC_FOLDER = resolve_npc_folder()
    return _RESOLVED_NPC_FOLDER

PAUSE = 0.0  # Extra pause between segments (seconds), on top of the padding below.

# --- Keep segments in sequence ---
# Player2's /tts/speak returns when GENERATION finishes, not when the audio stops
# playing (measured: a 9.8s line returned after 7.1s). Without compensating, the
# next segment starts while the previous is still sounding, so an action and the
# dialogue after it overlap. After each segment we wait out the remainder of its
# estimated speech time, so segments and lines play strictly in the order spoken.
PAD_SEGMENTS_TO_AUDIO_LENGTH = True
# How fast Player2 actually speaks, in characters per second. This is the single
# number the wait above depends on, and setting it too low is pure dead air: at
# the old 11.0 the log showed 1104 padded segments waiting 6645s in total (6.0s
# each, 55% of them pinned at the cap). Measured by pulling the real mp3 back
# from Player2 (play_in_app:false) and decoding its frame headers: 15.5-21.6
# ch/s on one voice. A fuller calibration across two more voices then measured
# 13.3-18.3 (median 14.8), so the rate varies more by voice than that first
# sample suggested. 13.5 sits below almost every measurement while still cutting
# the waiting by well over half; under-waiting slightly is cheap anyway, because
# the next segment has to generate (3-15s) before its audio starts, which is a
# cushion of its own.
#   Re-measure on your own voices at any time:  TTS_NARRATOR.py --calibrate
#   That writes speech_rate.txt, which overrides this value with no restart.
SPEECH_CHARS_PER_SECOND = 13.5
MAX_SEGMENT_PAD = 8.0            # never wait more than this after one segment
FILE_POLL_INTERVAL = 0.15  # How often to re-check the JSON file while waiting for a new entry (seconds)
FILE_POLL_TIMEOUT  = 8.0   # Max seconds to wait for a new history entry before giving up

# --- Voice stability ---
# Forward the per-turn tone notes (LastTTSInstructions, written fresh by the LLM
# every turn) to Player2 as advanced_voice instructions. Off: a note rewritten
# every turn is itself a source of drift, and the field is empty in every save
# file checked anyway (0 of 76 characters), so nothing is lost by ignoring it.
# The constant accent anchor below is sent instead.
SEND_VOICE_INSTRUCTIONS = False

# Player2 renders the SAME voice id differently from call to call when it is
# given no conditioning at all — a lord sounds American on one line and Irish two
# lines later. Every NPC line was going out bare (LastTTSInstructions is empty),
# so the model had nothing to hold onto; the narrator, which does send a constant
# instruction, has been the steadier voice all along. This sends each NPC voice a
# CONSTANT accent anchor, byte-identical on every call, built from that voice's
# own language in VOICE_DB.
PIN_VOICE_ACCENT = True

# AI Influence sends a DIFFERENT voice id for the same character across turns.
# From the proxy log, 18 of 64 characters have been voiced by 2-4 different
# voices (Robb Stark used four), and the id in the request often doesn't
# even match that character's AssignedTTSVoice on disk. resolve_voice is
# deterministic on the id it is GIVEN, so it faithfully produces a different
# voice. With this on, the first voice a character is heard with is pinned to
# their StringId and reused for every later line, so nobody is recast
# mid-conversation. Saved to npc_voices.json; clear it from the tray menu.
PIN_NPC_VOICES = True

# Speak neighbouring segments that share a voice as one call. Each /tts/speak is
# an independent generation and another chance to drift, so fewer is steadier.
MERGE_ADJACENT_SEGMENTS = True

# Tiny *actions* are the worst case for a generative TTS like Gemini: two words
# such as "quieter" or "a pleasant pause" give it almost nothing to hold onto,
# so it invents a reading and the narrator sounds like a different person. Long
# narration is far steadier, which is why full descriptions hold up and asides
# do not.
#   "skip"  - don't speak them. Nothing lands out of order; you lose the aside.
#   "merge" - fold it into the line's NEXT narrator segment. The words survive,
#             but they are then spoken AFTER the dialogue they were written in
#             front of, so the sequence no longer matches the text.
#   "keep"  - the old behaviour: each aside gets its own call, in its right
#             place, and that call is the one that drifts.
SHORT_NARRATOR_ACTION = "keep"
MIN_NARRATOR_WORDS = 3     # fewer words than this counts as a fragment

# --- Narrator segment tuning ---
# Short action fragments ("he nods") with no end punctuation get a trailing
# period, which Player2 paces like a sentence instead of rushing.
NARRATOR_FORCE_PUNCTUATION = True  # add a period to unpunctuated action text

# The narrator's instruction, sent identically on every narrator call.
# Player2's TTS FOLLOWS instructions, and it treats the text the same way: 17% of
# narrator lines are stage directions about delivery — a dropped voice, a caught
# breath — and an instruction-following voice will act those out, which is where
# the whispering, garbled or distorted narrator comes from. So the instruction
# names the voice we want AND says plainly that such words are to be read, not
# performed. It must stay constant: varying instructions made voices drift.
#
# REWRITTEN 2026-11-09, narrator swinging between a southern drawl and neutral:
# the old wording forbade accents by name ("no regional, local or character
# accent of any kind, and no dialect"). This TTS reads its instruction as
# language, and a generative voice does not reliably apply a "not" — naming
# accents and dialects at all puts them in front of it, so the sentence meant to
# suppress a drawl could just as well suggest one. It now names ONE positive
# target and says nothing about what to avoid. For the same reason the
# anti-performance rule no longer lists whispering or a cracking voice as
# examples: naming a delivery invites it. Do not reintroduce either list.
# Set to "" to send no instruction at all.
#   {accent} is filled in from the narrator VOICE's own language, so switching
#   the narrator to a British voice doesn't leave the instruction arguing with
#   it. Set NARRATOR_ACCENT below to pin it to specific wording instead.
NARRATOR_INSTRUCTIONS = (
    "{accent} You are a narrator reading a story aloud. Hold that same voice "
    "from the first word to the last: one steady, clear, even voice at an "
    "unhurried pace, every sentence delivered alike. "
    "Say exactly the words of the text, in order: add nothing, drop nothing, "
    "change nothing, and say unfamiliar names as spelled. That includes any "
    "words describing how a person speaks or breathes: they belong to the "
    "story and are spoken as written, never performed.")
# Blank = name the narrator voice's own language (recommended: fighting a voice's
# native accent is what makes it wander). Or set it by hand — if you do, name a
# single accent positively and never list accents to avoid, for the reason given
# above. E.g. "Speak in standard British English, as a national broadcaster
# speaks it."
NARRATOR_ACCENT = ""

# The narrator speaks at this fixed speed, whatever the MCM "TTS Speed" slider is
# set to — the slider speeds up the CHARACTERS. A narrator riding a raised speed
# rushed and dropped in pitch before. 1.0 was clean but slow; 1.1 is the middle
# ground between that and the characters' 1.2. None = follow the slider.
NARRATOR_SPEED = 1.1

# Tidy narrator text before it is spoken: curly quotes, em/en dashes, semicolons,
# ellipses and stray quote marks become plain punctuation, and the line starts
# with a capital and ends with a full stop. Fragments like "a shaky breath; he
# lifts his chin" are what Player2 stumbles over and mispronounces.
NARRATOR_NORMALIZE_TEXT = True

# --- Read a world event aloud ---
# AI Influence's World Events window (and the orange text in the log feed) comes
# from dynamic_events in aiinfluence_campaign_diplomacy.json, in the same save
# folder as the NPC files — title plus the full description, newest first by
# creation_time, exactly the order the window shows. Nothing is read
# automatically: press the hotkey and the narrator reads the newest event. Press
# it again within WORLD_EVENT_STEP_SECONDS to step back to the one before, so you
# can walk down the list by ear; pause longer and it starts from the newest again.
#   The hotkey is claimed system-wide, so while the proxy runs this key will NOT
#   reach Bannerlord or anything else — pick one the game doesn't need.
READ_WORLD_EVENTS = True
WORLD_EVENT_HOTKEY = "numpad+"      # also e.g. "ctrl+alt+e", "alt+f9", "numpad0"
WORLD_EVENT_STEP_SECONDS = 15.0
# Pressing again while an event is being read cuts it off and starts the next
# one, instead of queueing behind it. False = let each reading finish.
WORLD_EVENT_INTERRUPT = True
# How the key is watched for:
#   "register" - RegisterHotKey. Claims the key system-wide, so it never reaches
#                the game. Windows will NOT deliver it while a window from a
#                more privileged program is in front, and Bannerlord runs
#                elevated through BLSE — which is why this alone stayed silent
#                while playing unless the proxy also ran as administrator.
#   "poll"     - watch the key's own state a few dozen times a second. Not
#                subject to that restriction, needs no administrator rights, and
#                leaves the key working in the game as well.
#   "auto"     - both, whichever notices first; a second trigger in the same
#                instant is ignored, so one press is still read once.
WORLD_EVENT_HOTKEY_MODE = "auto"
WORLD_EVENT_POLL_SECONDS = 0.03     # how often "poll" looks at the key
WORLD_EVENT_READ_TITLE = True       # say the title before the description
# Read every event from the same campaign day in one go, rather than one event
# per press. The mod usually posts a handful together, and the day is what its
# own window labels them by ("Today", "1 day ago"). Pressing again then moves to
# the previous DAY, not the previous event. False = one event per press.
WORLD_EVENT_READ_WHOLE_DAY = True
# Order the events WITHIN a day:
#   "chronological" - oldest first, the order they actually happened, so a cause
#                     is read before its consequence. The mod's window lists
#                     newest at the top, which reads them backwards: the Errols
#                     opening their gates is recorded a fraction of a second
#                     before the market news that followed from it.
#   "window"        - newest first, matching what the window shows.
WORLD_EVENT_DAY_ORDER = "chronological"
# Long descriptions are spoken as sentence-sized pieces; one huge call is where
# Player2 stalls and garbles.
# RAISED 2026-11-09 (was 240): every call is an independent roll of the voice,
# so a reading split into several pieces can shift accent partway through. At
# this size a typical event or letter goes out as ONE call and holds one voice.
# It is a middle ground, not the maximum: the audio from a full piece still has
# to arrive inside the flat TTS timeout, and genuinely long readings are still
# broken up rather than risking a stall.
WORLD_EVENT_CHUNK_CHARS = 480

# --- Read a letter aloud ---
# AI Influence's lords write to you. The letter never reaches the TTS on its
# own: it arrives as a popup and is only stored in the sender's save file. The
# proxy sees it being written, though — the mod asks the LLM for it through
# here, using a letter prompt it marks with _LETTER_PROMPT_MARKER — so each
# letter is captured as it passes and kept in letters.json. Nothing is read
# automatically: press the key for the newest, again for the one before.
READ_LETTERS = True
LETTER_HOTKEY = "numpad-"
LETTER_ANNOUNCE_SENDER = True   # "A letter from Illyrio Mopatis." before the text
LETTER_KEEP = 20                # how many past letters to remember
LETTER_MAX_BYTES = 262144       # cap on a captured reply, so a stream can't grow

# --- Group conversations ---
# Whether *actions* are narrated during AI Influence group conversations (a court
# scene, several lords replying in turn). True narrates them everywhere, exactly
# like a 1-on-1. Set False to keep the narrator quiet in group scenes — those
# lines are then spoken in the character's own voice with the *action* text
# stripped out, which is less busy when many lords are talking.
#   A conversation counts as "group" when the current dialogue scene is tagged
#   "group:" by the mod, or the NPC has heard another npc speak in that scene.
NARRATE_ACTIONS_IN_GROUP = True

# In a GROUP conversation only, have the narrator name the speaker before their
# line, so several lords replying in turn are easy to tell apart. 1-on-1
# conversations are untouched — there is only one other voice, so naming them
# every turn would just be noise.
#   The name is folded into the leading *action* when there is one, so a line
#   like "*steps forward* My lord..." costs no extra TTS call — it becomes one
#   narrator segment, "Mace Tyrell. Steps forward." Only a line that opens
#   straight into dialogue needs an extra (short) call.
ANNOUNCE_SPEAKER_IN_GROUP = True
# Don't re-announce someone who is still speaking from the previous line.
ANNOUNCE_SPEAKER_SKIP_REPEAT = True

# --- Voice the PLAYER's line ---
# Normally there's dead air after you send a message: the LLM thinks, generates,
# and only then does anything get spoken. The proxy sees your message on its way
# to the LLM (the /v1/chat/completions request passes through here), so it can
# voice YOUR line during that gap — you hear your character speak, then the NPC's
# reply lands afterwards. Playback uses the same ordered queue, so your line is
# always spoken before the reply it prompted.
# Off by default — voicing your own lines costs extra TTS on every turn. Turn it
# on from the tray icon ("Voice my lines"); the choice is saved and reused.
VOICE_PLAYER_LINES = False
# Starting voice for your character. You can change it live from the tray icon
# ("Player voice" submenu) — the choice is saved to player_voice.txt and reused
# next launch, so this line is only the fallback default.
PLAYER_VOICE = "01955d76-ed5b-7497-9f8e-0e7448515bf3"   # Noah (american male)
# Speak a short sample line whenever you pick a voice from the tray menu.
PLAYER_VOICE_AUDITION = True
# Keep NPCs off your voice. AI Influence hands out its own voices and many lords
# share one, so without this a whole group of them can end up sounding exactly
# like you. Colliding NPCs are moved to a stable stand-in of the same gender.
AVOID_PLAYER_VOICE_FOR_NPCS = True
# Same idea for the narrator's voice — an NPC speaking in Ethan's voice is easy
# to mistake for narration. Set False to let NPCs use it.
AVOID_NARRATOR_VOICE_FOR_NPCS = True
# Send your *actions* to the narrator voice, same as NPC lines. False = skip them
# and speak only what your character actually says.
VOICE_PLAYER_ACTIONS = True
# Ignore a player line shorter than this (stray tokens, menu blips).
PLAYER_LINE_MIN_CHARS = 8
# Cut your line short the moment the NPC's reply is ready, instead of making the
# reply wait for you to finish. Your line is there to fill the thinking gap, so
# once there's a real reply it should take over immediately.
INTERRUPT_PLAYER_LINE_ON_REPLY = True

# --- Internal-thoughts leak filter ---
# With AI Influence's "Internal Thoughts" enabled, the LLM is asked to return
# JSON like {"internal_thoughts": "FACT CHECK: STEP 1: ...", "response": "..."}.
# Weaker/faster models (notably DeepSeek) sometimes ignore that and emit the raw
# chain-of-thought as plain text — "FACT CHECK: STEP 1: I am in the Red Keep...
# STEP 6: ..." followed by the real line. The mod can't parse it, passes the whole
# thing to TTS, and the narrator reads the character's private reasoning aloud.
# This strips the scaffolding and speaks only the actual dialogue.
STRIP_INTERNAL_THOUGHTS = True
# If the reasoning can't be separated from the dialogue with confidence, stay
# silent for that line rather than risk reading the thoughts aloud.
SKIP_LINE_IF_THOUGHTS_UNSEPARABLE = True

# --- Speed safety cap ---
# AI Influence forwards its MCM "TTS Speed" slider as the request speed, and the
# proxy passes it to Player2. A high slider makes speech unintelligibly fast (4.0
# is gibberish). This caps the speed the proxy will actually send, no matter what
# the slider says. 1.0 = normal pace; raise it if you genuinely want faster
# speech (Player2's own hard max is 4.0). Lower bound is Player2's min, 0.25.
# RAISED to 2.0 (2026-11-09): this is now the ceiling of OUR dial too, and the
# old one was itself the fastest setting, so the menu had nothing left to offer.
# Player2's own hard max is 4.0, which is gibberish; 2.0 leaves room to hand-edit
# tts_speed.txt past the fastest menu entry without reaching that.
MAX_TTS_SPEED = 2.0
# Take the talking speed from AI Influence's MCM "TTS Speed" slider. Requests
# reaching the proxy have only ever carried speed 1.0 (651 logged, none other),
# so the slider was never getting through — the proxy now reads it straight
# from the MCM settings file instead. Re-read whenever the file changes, so
# moving the slider in-game applies to the next line with no restart. Set False
# to use whatever speed the request carries.
USE_MOD_TTS_SPEED = True
# MCM's settings live in the Bannerlord folder under the player's Documents,
# wherever that is. Written out rather than hard-coded, because one person's
# name in a path is the difference between a tool and a tool only one person
# can run (2026-11-16). OneDrive moves Documents, so that is checked too.
def _bannerlord_doc_dir():
    home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    roots = [os.path.join(home, "Documents")]
    one = os.environ.get("OneDrive") or os.environ.get("OneDriveConsumer")
    if one:
        roots.insert(0, os.path.join(one, "Documents"))
    for root in roots:
        path = os.path.join(root, "Mount and Blade II Bannerlord")
        if os.path.isdir(path):
            return path
    return os.path.join(roots[-1], "Mount and Blade II Bannerlord")


BANNERLORD_DOC_DIR = _bannerlord_doc_dir()
MOD_SETTINGS_FILE = os.path.join(
    BANNERLORD_DOC_DIR,
    "Configs", "ModSettings", "Global", "AIInfluence", "AIInfluenceSettings.json")

# --- Our own speech-speed dial (2026-11-09) ---
# The mod's slider is a dead end: the proxy does read it out of the MCM settings
# file, but the stored value sits at normal however the dial is dragged, so there
# is nothing to follow. This dial is ours. The value lives in tts_speed.txt next
# to this script, is re-read whenever it changes (so the tray menu applies to the
# next line with no restart), and takes precedence over the MCM slider. Delete
# the file to hand control back to the slider. Set False to ignore ours entirely.
OWN_TTS_SPEED = True
# Where the dial sits before it is ever set. 1.0 is Player2's normal pace.
TTS_SPEED_DEFAULT = 1.0
# What the tray menu offers, as (name, speed). Named rather than numbered: the
# menu is there to be read. Anything above MAX_TTS_SPEED is left out of the menu.
TTS_SPEED_PRESETS = (
    ("Much slower",     0.75),
    ("Slower",          0.85),
    ("A little slower", 0.95),
    ("Normal",          1.0),
    ("A little faster", 1.1),
    ("Faster",          1.2),
    ("Much faster",     1.35),
    ("Very fast",       1.5),
    ("Fastest",         1.75),
)
# --- Volume ---
# Our own volume, as a multiplier on everything the narrator plays: the
# characters, the narrator itself, letters, the memory book. 1.0 leaves a clip
# exactly as loud as it was made, which is what the mod's own TTS Volume
# slider has already set.
#
# Useful mostly DOWNWARDS. A clip is already lifted to the mod's slider and
# sits near the top of what 16-bit audio can hold, so asking for much more
# than normal runs into that ceiling and is rounded off rather than getting
# louder - for genuinely more, raise it in Windows' own mixer. Below normal
# there is no such limit and it does exactly what it says.
OWN_TTS_VOLUME = True
# Where the dial sits before it is ever set.
TTS_VOLUME_DEFAULT = 1.0
# The range a setting is held to, whether it came from the menu or was typed
# into the file by hand.
MIN_TTS_VOLUME = 0.1
MAX_TTS_VOLUME = 1.6
# What the tray menu offers, as (name, volume). Named rather than numbered,
# like the speeds: the menu is there to be read.
TTS_VOLUME_PRESETS = (
    ("Very quiet",      0.25),
    ("Quiet",           0.45),
    ("A little quiet",  0.70),
    ("Normal",          1.0),
    ("A little louder", 1.2),
    ("Louder",          1.4),
)
# How far the NARRATOR follows the dial: 0 = never moves, 1 = moves with the
# characters. Half, because a rushed narrator does not merely hurry — it drops in
# pitch and slurs, which is exactly what its own fixed speed was protecting
# against. NARRATOR_SPEED stays its resting pace at a dial of normal.
NARRATOR_SPEED_FOLLOW = 0.5
# ...and the narrator never leaves this band, however far the dial is pushed.
NARRATOR_SPEED_BAND = (0.9, 1.3)

# --- TTS failure recovery ---
# Player2's TTS can return a 500 on long/slow generations (its own internal
# limit), which silently drops that segment — usually the character's dialogue,
# leaving only the narrator. These settings recover it:
#   - retry the failed segment a couple of times (the model is often just busy)
#   - if it still fails, split the line into sentences and speak those, since
#     each shorter generation is far more likely to come back under the limit.
TTS_RETRIES          = 2     # extra attempts per piece if Player2 returns non-200
TTS_RETRY_DELAY      = 0.6   # seconds between attempts
# How long to wait for Player2 before giving up on an attempt and retrying,
# scaled to the length of the text. A flat 60s let a stalled call hold the whole
# conversation for a minute: 18 attempts across the log sat the full 60s (~882s
# of waiting), while the retry that followed usually came back in seconds. Short
# narrator lines normally take 2-4s, so they give up at 20s; long speeches keep
# up to 60s. Player2 cancels a call the proxy abandons (it logs it as "-> 0" at
# the moment we disconnect), so a cut-off attempt never plays late or doubles up.
TTS_TIMEOUT_BASE     = 15.0  # seconds, plus...
TTS_TIMEOUT_PER_CHAR = 0.1   # ...this per character of text
TTS_TIMEOUT_MIN      = 60.0  # REVERTED to a flat 60s (2026-09-14): shorter limits
                             # cut slow-but-working generations and restarted them,
                             # which made waits LONGER, not shorter
TTS_TIMEOUT_MAX      = 60.0
TTS_CHUNK_ON_FAILURE = True  # last resort: break a failed line into sentences
TTS_CHUNK_MAX_CHARS  = 240   # target size of those sentence chunks


# --- System tray ---
# Run with a small icon in the Windows system tray (next to the clock) so you
# can keep the proxy running without an open console window to alt-tab to.
# Left-click the tray icon (or use its right-click menu) to show/hide the
# console; "Quit" stops the proxy. If pystray/Pillow aren't installed, the
# proxy simply runs with the console as before — it never leaves you with no
# window. START_MINIMIZED tucks the console away automatically on launch.
USE_TRAY = True
START_MINIMIZED = False
HIDE_FROM_TASKBAR = True   # Remove the console's taskbar button (and alt-tab entry)
                           # so the tray icon is its only presence. Show/hide still
                           # works from the tray. Windows-only; ignored elsewhere.



# --- Current-line validation guard ---
# The mod tells us what it wants spoken right now in the request 'text' field.
# We use that as ground truth. During AI Influence "initiative" events (a lord
# attacking via dialogue, or seeking you out on the map) that lord's save_data
# JSON may not get a fresh entry, so NPC matching can latch onto a STALE/PREVIOUS
# conversation that shares the same TTS voice. To prevent narrating the wrong
# conversation, we only trust JSON-recovered text if it matches the mod's text;
# otherwise we narrate the mod's text directly.
MATCH_RATIO_THRESHOLD = 0.6   # 0..1 similarity needed to accept JSON text as "the same line"
MATCH_POLL_TIMEOUT    = 3.0   # When we have the mod's text to validate against, stop waiting
# Speaker identification by text (see find_speaker_by_text). Only save files
# written this recently are searched, and only their last few lines, so an old
# conversation can never be mistaken for the line being spoken now.
SPEAKER_SEARCH_RECENT_SECONDS = 300
SPEAKER_SEARCH_LAST_ENTRIES   = 8
# When the text search found nothing, the line had already been waited for, so
# the voice-matched fallback only glances at its file instead of polling again.
FALLBACK_POLL_TIMEOUT = 0.5
                              # for a matching new entry after this many seconds (vs FILE_POLL_TIMEOUT).
                              # Keeps initiative misfires from stalling "Ready to Respond".

# --- Group-conversation ordering ---
# Every /v1/tts/speak line is voiced by ONE worker thread in strict arrival
# order (see the ordered playback queue below). This is what keeps AI Influence
# group conversations — where several lines fire in quick succession — from being
# narrated out of order (e.g. a reply spoken before the line it answered).
#
# MAX_QUEUE_AGE: optionally drop a queued line if it waited this many seconds
# before the worker got to it (0 = never drop; always voice every line). Leave at
# 0 unless a backlog keeps narrating after a group conversation has already moved
# on — then set it high enough (e.g. 60) that it only prunes a genuinely
# abandoned queue, never a line waiting behind one legitimately long line.
MAX_QUEUE_AGE = 0.0

# DEBUG — log all non-health HTTP calls:
DEBUG_REQUESTS = False

# --- Persistent log file ---
# Mirror everything the proxy prints to a timestamped file next to this script,
# so a conversation can be reviewed after the fact (the console alone is
# ephemeral). Useful for diagnosing group-conversation ordering: every request
# is logged with its arrival "seq" and time, and every line with the order it was
# actually played. LOG_FILE "" = proxy_log.txt beside this script.
LOG_TO_FILE = True
LOG_FILE = ""
LOG_MAX_BYTES = 5_000_000   # start a fresh file once it grows past this

# --- Passthrough (LLM chat etc.) ---
# Every Player2 call that isn't TTS — including the LLM chat completion — is
# forwarded by the passthrough route below. LLM generations, especially slower /
# cheaper models like DeepSeek, can take a while; the old hard 30s cut them off,
# which AI Influence then shows as "no response" (while Player2 may still bill the
# upstream call). Give slow completions room to finish.
PASSTHROUGH_TIMEOUT = 120   # seconds to wait on a forwarded Player2 call
# Log forwarded request+response bodies (chat prompts/replies, errors) to help
# diagnose model failures. Health pings are excluded. Bodies are your own local
# single-player data. Set False once you're done diagnosing to keep logs small.
LOG_CHAT = True

# ============================================================
#  VOICE DATABASE  (from Player2 /tts/voices endpoint)
# ============================================================

VOICE_DB = {
    "01955d76-ed5b-73e0-a88d-cbeb3c5b499d": {"name": "Sophia",    "gender": "female", "lang": "american_english"},
    "01955d76-ed5b-7407-a03c-cdd993439ba4": {"name": "Madison",   "gender": "female", "lang": "american_english"},
    "01955d76-ed5b-7416-82d8-5fc486e2f676": {"name": "Harper",    "gender": "female", "lang": "american_english"},
    "01955d76-ed5b-7426-8748-4b0e5aea1974": {"name": "Olivia",    "gender": "female", "lang": "american_english"},
    "01955d76-ed5b-7436-a182-c4d21aaca9fc": {"name": "Ava",       "gender": "female", "lang": "american_english"},
    "01955d76-ed5b-7441-a184-5f5ee015e4fe": {"name": "Amelia",    "gender": "female", "lang": "american_english"},
    "01955d76-ed5b-7451-92d6-5ef579d3ed28": {"name": "Charlotte", "gender": "female", "lang": "american_english"},
    "01955d76-ed5b-745d-add1-b755d440192d": {"name": "Evelyn",    "gender": "female", "lang": "american_english"},
    "01955d76-ed5b-7468-83a7-bfc267cf4849": {"name": "Abigail",   "gender": "female", "lang": "american_english"},
    "01955d76-ed5b-7474-86b2-a41b310c2a2d": {"name": "Mia",       "gender": "female", "lang": "american_english"},
    "01955d76-ed5b-7480-951c-af1dd9873e34": {"name": "Chloe",     "gender": "female", "lang": "american_english"},
    "01955d76-ed5b-748c-8d98-0fb708ef0fbd": {"name": "Ethan",     "gender": "male",   "lang": "american_english"},
    "01955d76-ed5b-7497-9f8e-0e7448515bf3": {"name": "Noah",      "gender": "male",   "lang": "american_english"},
    "01955d76-ed5b-74a3-9129-c3253d01f690": {"name": "Mason",     "gender": "male",   "lang": "american_english"},
    "01955d76-ed5b-74af-a2be-9302077075b8": {"name": "Logan",     "gender": "male",   "lang": "american_english"},
    "01955d76-ed5b-74ba-89e5-2b4b45e632cd": {"name": "Benjamin",  "gender": "male",   "lang": "american_english"},
    "01955d76-ed5b-74c6-ac15-ab68ee19d560": {"name": "Lucas",     "gender": "male",   "lang": "american_english"},
    "01955d76-ed5b-74d2-a33c-b2b8e998658f": {"name": "Jackson",   "gender": "male",   "lang": "american_english"},
    "01955d76-ed5b-74de-83e5-800a44fee0d1": {"name": "Caleb",     "gender": "male",   "lang": "american_english"},
    "01955d76-ed5b-74e9-9fea-1f8cad1cd9c5": {"name": "Nicholas",  "gender": "male",   "lang": "american_english"},
    "01955d76-ed5b-74f9-b54a-2d051890468d": {"name": "Eleanor",   "gender": "female", "lang": "british_english"},
    "01955d76-ed5b-751c-b341-0ee85dbefd92": {"name": "Poppy",     "gender": "female", "lang": "british_english"},
    "01955d76-ed5b-7528-86ee-3348a642af7e": {"name": "Florence",  "gender": "female", "lang": "british_english"},
    "01955d76-ed5b-7534-b7a6-028adcfb4e7d": {"name": "Amelia",    "gender": "female", "lang": "british_english"},
    "01955d76-ed5b-753f-9f74-c0674216f0f5": {"name": "Oliver",    "gender": "male",   "lang": "british_english"},
    "01955d76-ed5b-754f-a070-a570ddfed516": {"name": "Harry",     "gender": "male",   "lang": "british_english"},
    "01955d76-ed5b-755b-9b43-890d73586908": {"name": "William",   "gender": "male",   "lang": "british_english"},
    "01955d76-ed5b-7566-9c0e-bce4d88ceba0": {"name": "Charles",   "gender": "male",   "lang": "british_english"},
    "01955d76-ed5b-757a-9bdb-94fa0a2b7893": {"name": "Sakura",    "gender": "female", "lang": "japanese"},
    "01955d76-ed5b-7591-9d3f-f919ac645bb6": {"name": "Akari",     "gender": "female", "lang": "japanese"},
    "01955d76-ed5b-75a1-96f8-7a82e767e2c4": {"name": "Yuki",      "gender": "female", "lang": "japanese"},
    "01955d76-ed5b-75ad-afe3-ac5eb3d0a16e": {"name": "Hana",      "gender": "female", "lang": "japanese"},
    "01955d76-ed5b-75b8-b70f-dfaf400b7c42": {"name": "Takashi",   "gender": "male",   "lang": "japanese"},
    "01955d76-ed5b-75c8-8386-b83ff9c45856": {"name": "Mei",       "gender": "female", "lang": "mandarin_chinese"},
    "01955d76-ed5b-75d4-8338-3d7108137cd1": {"name": "Ling",      "gender": "female", "lang": "mandarin_chinese"},
    "01955d76-ed5b-75df-8ca5-a6f84acaff76": {"name": "Jingyi",    "gender": "female", "lang": "mandarin_chinese"},
    "01955d76-ed5b-75eb-b509-e7bf29b3b530": {"name": "Qiuyue",    "gender": "female", "lang": "mandarin_chinese"},
    "01955d76-ed5b-75fb-87dd-ebbed25d2585": {"name": "Wei",       "gender": "male",   "lang": "mandarin_chinese"},
    "01955d76-ed5b-7606-9e21-8b236fbe12a8": {"name": "Liang",     "gender": "male",   "lang": "mandarin_chinese"},
    "01955d76-ed5b-7612-bf44-f7bdcc808356": {"name": "Ming",      "gender": "male",   "lang": "mandarin_chinese"},
    "01955d76-ed5b-761e-abac-1956f66ac089": {"name": "Hao",       "gender": "male",   "lang": "mandarin_chinese"},
    "01955d76-ed5b-762a-9a2a-0fec3b7ace8b": {"name": "Carmen",    "gender": "female", "lang": "spanish"},
    "01955d76-ed5b-7649-ac1e-c56a13c3302f": {"name": "Miguel",    "gender": "male",   "lang": "spanish"},
    "01955d76-ed5b-7655-98bb-fd7578af9617": {"name": "Javier",    "gender": "male",   "lang": "spanish"},
    "01955d76-ed5b-7668-877b-2fa240c1d5ee": {"name": "Sophie",    "gender": "female", "lang": "french"},
    "01955d76-ed5b-7678-b678-3ddc5ec8b5c4": {"name": "Priya",     "gender": "female", "lang": "hindi"},
    "01955d76-ed5b-7683-a79d-253390189fdb": {"name": "Aditi",     "gender": "female", "lang": "hindi"},
    "01955d76-ed5b-768f-9e5b-8bcc89ba8f3d": {"name": "Arjun",     "gender": "male",   "lang": "hindi"},
    "01955d76-ed5b-769b-bd00-002a8e88dc65": {"name": "Vikram",    "gender": "male",   "lang": "hindi"},
    "01955d76-ed5b-76ab-bc6b-57cc5dfeaf01": {"name": "Bianca",    "gender": "female", "lang": "italian"},
    "01955d76-ed5b-76ba-898e-c65bd579a334": {"name": "Marco",     "gender": "male",   "lang": "italian"},
    "01955d76-ed5b-76c6-8b9e-b713d3f0b866": {"name": "Isabela",   "gender": "female", "lang": "brazilian_portuguese"},
    "01955d76-ed5b-76d2-8f05-b9a34b5f9011": {"name": "Gabriel",   "gender": "male",   "lang": "brazilian_portuguese"},
    "01955d76-ed5b-76dd-bef6-37119ea2f99f": {"name": "Rafael",    "gender": "male",   "lang": "brazilian_portuguese"},
}

# English voice pools for auto-fix (non-English UUID → replaced with English equivalent)
ENGLISH_MALE_VOICES = [
    "01955d76-ed5b-7497-9f8e-0e7448515bf3",  # Noah
    "01955d76-ed5b-74a3-9129-c3253d01f690",  # Mason
    "01955d76-ed5b-74af-a2be-9302077075b8",  # Logan
    "01955d76-ed5b-74ba-89e5-2b4b45e632cd",  # Benjamin
    "01955d76-ed5b-74c6-ac15-ab68ee19d560",  # Lucas
    "01955d76-ed5b-74d2-a33c-b2b8e998658f",  # Jackson
    "01955d76-ed5b-74de-83e5-800a44fee0d1",  # Caleb
    "01955d76-ed5b-74e9-9fea-1f8cad1cd9c5",  # Nicholas
    "01955d76-ed5b-753f-9f74-c0674216f0f5",  # Oliver
    "01955d76-ed5b-754f-a070-a570ddfed516",  # Harry
    "01955d76-ed5b-755b-9b43-890d73586908",  # William
    "01955d76-ed5b-7566-9c0e-bce4d88ceba0",  # Charles
]
ENGLISH_FEMALE_VOICES = [
    "01955d76-ed5b-7407-a03c-cdd993439ba4",  # Madison
    "01955d76-ed5b-7416-82d8-5fc486e2f676",  # Harper
    "01955d76-ed5b-7426-8748-4b0e5aea1974",  # Olivia
    "01955d76-ed5b-7436-a182-c4d21aaca9fc",  # Ava
    "01955d76-ed5b-7441-a184-5f5ee015e4fe",  # Amelia
    "01955d76-ed5b-7451-92d6-5ef579d3ed28",  # Charlotte
    "01955d76-ed5b-745d-add1-b755d440192d",  # Evelyn
    "01955d76-ed5b-7468-83a7-bfc267cf4849",  # Abigail
    "01955d76-ed5b-7474-86b2-a41b310c2a2d",  # Mia
    "01955d76-ed5b-7480-951c-af1dd9873e34",  # Chloe
    "01955d76-ed5b-74f9-b54a-2d051890468d",  # Eleanor
    "01955d76-ed5b-751c-b341-0ee85dbefd92",  # Poppy
    "01955d76-ed5b-7528-86ee-3348a642af7e",  # Florence
]

# Cache: NPC StringId → assigned English voice (legacy; kept for compatibility)
_npc_voice_assignment = {}

# Cache: source voice UUID → assigned English voice.
# Keyed on the SOURCE voice (which is stable for a character across every chunk
# of a line and across sessions) rather than the per-request, guessed NPC id —
# this is what keeps a character's voice from changing after a narrator interruption.
_voice_remap_cache = {}


def _stable_index(key, n):
    """Process-independent index in [0, n). Unlike hash(), this never changes
    between runs, so a character keeps the same remapped voice every session."""
    digest = hashlib.md5((key or "").encode("utf-8")).hexdigest()
    return int(digest, 16) % max(1, n)


# Cache: NPC file path → number of ConversationHistory entries last seen
# Used to detect genuinely NEW messages (not replay of old ones)
_npc_history_seen = {}

# ---- Ordered playback queue ----
# All /v1/tts/speak requests are voiced by a SINGLE worker thread in strict
# arrival order. AI Influence group conversations fire several lines in quick
# succession; handling each in its own racing thread (as before) let a later
# line's audio start before an earlier line's — so a reply could be spoken
# before the line it answered. Funnelling everything through one FIFO queue
# guarantees lines play in the order the mod sent them, and also removes the
# audio overlap that used to drop/silence lines (so the old per-line
# "generation" supersede is no longer needed).
_play_queue = collections.deque()
_play_cond = threading.Condition()
_play_seq_counter = 0

# What the worker is voicing right now, and a flag to cut it short. Used to stop
# the player's own line the instant the NPC's reply is ready.
#
# Note: Player2's /tts/speak returns when GENERATION finishes, not when the audio
# stops playing — measured ~7.1s for a 9.8s line. So a player line can still be
# audible after its job is "done", and we track that separately.
_playback_state = {"kind": None, "seq": None}
_playback_cancel = threading.Event()
_player_audio_pending = False   # a player line may still be sounding


def _stop_player2_audio():
    """Ask Player2 to stop whatever it is currently speaking."""
    try:
        requests.post(f"{REAL_PLAYER2}/v1/tts/stop",
                      headers=_game_headers(), timeout=5)
    except Exception as e:
        print(f"  [interrupt] tts/stop failed: {e}")




# ============================================================
#  INTERNAL CACHE
# ============================================================

_npc_cache = {}
_cache_mtime = {}
_missing_said = {}


def switch_campaign_if_needed():
    """
    Move to the campaign the game is writing to, if that is not ours.

    Called every few seconds by the narrator. Returns the new folder when it
    switched, else None. Only a campaign written to AFTER ours counts, so two
    campaigns never trade places back and forth.
    """
    global _RESOLVED_NPC_FOLDER
    if not FOLLOW_ACTIVE_CAMPAIGN or NPC_FOLDER.strip():
        return None
    current = _RESOLVED_NPC_FOLDER or ""
    saves = find_all_save_subfolders()
    if not saves:
        return None
    best = saves[0]
    if os.path.normcase(best) == os.path.normcase(current):
        return None
    if os.path.isdir(current) and campaign_last_written(best) <= campaign_last_written(current):
        return None
    _RESOLVED_NPC_FOLDER = best
    _npc_cache.clear()
    _cache_mtime.clear()
    _missing_said.clear()
    _save_config(best)
    return best

# ============================================================
#  FUNCTIONS
# ============================================================

def load_all_npc_data():
    """Load (or reload if changed) all NPC JSON files into memory cache."""
    folder = get_npc_folder()
    if not folder or not os.path.exists(folder):
        # Said once per folder, not on every look (a deleted campaign filled
        # the log with thousands of these). The narrator moves to the campaign
        # being played on its own; see switch_campaign_if_needed().
        if _missing_said.get("folder") != folder:
            _missing_said["folder"] = folder
            print(f"  The campaign folder is gone: {folder}")
        return {}
    for filename in os.listdir(folder):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(folder, filename)
        try:
            mtime = os.path.getmtime(filepath)
            if _cache_mtime.get(filepath) == mtime:
                continue  # Not changed, skip
            with open_shared(filepath) as f:
                data = json.load(f)
            if not isinstance(data, dict):
                continue  # Skip list-type JSON files (e.g. diplomatic_statements.json)
            _npc_cache[filepath] = data
            _cache_mtime[filepath] = mtime
        except (FileNotFoundError, PermissionError):
            continue  # mid-save by the mod; read on the next pass
        except Exception as e:
            print(f"  ERROR reading {filename}: {e}")
    return _npc_cache


def _autoclose_actions(text):
    """
    Close an *action* that was opened but never closed.

    It's easy to type "**He draws his sword" and forget the closing ** when the
    action ends the message. Without this the asterisks are left in the text and
    spoken as dialogue instead of being routed to the narrator, so we treat an
    unmatched opener as running to the end of the message.

    Deliberately conservative — only fires when the opener looks like an action
    marker: at the start or after whitespace, and immediately followed by a
    non-space character. That leaves arithmetic ("5 * 3") and stray trailing
    asterisks alone.
    """
    if not text or "*" not in text:
        return text
    runs = list(re.finditer(r'\*+', text))
    if len(runs) % 2 == 0:
        return text                       # balanced — nothing to close
    opener = runs[-1]                     # the odd one out opened something
    before = text[:opener.start()]
    after = text[opener.end():]
    if not after.strip() or after[:1].isspace():
        return text                       # stray asterisks, not an action opener
    if before and not before[-1].isspace():
        return text                       # mid-word/mid-number asterisk
    return text.rstrip() + opener.group(0)


def strip_actions(text):
    """Remove *action text* (single or **double** asterisks) and normalize."""
    text = re.sub(r'\*+[^*]+\*+', '', _autoclose_actions(text))
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _entry_speaker_id(entry):
    """
    Parse a ConversationHistory line of the form '<label>: <text>'.

    The updated AI Influence mod embeds each speaker's StringId in backticks
    inside the label, e.g.:
        "Я (Aegon Targaryen, `ROTlord_369`): ..."             <- the NPC, first person
        "Unidentified person (`main_hero`): ..."              <- the player
        "Viserys Targaryen (as introduced, `main_hero`): ..."  <- the player

    Returns (speaker_id, text):
      speaker_id : the id found in backticks (e.g. 'ROTlord_369', 'main_hero'),
                   or None if the line has no parseable label.
      text       : everything after the first ': ' (keeps *action* asterisks).
    """
    if not isinstance(entry, str) or ": " not in entry:
        return None, None
    label, text = entry.split(": ", 1)
    m = re.search(r'`([^`]+)`', label)
    return (m.group(1) if m else None), text


def _player_id(data):
    """The player's bind id for this save file (defaults to 'main_hero')."""
    return (data or {}).get("player_bind_string_id", "main_hero") or "main_hero"


# Words that start a TITLE rather than a personal name. Needed because the mod's
# single Name field holds two different shapes:
#   "King of the Seven Kingdoms Joffrey Baratheon"  -> title first, name last
#   "Alaric of Long Lake"                           -> the whole thing IS the name
# Trimming the second shape the way the first needs would leave "Long Lake".
_TITLE_WORDS = {
    "king", "queen", "lord", "lady", "ser", "prince", "princess", "warden",
    "magister", "maester", "septon", "septa", "high", "first", "khal", "archon",
    "god-emperor", "commander", "hand", "protector", "regent",
}


def speaker_label(name):
    """
    A short, unambiguous way to say who is speaking.

    Long titles are dropped and the personal name kept, but only where the
    leading word really is a title — "Moqorro of Tasko" is a name, not a rank.
    Anything already short is left exactly as it is.
    """
    parts = (name or "").split()
    if not parts:
        return ""
    if parts[0].lower().strip(",.") in _TITLE_WORDS and len(parts) >= 5:
        # "Lord Commander of the Night's Watch Alliser Thorne" -> "Alliser Thorne"
        return " ".join(parts[-2:])
    if len(parts) >= 5 and any(w.lower() == "of" for w in parts[1:]):
        # "Warren of The Inn of the Kneeling Man" -> "Warren"
        return parts[0]
    return " ".join(parts)


# The last speaker announced, so someone continuing across two lines isn't
# named twice in a row.
_last_announced_speaker = None


def _reset_announced_speaker():
    """Forget the last speaker, so the next group conversation opens with a name."""
    global _last_announced_speaker
    _last_announced_speaker = None


def announce_speaker(segments, npc_data):
    """
    Put the speaker's name in front of their line, as narrator speech.

    Folded into a leading narrator segment where one exists, so the common case
    (a line that opens with an *action*) costs no additional TTS call.
    """
    global _last_announced_speaker
    if not ANNOUNCE_SPEAKER_IN_GROUP or not segments:
        return segments
    label = speaker_label((npc_data or {}).get("Name"))
    if not label:
        return segments
    if ANNOUNCE_SPEAKER_SKIP_REPEAT and label == _last_announced_speaker:
        print(f"  [GROUP] {label} is still speaking — not re-announcing.")
        return segments
    _last_announced_speaker = label
    free = segments[0][0] == NARRATOR_VOICE
    print(f"  [GROUP] Announcing speaker: {label}"
          + ("  (folded into the opening action)" if free else "  (+1 short call)"))
    return _merge_adjacent([(NARRATOR_VOICE, label)] + list(segments))


def is_group_conversation(npc_data):
    """
    True if this NPC's CURRENT dialogue scene is a group conversation.

    AI Influence records everything an NPC hears in DialogueObservations, each
    tagged with a scene_id and the speaker (speaker_hero_id / is_player). We scope
    to the latest scene so a lord who was in a group court yesterday but is now in
    a private 1-on-1 is correctly seen as 1-on-1.

    Two signals, either is enough:
      1. The scene_id is prefixed "group:" — AI Influence's own tag for a group
         conversation ("dialog:" is a normal 1-on-1). This is set from the start,
         so it catches even the FIRST speaker's line (before it has heard anyone
         else) — which the observation-based check below cannot.
      2. The NPC has already heard at least one OTHER npc speak in this scene.
    """
    if not isinstance(npc_data, dict):
        return False
    obs = npc_data.get("DialogueObservations") or []
    if not obs:
        return False
    # Current scene = scene_id of the most recent observation that has one.
    scene = None
    for o in reversed(obs):
        if isinstance(o, dict) and o.get("scene_id"):
            scene = o["scene_id"]
            break
    if not scene:
        return False
    # 1) AI Influence's explicit group tag.
    if str(scene).startswith("group:"):
        return True
    # 2) Heard another npc speak in this scene.
    self_id   = npc_data.get("StringId")
    player_id = _player_id(npc_data)
    for o in obs:
        if not isinstance(o, dict) or o.get("scene_id") != scene:
            continue
        if o.get("is_player"):
            continue
        sid = o.get("speaker_hero_id")
        if sid and sid != self_id and sid != player_id:
            return True   # heard another npc in this scene → group
    return False


def _normalize_for_match(s):
    """Lowercase, drop *actions*, strip punctuation, collapse whitespace."""
    s = strip_actions(s or "")
    s = re.sub(r'[^a-z0-9 ]', '', s.lower())
    return re.sub(r'\s+', ' ', s).strip()


def _texts_match(a, b):
    """
    True if two lines are plausibly the SAME spoken line, ignoring *actions*,
    case, punctuation and whitespace.

    Used to verify that text recovered from the save_data JSON is actually the
    line the mod just asked us to speak. Biased to avoid FALSE POSITIVES: if it
    wrongly said two different lines match we would narrate the wrong one, so a
    near-miss is treated as "no match" (we then fall back to the mod's own text,
    which is always the correct current line — just without recovered asterisks).
    """
    import difflib
    na, nb = _normalize_for_match(a), _normalize_for_match(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    # One is a substantial substring of the other (e.g. the mod trimmed/truncated)
    shorter, longer = (na, nb) if len(na) <= len(nb) else (nb, na)
    if len(shorter) >= 12 and shorter in longer:
        return True
    # Sequence similarity — two genuinely different conversations score low here
    # even when they share names/vocabulary, because order differs.
    return difflib.SequenceMatcher(None, na, nb).ratio() >= MATCH_RATIO_THRESHOLD


# Phrases AI Influence writes as the NPC line when Player2's LLM fails to answer.
# In 5.0.3 these land in ConversationHistory / LastAIResponseSummary like any
# real line, so without this the narrator would voice them in a lord's voice.
ERROR_TEXT_MARKERS = (
    "i am unable to respond right now",
    "please check if player2 application is installed",
    "ensure your device has sufficient battery",
)


def _is_error_text(text):
    """True if the text is one of AI Influence's LLM-failure fallback messages."""
    low = (text or "").lower()
    return any(marker in low for marker in ERROR_TEXT_MARKERS)


# ============================================================
#  PLAYER LINE EXTRACTION  (for VOICE_PLAYER_LINES)
# ============================================================
# AI Influence sends several kinds of chat request through this proxy (diplomacy,
# world events, memory pages, character creation, group reply-ordering). Only the
# NPC role-play request carries the player's spoken line, and it's identified by
# this marker at the top of its system prompt.
_DIALOGUE_PROMPT_MARKER = "### Mission ###"

_PLAYER_BIND_ID = None
# Remember plenty of past lines: a group conversation fires one request per NPC
# with the same line, and re-sent prompts can resurface a line from much earlier.
_recent_player_lines = collections.deque(maxlen=200)

# ---- Live player-voice selection ----
# The active voice lives here rather than in the constant, so it can be changed
# on the fly from the tray menu. It's persisted to player_voice.txt, which is
# also re-read when it changes — so editing that file by hand works too, with no
# restart needed.
PLAYER_VOICE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "player_voice.txt")
_player_voice = None
_player_voice_mtime = None

# ---- Live on/off switch for voicing your own lines ----
# Kept in a file so the tray toggle survives a restart, and so it can be flipped
# by hand without one. Defaults to VOICE_PLAYER_LINES above.
PLAYER_LINES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "player_lines_enabled.txt")
_player_lines_on = None
_player_lines_mtime = None


def player_lines_enabled():
    """True if your own lines should be voiced. Re-reads the file when it changes."""
    global _player_lines_on, _player_lines_mtime
    try:
        mtime = os.path.getmtime(PLAYER_LINES_FILE)
    except OSError:
        mtime = None
    if mtime is not None and mtime != _player_lines_mtime:
        try:
            with open(PLAYER_LINES_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip().lower()
                    if line and not line.startswith("#"):
                        _player_lines_on = line in ("1", "on", "true", "yes", "enabled")
                        break
            _player_lines_mtime = mtime
        except Exception as e:
            print(f"  [player] Could not read {PLAYER_LINES_FILE}: {e}")
    if _player_lines_on is None:
        _player_lines_on = VOICE_PLAYER_LINES
    return _player_lines_on


def set_player_lines_enabled(on):
    """Turn voicing of your own lines on or off, and remember it."""
    global _player_lines_on, _player_lines_mtime
    _player_lines_on = bool(on)
    try:
        with open(PLAYER_LINES_FILE, "w", encoding="utf-8") as f:
            f.write("# Voice the player's own lines while the reply generates.\n")
            f.write("# on / off — set from the tray menu, applies immediately.\n")
            f.write(("on" if on else "off") + "\n")
        _player_lines_mtime = os.path.getmtime(PLAYER_LINES_FILE)
    except Exception as e:
        print(f"  [player] Could not save setting: {e}")
    print(f"  [player] Voicing your own lines: {'ON' if on else 'OFF'}")


def _english_voices():
    """English voices grouped for the picker: {(lang, gender): [(id, name), ...]}."""
    groups = {}
    for vid, info in VOICE_DB.items():
        lang = info.get("lang", "")
        if lang not in ("american_english", "british_english"):
            continue
        if vid == NARRATOR_VOICE:      # keep the narrator out of the player list
            continue
        groups.setdefault((lang, info.get("gender", "male")), []).append(
            (vid, info.get("name", vid)))
    for k in groups:
        groups[k].sort(key=lambda t: t[1])
    return groups


def _save_player_voice(vid):
    global _player_voice_mtime
    try:
        with open(PLAYER_VOICE_FILE, "w", encoding="utf-8") as f:
            f.write("# Player TTS voice — set from the tray menu, or edit this id.\n")
            f.write("# Takes effect on the next spoken line; no restart needed.\n")
            f.write(vid + "\n")
        _player_voice_mtime = os.path.getmtime(PLAYER_VOICE_FILE)
    except Exception as e:
        print(f"  [voice] Could not save selection: {e}")


def get_player_voice():
    """
    The player's current voice id. Re-reads player_voice.txt when it changes so a
    hand-edit applies without restarting; otherwise returns the cached choice.
    """
    global _player_voice, _player_voice_mtime
    try:
        mtime = os.path.getmtime(PLAYER_VOICE_FILE)
    except OSError:
        mtime = None
    if mtime is not None and mtime != _player_voice_mtime:
        try:
            with open(PLAYER_VOICE_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if line in VOICE_DB:
                            if line != _player_voice:
                                print(f"  [voice] Player voice -> "
                                      f"{VOICE_DB[line].get('name')} (from file)")
                            _player_voice = line
                        else:
                            print(f"  [voice] Unknown voice id in file: {line}")
                        break
            _player_voice_mtime = mtime
        except Exception as e:
            print(f"  [voice] Could not read {PLAYER_VOICE_FILE}: {e}")
    if not _player_voice:
        _player_voice = PLAYER_VOICE
    return _player_voice


def set_player_voice(vid, audition=None):
    """Switch the player's voice immediately and remember it."""
    global _player_voice
    if vid not in VOICE_DB:
        print(f"  [voice] Unknown voice id: {vid}")
        return
    _player_voice = vid
    _save_player_voice(vid)
    info = VOICE_DB[vid]
    print(f"  [voice] Player voice -> {info.get('name')} "
          f"({info.get('gender')}, {info.get('lang')})")
    if PLAYER_VOICE_AUDITION if audition is None else audition:
        _enqueue_player_job(f"This is {info.get('name')}. "
                            f"Your character will speak with this voice.")


# ============================================================
#  WORLD EVENTS  (hotkey -> narrator reads the latest event)
# ============================================================

WORLD_EVENTS_FILENAME = "aiinfluence_campaign_diplomacy.json"
_event_cursor = 0          # 0 = newest; grows while you keep pressing
_event_last_press = 0.0


def world_events_path():
    """The diplomacy file, which sits beside the NPC files in the save folder."""
    folder = get_npc_folder()
    return os.path.join(folder, WORLD_EVENTS_FILENAME) if folder else None


def read_world_events():
    """
    Every stored world event, newest first.

    Ordered by creation_time rather than campaign day: two events can share a day
    (an execution and the march it caused), and only the timestamp separates
    them — sorting on it reproduces the window's own order.
    """
    path = world_events_path()
    if not path or not os.path.isfile(path):
        print(f"  [events] No world-event file at {path}")
        return []
    try:
        with open_shared(path) as f:
            data = json.load(f)
    except Exception as e:
        print(f"  [events] Could not read {WORLD_EVENTS_FILENAME}: {e}")
        return []
    events = [e for e in (data.get("dynamic_events") or []) if isinstance(e, dict)]
    # The file is written in arrival order, so the position is a dependable
    # tiebreak when two events carry the same timestamp.
    for i, e in enumerate(events):
        e["_source_index"] = i
    events.sort(key=lambda e: (str(e.get("creation_time") or ""),
                               e.get("creation_campaign_days") or 0), reverse=True)
    return events


def _event_arrival_key(event):
    """Sort key putting the event that arrived first, first."""
    return (str(event.get("creation_time") or ""), event.get("_source_index") or 0)


def _event_speech(event):
    """The text to speak for one event: its title, then its description."""
    title = (event.get("title") or "").strip()
    body = (event.get("description") or "").strip()
    if WORLD_EVENT_READ_TITLE and title and body:
        return f"{_ensure_sentence_punctuation(title)} {body}"
    return body or title


def group_world_events_by_day(events=None):
    """
    The events bucketed by campaign day, newest day first, each bucket keeping
    the window's own order.

    The campaign day is what AI Influence labels events by, so a bucket is
    exactly the set the window shows under one heading. Two events can share a
    day while carrying different fractional times — a peace and a feud hours
    apart — and both still belong to that day.
    """
    events = read_world_events() if events is None else events
    buckets, order = {}, []
    for e in events:
        day = e.get("creation_campaign_days")
        if isinstance(day, (int, float)):
            key = int(day)
        else:                      # no campaign day: fall back to the date
            key = str(e.get("creation_time") or "")[:10] or "?"
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(e)
    if (WORLD_EVENT_DAY_ORDER or "chronological").lower() == "chronological":
        for k in buckets:
            buckets[k].sort(key=_event_arrival_key)
    return [(k, buckets[k]) for k in order]


def narrate_world_event_day(index=0):
    """Queue every event from one campaign day, read as one piece."""
    days = group_world_events_by_day()
    if not days:
        print("  [events] No world events recorded yet.")
        return False
    index = max(0, min(index, len(days) - 1))
    day, events = days[index]
    parts = [t for t in (_event_speech(e) for e in events) if t]
    if not parts:
        print("  [events] That day's events have no text to read.")
        return False
    # Each event ends in a full stop, so they don't run into one another.
    text = " ".join(_ensure_sentence_punctuation(t) for t in parts)
    where = "latest day" if index == 0 else f"{index + 1} days back"
    titles = ", ".join(repr(e.get("title")) for e in events)
    print(f"  [events] Reading {len(parts)} event(s) from campaign day {day} "
          f"({where} of {len(days)}): {titles}")
    _enqueue_event_job(text)
    return True


def narrate_world_event(index=0):
    """Queue one world event to be read in the narrator's voice. True if queued."""
    events = read_world_events()
    if not events:
        print("  [events] No world events recorded yet.")
        return False
    index = max(0, min(index, len(events) - 1))
    event = events[index]
    text = _event_speech(event)
    if not text:
        print("  [events] That event has no text to read.")
        return False
    where = "newest" if index == 0 else f"{index + 1} back"
    print(f"  [events] Reading ({where} of {len(events)}): {event.get('title')!r}")
    _enqueue_event_job(text)
    return True


_hotkey_fired_at = 0.0
_hotkey_lock = threading.Lock()


_hotkey_fired = {}


def _fire_hotkey(name, action):
    """
    One press, one reading — even when both watchers notice it. Whichever gets
    here first wins; anything arriving in the same instant is dropped. Keys are
    gated separately, so the two hotkeys never silence one another.
    """
    with _hotkey_lock:
        now = time.time()
        if now - _hotkey_fired.get(name, 0.0) < 0.4:
            return
        _hotkey_fired[name] = now
    action()


def _fire_world_event_hotkey():
    _fire_hotkey("world events", _on_world_event_hotkey)


_NARRATION_KINDS = ("event", "letter")


def _world_event_in_progress():
    """True while an event or letter is being read, or one is waiting its turn."""
    if _playback_state.get("kind") in _NARRATION_KINDS:
        return True
    with _play_cond:
        return any(j.get("kind") in _NARRATION_KINDS for j in _play_queue)


def _interrupt_world_event():
    """
    Stop the event currently being read and discard any others still queued.

    Only event readings are touched: a conversation playing at the time is left
    alone, so asking for an event never talks over a lord mid-sentence.
    """
    with _play_cond:
        kept = [j for j in _play_queue if j.get("kind") not in _NARRATION_KINDS]
        dropped = len(_play_queue) - len(kept)
        _play_queue.clear()
        _play_queue.extend(kept)
    cutting = _playback_state.get("kind") in _NARRATION_KINDS
    if cutting:
        _playback_cancel.set()      # stop before the next segment is sent
        _stop_player2_audio()       # and silence what is already sounding
    if cutting or dropped:
        extra = f", dropped {dropped} waiting" if dropped else ""
        print(f"  [events] Cut off the reading in progress{extra}.")


def _on_world_event_hotkey():
    """
    Hotkey pressed. Read the latest campaign day's events; press again to move
    back a day, cutting off whatever is being read.
    """
    global _event_cursor, _event_last_press
    now = time.time()
    whole_day = WORLD_EVENT_READ_WHOLE_DAY
    total = len(group_world_events_by_day()) if whole_day else len(read_world_events())
    speaking = WORLD_EVENT_INTERRUPT and _world_event_in_progress()
    # Still reading, or pressed again soon after: this is "next one, please".
    # Otherwise the run has ended and we start again from the newest.
    if total and (speaking or now - _event_last_press <= WORLD_EVENT_STEP_SECONDS):
        _event_cursor = (_event_cursor + 1) % total      # wrap round to newest
    else:
        _event_cursor = 0
    _event_last_press = now
    if speaking:
        _interrupt_world_event()
    if whole_day:
        narrate_world_event_day(_event_cursor)
    else:
        narrate_world_event(_event_cursor)


# ---- Global hotkey (Windows) ----
# RegisterHotKey works while Bannerlord has focus, which a key listener inside
# the game window could not. It needs its own thread with a message loop,
# because the hotkey is delivered as a window message to the thread that
# registered it.
_VK_NAMES = {"space": 0x20, "enter": 0x0D, "tab": 0x09, "escape": 0x1B,
             "insert": 0x2D, "delete": 0x2E, "home": 0x24, "end": 0x23,
             "pageup": 0x21, "pagedown": 0x22,
             "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
             # numeric keypad — distinct keys from the row above the letters
             "numadd": 0x6B, "numsubtract": 0x6D, "nummultiply": 0x6A,
             "numdivide": 0x6F, "numdecimal": 0x6E}
_VK_NAMES.update({f"numpad{d}": 0x60 + d for d in range(10)})
_MOD_NAMES = {"alt": 0x0001, "ctrl": 0x0002, "control": 0x0002,
              "shift": 0x0004, "win": 0x0008}
# The keypad symbols can't survive splitting on "+", so they are renamed first.
_HOTKEY_ALIASES = [("numpad+", "numadd"), ("num+", "numadd"),
                   ("numpadplus", "numadd"), ("numpad-", "numsubtract"),
                   ("num-", "numsubtract"), ("numpad*", "nummultiply"),
                   ("numpad/", "numdivide"), ("numpad.", "numdecimal")]


def _parse_hotkey(spec):
    """'ctrl+alt+e' or 'numpad+' -> (modifier flags, virtual key code)."""
    spec = (spec or "").lower().replace(" ", "")
    for alias, name in _HOTKEY_ALIASES:
        spec = spec.replace(alias, name)
    mods, vk = 0, None
    for part in spec.split("+"):
        if not part:
            continue
        if part in _MOD_NAMES:
            mods |= _MOD_NAMES[part]
        elif part in _VK_NAMES:
            vk = _VK_NAMES[part]
        elif re.fullmatch(r"f([1-9]|1[0-2])", part):
            vk = 0x70 + int(part[1:]) - 1
        elif len(part) == 1 and part.isalnum():
            vk = ord(part.upper())
        else:
            return None, None
    return (mods, vk) if vk else (None, None)


def _hotkey_slots():
    """The keys to watch: (label, key spec, what to do, what it reads)."""
    slots = []
    if READ_WORLD_EVENTS:
        slots.append(("events", WORLD_EVENT_HOTKEY, _on_world_event_hotkey,
                      "the latest world events"))
    if READ_LETTERS:
        slots.append(("letters", LETTER_HOTKEY, _on_letter_hotkey,
                      "the latest letter"))
    return slots


def _world_event_hotkey_loop():
    """
    Reserve every hotkey and wait for presses.

    All of them are registered on THIS thread, because Windows delivers the
    press as a message to whichever thread registered the key — a second thread
    would never hear about the first thread's keys.
    """
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    MOD_NOREPEAT = 0x4000          # holding the key must not repeat the reading
    registered = {}
    for i, (label, spec, action, reads) in enumerate(_hotkey_slots(), start=1):
        mods, vk = _parse_hotkey(spec)
        if not vk:
            print(f"  [{label}] Could not understand {spec!r} — hotkey disabled.")
            continue
        if not user32.RegisterHotKey(None, i, mods | MOD_NOREPEAT, vk):
            if (WORLD_EVENT_HOTKEY_MODE or "auto").lower() == "auto":
                print(f"  [{label}] Could not reserve {spec.upper()} "
                      f"(another program has it) — the direct key watch still works.")
            else:
                print(f"  [{label}] {spec.upper()} is already taken by another "
                      f"program — pick a different key.")
            continue
        registered[i] = (label, spec, action)
        print(f"  [{label}] Press {spec.upper()} in game to hear {reads} "
              f"(again to step back).")
    if not registered:
        return
    msg = wintypes.MSG()
    try:
        while True:
            got = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if got in (0, -1):
                break
            if msg.message == 0x0312:        # WM_HOTKEY
                slot = registered.get(msg.wParam)
                if not slot:
                    continue
                label, spec, action = slot
                try:
                    _fire_hotkey(label, action)
                except Exception as e:
                    print(f"  [{label}] Could not read it: {e}")
    finally:
        for i in registered:
            user32.UnregisterHotKey(None, i)


_MOD_VKS = {0x0001: 0x12, 0x0002: 0x11, 0x0004: 0x10}   # alt, ctrl, shift


def _world_event_poll_loop():
    """
    Watch the keys' own state instead of asking Windows to reserve them.

    Reading key state is not blocked the way hotkey delivery is, so this keeps
    working while an elevated Bannerlord has focus and without the proxy running
    as administrator. It also does not consume the key, so the game still sees
    it — pick keys the game doesn't need, or they will do both things at once.
    """
    import ctypes
    user32 = ctypes.windll.user32
    watched = []
    for label, spec, action, _reads in _hotkey_slots():
        mods, vk = _parse_hotkey(spec)
        if vk:
            watched.append({"label": label, "vk": vk, "action": action,
                            "mods": [m for m in _MOD_VKS if mods & m],
                            "was_down": False})
    if not watched:
        return
    print(f"  [hotkeys] Also watching "
          f"{', '.join(w['label'] for w in watched)} directly "
          f"(works without administrator rights).")
    while True:
        try:
            for w in watched:
                down = bool(user32.GetAsyncKeyState(w["vk"]) & 0x8000)
                if down and w["mods"]:
                    down = all(user32.GetAsyncKeyState(_MOD_VKS[m]) & 0x8000
                               for m in w["mods"])
                if down and not w["was_down"]:
                    w["was_down"] = True
                    try:
                        _fire_hotkey(w["label"], w["action"])
                    except Exception as e:
                        print(f"  [{w['label']}] Could not read it: {e}")
                elif not down:
                    w["was_down"] = False
        except Exception as e:
            print(f"  [hotkeys] Key watch stopped: {e}")
            return
        time.sleep(WORLD_EVENT_POLL_SECONDS)


def _start_world_event_hotkey():
    if not _hotkey_slots():
        return
    if os.name != "nt":
        print("  [events] The hotkey is Windows-only; skipped.")
        return
    mode = (WORLD_EVENT_HOTKEY_MODE or "auto").lower()
    if mode in ("auto", "register"):
        threading.Thread(target=_world_event_hotkey_loop, daemon=True).start()
    if mode in ("auto", "poll"):
        threading.Thread(target=_world_event_poll_loop, daemon=True).start()


# ============================================================
#  LETTERS  (hotkey -> narrator reads the latest letter)
# ============================================================

LETTERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "letters.json")
_letter_cursor = 0
_letter_last_press = 0.0


# Phrases that only appear when the mod is asking for a WRITTEN message. Taken
# from its own prompt templates: InitiativeMessengerContact.txt (a lord writing
# to you first — the "Messenger from ..." popup) and InitiativeLetterResponse.txt
# (a reply to a letter you sent). Several are listed because those templates
# live under save_data and can be edited, so no single line is guaranteed.
_LETTER_REQUEST_MARKERS = (
    "SPECIAL SITUATION: YOU INITIATED CONTACT",
    "SPECIAL SITUATION: YOU RECEIVED A LETTER",
    "This is a WRITTEN MESSAGE",
    "For written letters only",
    "as on parchment",
    # the same string as _LETTER_PROMPT_MARKER, spelled out because that
    # constant is defined further down the file than this list
    "Dialogue only, no action descriptions",
)


def _is_letter_request(body):
    """True if this chat request is the mod asking an NPC to write a letter."""
    if not READ_LETTERS or not body:
        return False
    try:
        text = body.decode("utf-8", "replace")
    except Exception:
        return False
    return any(m in text for m in _LETTER_REQUEST_MARKERS)


def read_letters():
    """Letters captured so far, newest first."""
    try:
        if os.path.isfile(LETTERS_FILE):
            with open(LETTERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return [e for e in data if isinstance(e, dict) and e.get("text")]
    except Exception as e:
        print(f"  [letters] Could not read {os.path.basename(LETTERS_FILE)}: {e}")
    return []


def _save_letters(letters):
    try:
        with open(LETTERS_FILE, "w", encoding="utf-8") as f:
            json.dump(letters[:LETTER_KEEP], f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"  [letters] Could not save {os.path.basename(LETTERS_FILE)}: {e}")


def _letter_text_from_reply(raw):
    """
    Pull the letter out of Player2's reply.

    The reply is a chat completion whose message content is itself JSON, with
    the letter under "response" alongside the character's private reasoning —
    so take that field rather than the whole blob, and fall back to the
    thought-stripper if the shape is not what we expect.
    """
    try:
        outer = json.loads(raw.decode("utf-8", "replace"))
        content = outer["choices"][0]["message"]["content"]
    except Exception:
        return ""
    content = re.sub(r"^\s*```(?:json)?|```\s*$", "", str(content).strip())
    try:
        inner = json.loads(content)
        if isinstance(inner, dict) and inner.get("response"):
            return str(inner["response"]).strip()
    except Exception:
        pass
    cleaned, _ = strip_internal_thoughts(content)
    return (cleaned or "").strip()


def _capture_letter(raw):
    """Remember a letter as it passes through, newest first."""
    text = _letter_text_from_reply(raw)
    if not text or _is_error_text(text):
        return
    letters = read_letters()
    if letters and _texts_match(letters[0].get("text", ""), text):
        return                      # the same letter arriving twice
    letters.insert(0, {"text": text, "sender": "",
                       "at": time.strftime("%Y-%m-%d %H:%M:%S")})
    _save_letters(letters)
    print(f"  [letters] Letter received ({len(text)} chars) — "
          f"press {LETTER_HOTKEY.upper()} to hear it.")


def _letter_sender_name(text):
    """
    Who wrote it. The mod stores a character's latest letter in their own file
    under LastDynamicResponse, so an exact match there names the sender. Looked
    up when the letter is read, not when captured — the file is written a moment
    after the reply comes back.
    """
    target = _normalize_for_match(text)
    if not target:
        return ""
    try:
        npcs = list(load_all_npc_data().items())
    except Exception as e:
        print(f"  [letters] Could not identify the sender: {e}")
        return ""
    # Fast path: the letter is still that character's most recent response.
    for _path, d in npcs:
        if not isinstance(d, dict):
            continue
        last = d.get("LastDynamicResponse") or ""
        if last and _normalize_for_match(last) == target:
            return (d.get("Name") or "").strip()
    # LastDynamicResponse is overwritten the moment that character next speaks,
    # so fall back to their conversation history, where the letter stays.
    for _path, d in npcs:
        if not isinstance(d, dict):
            continue
        for entry in reversed((d.get("ConversationHistory") or [])[-40:]):
            if not isinstance(entry, str) or ": " not in entry:
                continue
            label, body = entry.split(": ", 1)
            if _normalize_for_match(body) == target:
                # The label is the sender's name; letters carry no `id` tag.
                return (d.get("Name") or label).strip()
    return ""


def narrate_letter(index=0):
    """Queue one letter to be read in the narrator's voice."""
    letters = read_letters()
    if not letters:
        print("  [letters] No letters received yet.")
        return False
    index = max(0, min(index, len(letters) - 1))
    entry = letters[index]
    sender = entry.get("sender") or _letter_sender_name(entry.get("text", ""))
    if sender and sender != entry.get("sender"):
        entry["sender"] = sender
        _save_letters(letters)
    body = entry.get("text", "")
    if LETTER_ANNOUNCE_SENDER and sender:
        text = f"A letter from {_ensure_sentence_punctuation(speaker_label(sender))} {body}"
    else:
        text = body
    where = "newest" if index == 0 else f"{index + 1} back"
    print(f"  [letters] Reading ({where} of {len(letters)})"
          f"{' from ' + sender if sender else ''}.")
    _enqueue_letter_job(text)
    return True


def _on_letter_hotkey():
    """Newest letter; press again to step back, cutting off what is being read."""
    global _letter_cursor, _letter_last_press
    now = time.time()
    total = len(read_letters())
    speaking = WORLD_EVENT_INTERRUPT and _world_event_in_progress()
    if total and (speaking or now - _letter_last_press <= WORLD_EVENT_STEP_SECONDS):
        _letter_cursor = (_letter_cursor + 1) % total
    else:
        _letter_cursor = 0
    _letter_last_press = now
    if speaking:
        _interrupt_world_event()
    narrate_letter(_letter_cursor)


def _enqueue_letter_job(text):
    """Queue a letter to be read in the narrator's voice."""
    global _play_seq_counter
    with _play_cond:
        _play_seq_counter += 1
        _play_queue.append({
            "kind": "letter", "seq": _play_seq_counter, "text": text,
            "voice_id": NARRATOR_VOICE, "speed": NARRATOR_SPEED or 1.0,
            "ts": time.time(),
        })
        _play_cond.notify()


def _enqueue_event_job(text):
    """Queue a world event to be read in the narrator's voice."""
    global _play_seq_counter
    with _play_cond:
        _play_seq_counter += 1
        _play_queue.append({
            "kind": "event", "seq": _play_seq_counter, "text": text,
            "voice_id": NARRATOR_VOICE, "speed": NARRATOR_SPEED or 1.0,
            "ts": time.time(),
        })
        _play_cond.notify()


def _enqueue_player_job(text):
    """Queue a line to be spoken in the player's voice (used for auditions)."""
    global _play_seq_counter
    with _play_cond:
        _play_seq_counter += 1
        _play_queue.append({
            "kind": "player", "seq": _play_seq_counter, "text": text,
            "voice_id": get_player_voice(), "speed": 1.0, "ts": time.time(),
        })
        _play_cond.notify()


def _player_bind_id():
    """
    The player's hero id as AI Influence writes it in conversation lines
    (e.g. 'main_hero', or a ROTlord_* id when playing an existing lord).
    Read once from the save data and cached.
    """
    global _PLAYER_BIND_ID
    if _PLAYER_BIND_ID:
        return _PLAYER_BIND_ID
    for data in _npc_cache.values():                 # already-loaded files first
        pid = data.get("player_bind_string_id")
        if pid:
            _PLAYER_BIND_ID = pid
            return pid
    folder = get_npc_folder()                        # else peek at a few files
    if folder and os.path.isdir(folder):
        try:
            for name in os.listdir(folder)[:60]:
                if not name.endswith(".json"):
                    continue
                try:
                    with open_shared(os.path.join(folder, name)) as f:
                        pid = json.load(f).get("player_bind_string_id")
                except Exception:
                    continue
                if pid:
                    _PLAYER_BIND_ID = pid
                    return pid
        except Exception:
            pass
    _PLAYER_BIND_ID = "main_hero"
    return _PLAYER_BIND_ID


def _strip_speaker_label(line):
    """Drop a leading 'Name (`id`): ' / 'Name: ' label from a conversation line."""
    s = (line or "").strip()
    m = re.match(r'^[^\n:]{0,80}?\(`[^`]+`\)\s*:\s*(.+)$', s, re.DOTALL)
    if m:
        return m.group(1).strip()
    return s


# The transcript lives under this header; everything else in the prompt is
# context (world state, relations, character sheets) and must never be voiced.
_HISTORY_HEADER_RE = re.compile(r'^[ \t]*#{2,}[ \t]*Conversation history[ \t]*#*[ \t]*$',
                                re.IGNORECASE | re.MULTILINE)
_NEXT_SECTION_RE = re.compile(r'^[ \t]*#{2,}[ \t]*\S', re.MULTILINE)


def _conversation_section(text):
    """
    Return just the '### Conversation history ###' block, or None if absent.

    Scoping to it is essential: AI Influence also emits relation lines such as
        Jon Snow (`main_hero`): positive.
    which are structurally identical to dialogue and would otherwise be spoken.
    """
    if not text:
        return None
    m = _HISTORY_HEADER_RE.search(text)
    if not m:
        return None
    rest = text[m.end():]
    nxt = _NEXT_SECTION_RE.search(rest)
    return rest[:nxt.start()] if nxt else rest


# Any speaker line in the transcript: "... (`id`): text" — the label may carry
# extra words inside the parentheses, e.g. "Jon (as introduced, `main_hero`):"
_SPEAKER_LINE_RE = re.compile(r'\([^()]*`([^`]+)`[^()]*\)\s*:\s*(.+?)\s*$')

# AI Influence reuses the "### Mission ###" prompt for letters, but swaps this
# phrase in place of the usual "Use *asterisks for actions/surroundings*".
_LETTER_PROMPT_MARKER = "Dialogue only, no action descriptions"

_player_line_patterns = {}


def _player_line_pattern(pid):
    """
    Match one spoken line by `pid`: a "(... `id` ...)" group immediately followed
    by the colon, then the spoken text. Anything before the group (a name, an
    "[Overheard ...]" prefix) is allowed; metadata lines where other words sit
    between the group and the colon are not.
    """
    pat = _player_line_patterns.get(pid)
    if pat is None:
        pat = re.compile(r'\([^()]*`' + re.escape(pid) + r'`[^()]*\)\s*:\s*(.+?)\s*$')
        _player_line_patterns[pid] = pat
    return pat


def _looks_like_context_blob(s):
    """
    True if this text is prompt context (the '### Conversation history ###' dump
    AI Influence sends as the user message) rather than one spoken utterance.
    Guard against ever reading the whole transcript aloud.
    """
    if not s:
        return True
    if len(s) > 1200:
        return True
    if "### " in s or "conversation history" in s.lower():
        return True
    # More than one 'Speaker (`id`):' tag means it's a transcript, not a line.
    return len(re.findall(r'\(`[^`]+`\)\s*:', s)) > 1


def extract_player_line(body):
    """
    Pull the player's newest spoken line out of an AI Influence dialogue request,
    or None if this isn't a dialogue request / no line found.

    AI Influence puts the whole conversation transcript in the 'user' message
    ("### Conversation history ###" + the last N messages), so the reliable read
    is the LAST transcript line tagged with the player's hero id — not the raw
    message content, which is the entire blob.
    """
    try:
        data = json.loads(body)
    except Exception:
        return None
    msgs = data.get("messages")
    if not isinstance(msgs, list) or not msgs:
        return None

    # Only the NPC role-play request carries player dialogue.
    if not any(isinstance(m, dict) and m.get("role") == "system"
               and _DIALOGUE_PROMPT_MARKER in str(m.get("content") or "")
               for m in msgs):
        return None

    # Primary: last transcript line spoken by the player.
    #
    # The request is mostly prompt context — tens of thousands of characters of
    # world state that also mention the player. So we can't just look for the id
    # before a colon: a metadata line like
    #     Jon Snow (`main_hero`) relation: positive.
    # would parse as the player saying "positive."
    #
    # What separates a real dialogue line is that the "(...`id`)" group sits
    # IMMEDIATELY before the colon. That holds for every label AI Influence uses:
    #     Unidentified person (`main_hero`): ...
    #     Jon (as introduced, `main_hero`): ...       <- after introducing yourself
    #     Lord Jon Snow (`main_hero`): ...
    #     [Overheard nearby, ...] Unidentified person (`main_hero`): ...
    # Scope to the transcript section when the prompt has one — the rest of the
    # prompt contains relation/world-state lines in the very same shape.
    pid = _player_bind_id()
    contents = [m.get("content") for m in msgs
                if isinstance(m, dict) and isinstance(m.get("content"), str)]

    # Letters reuse this same prompt but you aren't speaking — the transcript is
    # from an earlier conversation, so voicing "your line" would replay an old one.
    if any(_LETTER_PROMPT_MARKER in c for c in contents):
        return None
    haystacks = [s for s in (_conversation_section(c) for c in contents) if s]
    if not haystacks:
        # No transcript section means there's no spoken line to recover. Never
        # fall back to scanning the rest of the prompt: relation and world-state
        # lines ("Jon Snow (`main_hero`): positive.") are shaped exactly
        # like dialogue and would be voiced.
        return None

    # Take the LAST speaker line in the transcript and require it to be yours.
    #
    # In a live turn you have just spoken and the NPC hasn't answered yet, so
    # your line is last. If someone else's line comes after yours, this isn't a
    # fresh utterance — it's history being replayed (a letter, an initiative
    # event, a re-sent prompt), and voicing it would read out an old chat.
    last_speaker = last_text = None
    for c in haystacks:
        for raw in c.splitlines():
            hit = _SPEAKER_LINE_RE.search(raw)
            if hit and hit.group(2).strip():
                last_speaker, last_text = hit.group(1), hit.group(2).strip()
    candidate = last_text if last_speaker == pid else None

    # Fallback: a 'user' message that is genuinely just one utterance.
    if not candidate:
        for m in reversed(msgs):
            if isinstance(m, dict) and m.get("role") == "user":
                raw = str(m.get("content") or "").strip()
                if not _looks_like_context_blob(raw):
                    candidate = _strip_speaker_label(raw)
                break

    if not candidate or _looks_like_context_blob(candidate):
        return None
    return candidate


def maybe_voice_player_line(body):
    """
    If this request is the player speaking, queue their line for playback so it's
    voiced while the LLM generates the reply. Deduplicated, because a group
    conversation fires one chat request per NPC with the same player line.
    """
    if not player_lines_enabled():
        return
    try:
        line = extract_player_line(body)
    except Exception as e:
        print(f"  [PLAYER] extraction error: {e}")
        return
    if not line or len(line.strip()) < PLAYER_LINE_MIN_CHARS:
        # If it WAS a dialogue request but we couldn't find the line, dump the
        # message shapes once so the extraction can be corrected.
        try:
            msgs = (json.loads(body) or {}).get("messages") or []
            if any(isinstance(m, dict) and m.get("role") == "system"
                   and _DIALOGUE_PROMPT_MARKER in str(m.get("content") or "")
                   for m in msgs):
                shapes = ", ".join(f"{m.get('role')}:{len(str(m.get('content') or ''))}c"
                                   for m in msgs if isinstance(m, dict))
                print(f"  [PLAYER] Dialogue request but no player line found "
                      f"(bind id '{_player_bind_id()}'; messages: {shapes}).")
                tail = str(msgs[-1].get("content") or "")[-400:] if msgs else ""
                print(f"  [PLAYER] last message tail: {tail}")
        except Exception:
            pass
        return
    # Belt-and-braces: never let leaked reasoning ride along on a player line.
    if STRIP_INTERNAL_THOUGHTS:
        cleaned, leaked = strip_internal_thoughts(line)
        if leaked:
            if not cleaned:
                print("  [PLAYER] Line contained unseparable reasoning — skipping.")
                return
            line = cleaned

    key = _normalize_for_match(line)[:200]
    if not key or key in _recent_player_lines:
        return                                   # already voiced this turn
    _recent_player_lines.append(key)

    global _play_seq_counter
    with _play_cond:
        _play_seq_counter += 1
        seq = _play_seq_counter
        _play_queue.append({
            "kind": "player", "seq": seq, "text": line,
            "voice_id": get_player_voice(), "speed": 1.0, "ts": time.time(),
        })
        depth = len(_play_queue)
        _play_cond.notify()
    print(f"\n--- PLAYER LINE (queued seq {seq}, depth {depth}) ---")
    print(f"  Text: {line[:120]}{'...' if len(line) > 120 else ''}")


# ============================================================
#  INTERNAL-THOUGHTS LEAK FILTER
# ============================================================
# Scaffolding the model emits when it leaks its reasoning instead of returning
# the required JSON: "FACT CHECK: STEP 1: ... STEP 6: ..." then the real line.
_THOUGHT_MARKER_RE = re.compile(r'(?i)(\bFACT\s*CHECK\b|\bSTEP\s*\d+\s*:)')
_LAST_STEP_RE      = re.compile(r'(?i).*\bSTEP\s*\d+\s*:', re.DOTALL)
_FACT_CHECK_RE     = re.compile(r'(?i)^.*?\bFACT\s*CHECK\b\s*:?\s*', re.DOTALL)

# Phrases that mark a sentence as the model planning, not the character speaking.
_REASONING_STARTS = (
    "fact check", "step ", "no technical action", "no technical actions",
    "i should ", "i must ", "i need to ", "i will respond", "i am to ",
    "i am in ", "i am lord ", "i am ser ", "we are in ", "as lord ", "as ser ",
    "my trust in", "this is a moment", "being the ", "the council has been",
    "i am calm", "i feel calm", "i should respond", "i want to convey",
)
# Signals that a sentence is real in-character speech or action.
_DIALOGUE_HINTS = (
    "your grace", "my lord", "my lady", "my king", "my queen", "my prince",
    "my princess", "ser ", "father,", "mother,", "my sweet",
)


def _looks_like_dialogue(sentence):
    """True if the sentence reads as in-character speech/action rather than planning."""
    s = (sentence or "").strip()
    if not s:
        return False
    if "*" in s:                      # an *action* — the prompt reserves these for speech
        return True
    low = s.lower()
    if any(h in low for h in _DIALOGUE_HINTS):
        return True
    return s.endswith("?") or s.endswith("!")


def _looks_like_reasoning(sentence):
    """True if the sentence is model planning/meta-analysis."""
    low = (sentence or "").strip().lower()
    if not low:
        return False
    return any(low.startswith(p) for p in _REASONING_STARTS)


def strip_internal_thoughts(text):
    """
    Remove leaked internal-thought scaffolding, returning only the spoken line.

    Handles two leak shapes:
      1. Raw JSON leaked as text — pull out the "response" field.
      2. "FACT CHECK: STEP 1: ... STEP N: <planning> <actual dialogue>" — drop
         everything through the last STEP marker, then drop the remaining leading
         planning sentences until in-character speech starts.

    Returns (cleaned_text, was_leaking). cleaned_text is "" when the dialogue
    could not be confidently separated.
    """
    if not text or not _THOUGHT_MARKER_RE.search(text):
        return text, False

    work = text.strip()

    # --- Shape 1: the whole JSON object leaked as text ---
    if work.startswith("{") or work.startswith("```"):
        body = re.sub(r'^```(?:json)?\s*|\s*```$', '', work).strip()
        try:
            obj = json.loads(body)
            if isinstance(obj, dict):
                resp = obj.get("response")
                if isinstance(resp, str) and resp.strip():
                    return resp.strip(), True
        except Exception:
            # Not parseable (often truncated) — fall back to a direct field grab.
            m = re.search(r'"response"\s*:\s*"((?:[^"\\]|\\.)*)"', body)
            if m:
                try:
                    return json.loads('"' + m.group(1) + '"').strip(), True
                except Exception:
                    pass

    # --- Shape 2: plain-text chain of thought ---
    # Cut through the LAST "STEP n:" marker if present, else past "FACT CHECK:".
    m = _LAST_STEP_RE.match(work)
    remainder = work[m.end():] if m else _FACT_CHECK_RE.sub('', work, count=1)

    # Drop leading planning sentences until the character starts speaking.
    sentences = re.split(r'(?<=[.!?])\s+', remainder.strip())
    keep_from = None
    for i, s in enumerate(sentences):
        if _looks_like_dialogue(s):
            keep_from = i
            break
        if _looks_like_reasoning(s):
            continue
        keep_from = i          # neither planning nor obviously speech — assume speech
        break

    if keep_from is None:
        return "", True        # it was reasoning all the way down
    cleaned = " ".join(sentences[keep_from:]).strip()
    if len(cleaned) < 15 or _THOUGHT_MARKER_RE.search(cleaned):
        return "", True        # nothing usable / scaffolding still present
    return cleaned, True




_voice_guard_announced = set()


# ---- Banned voices ----
# Voices you never want to hear again, from anyone. A banned voice is treated
# like the narrator's or your own: NPCs are moved off it, remaps never land on
# it, and anyone already pinned to it is permanently recast. Kept in a file so
# the tray toggle survives a restart and so it can be edited by hand.
BANNED_VOICES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "banned_voices.txt")
_banned_voices = None
_banned_voices_mtime = None


def banned_voices():
    """The set of banned voice ids. Re-reads the file whenever it changes."""
    global _banned_voices, _banned_voices_mtime
    try:
        mtime = os.path.getmtime(BANNED_VOICES_FILE)
    except OSError:
        mtime = None
    if mtime is None:                      # no file yet — nothing is banned
        if _banned_voices is None:
            _banned_voices = set()
        return _banned_voices
    if mtime != _banned_voices_mtime:
        found = set()
        try:
            with open(BANNED_VOICES_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.split("#")[0].strip()   # allow trailing comments
                    if not line:
                        continue
                    if line in VOICE_DB:
                        found.add(line)
                    else:
                        print(f"  [voice] Unknown voice id in "
                              f"{os.path.basename(BANNED_VOICES_FILE)}: {line}")
            _banned_voices = found
            _banned_voices_mtime = mtime
        except Exception as e:
            print(f"  [voice] Could not read {BANNED_VOICES_FILE}: {e}")
            if _banned_voices is None:
                _banned_voices = set()
    return _banned_voices


def _save_banned_voices(ids):
    global _banned_voices, _banned_voices_mtime
    _banned_voices = set(ids)
    try:
        with open(BANNED_VOICES_FILE, "w", encoding="utf-8") as f:
            f.write("# Voices never to be used, by anyone.\n")
            f.write("# Toggle from the tray menu, or add/remove ids by hand -\n")
            f.write("# changes apply on the next line, no restart needed.\n")
            for vid in sorted(_banned_voices,
                              key=lambda v: VOICE_DB.get(v, {}).get("name", "")):
                info = VOICE_DB.get(vid, {})
                f.write(f"{vid}  # {info.get('name')} "
                        f"({info.get('gender')}, {info.get('lang')})\n")
        _banned_voices_mtime = os.path.getmtime(BANNED_VOICES_FILE)
    except Exception as e:
        print(f"  [voice] Could not save {BANNED_VOICES_FILE}: {e}")


def set_voice_banned(vid, banned=True):
    """Ban or unban a voice, then recast anyone currently pinned to it."""
    if vid not in VOICE_DB:
        print(f"  [voice] Unknown voice id: {vid}")
        return
    current = set(banned_voices())
    if banned:
        current.add(vid)
    else:
        current.discard(vid)
    _save_banned_voices(current)
    print(f"  [voice] {VOICE_DB[vid].get('name')} is "
          f"{'BANNED' if banned else 'allowed again'}.")
    if banned:
        _recast_pins_off_banned()


def _fresh_voice_for(key, gender):
    """
    Pick an allowed voice for one character, keyed on the CHARACTER rather than
    the voice they are leaving. Only safe where the result is persisted (the
    pin file) — elsewhere, keying on the source voice is what keeps a voice from
    shifting mid-line.
    """
    reserved = _reserved_voices()
    pool = [v for v in (ENGLISH_MALE_VOICES
                        if (gender or "male").lower() == "male"
                        else ENGLISH_FEMALE_VOICES)
            if v not in reserved]
    if not pool:
        return None
    return pool[_stable_index(key, len(pool))]


def _recast_pins_off_banned():
    """
    Move every pinned character off a now-banned voice and write the new voice
    back. Persisting it matters: a ban is permanent, so the replacement should be
    settled once rather than recomputed - and possibly shifted - later.
    """
    pins = _load_npc_voice_pins()
    bad = banned_voices()
    moved = 0
    for string_id, entry in pins.items():
        stored = entry.get("voice")
        if stored not in bad:
            continue
        gender = (entry.get("gender")
                  or VOICE_DB.get(stored, {}).get("gender") or "male")
        replacement = _fresh_voice_for(string_id, gender)
        if not replacement or replacement == stored:
            continue                       # nothing left to move to
        entry["voice"] = replacement
        entry["recast_from"] = stored
        entry["at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        moved += 1
        print(f"  [voice] Recast {entry.get('name') or string_id}: "
              f"{VOICE_DB.get(stored, {}).get('name')} -> "
              f"{VOICE_DB.get(replacement, {}).get('name')}")
    if moved:
        _save_npc_voice_pins()
        print(f"  [voice] Recast {moved} character(s) off banned voices.")


def _reserved_voices():
    """
    Voice ids NPCs must not use: yours, the narrator's, and any you've banned.
    """
    reserved = set(banned_voices())
    if AVOID_PLAYER_VOICE_FOR_NPCS and player_lines_enabled():
        reserved.add(get_player_voice())
    if AVOID_NARRATOR_VOICE_FOR_NPCS:
        reserved.add(NARRATOR_VOICE)
    return reserved


# Accent phrasing per Player2 voice language. Keep these short and unchanging —
# the point is not the wording, it's that the string never varies.
# Short on purpose. The long form ("Speak in a neutral American English accent.
# Keep the same voice, accent, age and pitch for the whole line; do not switch to
# any other accent.") appeared to cost 26-71% more generation time in a small
# sample, and length is not what makes an anchor work — being IDENTICAL on every
# call is. Naming the accent is the part that has to survive.
_ACCENT_PHRASES = {
    "american_english": "Neutral American English accent.",
    "british_english":  "British English accent.",
}
_accent_instructions_cache = {}


_narrator_instruction_cache = {}


def narrator_instructions():
    """
    The narrator's instruction, identical on every call.

    The accent sentence is built from the narrator voice's own language: telling
    an American voice to sound British (or the reverse) is exactly the sort of
    pull that makes Player2 wander into a dialect, which is what we're trying to
    stop. Cached per voice so the text never varies between calls.
    """
    if not NARRATOR_INSTRUCTIONS:
        return None
    voice = NARRATOR_VOICE
    if voice not in _narrator_instruction_cache:
        if NARRATOR_ACCENT:
            accent = NARRATOR_ACCENT
        else:
            lang = VOICE_DB.get(voice, {}).get("lang", "")
            # One accent, named positively. Never a list of accents to avoid:
            # see the note above NARRATOR_INSTRUCTIONS.
            accent = {
                "american_english": "Speak in General American English, the "
                                    "standard accent of the American Midwest, "
                                    "as a national news anchor speaks it.",
                "british_english":  "Speak in standard British English, as a "
                                    "national broadcaster speaks it.",
            }.get(lang, "Speak in standard English, as a national broadcaster "
                        "speaks it.")
        _narrator_instruction_cache[voice] = NARRATOR_INSTRUCTIONS.format(
            accent=accent)
    return _narrator_instruction_cache[voice]


def voice_accent_instructions(voice_id):
    """
    A CONSTANT instruction anchoring one voice's accent and vocal identity.

    Player2 free-runs when a call carries no conditioning, which is why the same
    lord could sound American on one line and Irish on the next — NPC lines went
    out bare while the narrator, which always sends a fixed instruction, held its
    accent. The exact wording matters far less than it never changing, so it's
    built once per voice and cached: every call for that voice sends byte-
    identical text.
    """
    if not PIN_VOICE_ACCENT or not voice_id:
        return None
    if voice_id not in _accent_instructions_cache:
        info = VOICE_DB.get(voice_id, {})
        _accent_instructions_cache[voice_id] = _ACCENT_PHRASES.get(
            info.get("lang", ""), "Consistent English accent.")
    return _accent_instructions_cache[voice_id]


# ---- Character -> voice pins ----
# AI Influence hands us a different voice id for the same character from one turn
# to the next, so the only stable key is the character themselves. Persisted so a
# lord keeps his voice across restarts and saves.
NPC_VOICES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "npc_voices.json")
_npc_voice_pins = None


def _load_npc_voice_pins():
    """Read the pins once, then serve them from memory."""
    global _npc_voice_pins
    if _npc_voice_pins is None:
        _npc_voice_pins = {}
        try:
            if os.path.exists(NPC_VOICES_FILE):
                with open(NPC_VOICES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    _npc_voice_pins = {k: v for k, v in data.items()
                                       if isinstance(v, dict)}
                print(f"  [voice] Loaded {len(_npc_voice_pins)} pinned character voices.")
        except Exception as e:
            print(f"  [voice] Could not read {NPC_VOICES_FILE}: {e}")
            _npc_voice_pins = {}
    return _npc_voice_pins


def _save_npc_voice_pins():
    try:
        with open(NPC_VOICES_FILE, "w", encoding="utf-8") as f:
            json.dump(_load_npc_voice_pins(), f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"  [voice] Could not save {NPC_VOICES_FILE}: {e}")


def pinned_character_instructions(string_id):
    """
    Optional per-character delivery note, set by hand as "instructions" on a pin
    in npc_voices.json. Replaces that character's per-voice accent anchor, so it
    must stay constant text for the same reason the anchor does.
    """
    entry = _load_npc_voice_pins().get(string_id) if string_id else None
    text = entry.get("instructions") if entry else None
    return text.strip() if isinstance(text, str) and text.strip() else None


def pin_npc_voice(string_id, name, resolved_voice, source_voice, npc_gender):
    """
    Keep a character on the voice they were first heard with.

    Only called from the validated path — the NPC was recovered from their JSON
    and their text matched the line the mod asked for — so a mis-identified line
    can never recast anyone. The pin is still run through the reserved-voice
    guard on the way out, so changing your own voice later still pushes NPCs off
    it rather than being frozen by an old pin.
    """
    if not PIN_NPC_VOICES or not string_id or not resolved_voice:
        return resolved_voice

    pins = _load_npc_voice_pins()
    entry = pins.get(string_id)
    if entry and entry.get("voice") in VOICE_DB:
        # A ban is permanent, so settle the replacement once and write it back
        # rather than recomputing it on every line. Your voice and the
        # narrator's are live, reversible choices, so those stay unpersisted.
        if entry["voice"] in banned_voices():
            _recast_pins_off_banned()
        pinned = _avoid_reserved_voice(entry["voice"], npc_gender)
        if pinned != resolved_voice:
            print(f"  [voice] Pin: {name or string_id} stays "
                  f"{VOICE_DB.get(pinned, {}).get('name')} — the mod asked for "
                  f"{VOICE_DB.get(resolved_voice, {}).get('name')} this turn")
        return pinned

    resolved_voice = _avoid_reserved_voice(resolved_voice, npc_gender)
    pins[string_id] = {"voice": resolved_voice, "name": name or "",
                       "source": source_voice or "", "gender": npc_gender or "",
                       "at": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save_npc_voice_pins()
    print(f"  [voice] Pinned {name or string_id} -> "
          f"{VOICE_DB.get(resolved_voice, {}).get('name')}")
    return resolved_voice


def forget_npc_voice_pins():
    """Drop every character pin. They re-pin from whatever they next speak with."""
    global _npc_voice_pins
    n = len(_load_npc_voice_pins())
    _npc_voice_pins = {}
    _save_npc_voice_pins()
    print(f"  [voice] Forgot {n} pinned character voices — "
          f"each will re-pin on their next line.")


def _avoid_reserved_voice(voice_id, npc_gender):
    """
    If an NPC landed on a reserved voice (yours / the narrator's), move it to a
    stand-in of the same gender.

    Keyed on the SOURCE voice id — the same reasoning as resolve_voice: it's
    identical for every chunk of a line and every session, so a mis-identified
    continuation can't shift the voice mid-line. Every NPC sharing that source
    voice moves together, which is fine — they already sounded identical.
    """
    reserved = _reserved_voices()
    if not voice_id or voice_id not in reserved:
        return voice_id

    info = VOICE_DB.get(voice_id, {})
    gender = (info.get("gender") or npc_gender or "male").lower()
    pool = [v for v in (ENGLISH_MALE_VOICES if gender == "male" else ENGLISH_FEMALE_VOICES)
            if v not in reserved]
    if not pool:                       # nothing left to move to — keep as-is
        return voice_id
    # Include the reserved set in the hash key so the pick stays deterministic
    # for a given player voice, and recomputes cleanly if you change it.
    stand_in = pool[_stable_index(voice_id + "|" + "|".join(sorted(reserved)), len(pool))]
    # Announce each remap once, not on every line.
    announce_key = (voice_id, stand_in)
    if announce_key not in _voice_guard_announced:
        _voice_guard_announced.add(announce_key)
        if voice_id in banned_voices():
            why = "a banned voice"
        elif voice_id == (get_player_voice() if player_lines_enabled() else None):
            why = "your voice"
        else:
            why = "the narrator's voice"
        print(f"  Voice guard: NPC would use {info.get('name')} ({why}) -> "
              f"{VOICE_DB.get(stand_in, {}).get('name')}")
    return stand_in


def resolve_voice(voice_id, npc_gender, npc_string_id):
    """
    If the assigned voice UUID is non-English (e.g. Mandarin, Hindi), replace it
    with a consistent English voice. If it's already English, return it unchanged.

    The replacement is keyed on the SOURCE voice_id (and the source voice's own
    gender), NOT on npc_string_id. The source voice is identical for every chunk
    of a character's line and every session, whereas npc_string_id is guessed
    per request by find_npc and can differ for a short continuation chunk after a
    narrator interruption — which is what used to make the voice change mid-line.
    Hashing is done with hashlib so the choice is also stable across restarts.
    """
    voice_info = VOICE_DB.get(voice_id, {})
    lang = voice_info.get("lang", "american_english")

    # Already English → use as-is (no remap, so nothing can drift), unless it
    # collides with a reserved voice (yours / the narrator's).
    if lang in ("american_english", "british_english"):
        return _avoid_reserved_voice(voice_id, npc_gender)

    # Non-English → map to a stable English voice keyed on the source voice.
    # The collision check runs on the result, not the cache, so changing your
    # voice from the tray takes effect immediately.
    if voice_id in _voice_remap_cache:
        return _avoid_reserved_voice(_voice_remap_cache[voice_id], npc_gender)

    # Prefer the source voice's own gender; fall back to the NPC's gender.
    gender = (voice_info.get("gender") or npc_gender or "male").lower()
    pool = ENGLISH_MALE_VOICES if gender == "male" else ENGLISH_FEMALE_VOICES
    new_voice = pool[_stable_index(voice_id, len(pool))]
    new_info = VOICE_DB.get(new_voice, {})
    print(f"  Auto-fix: {voice_info.get('name')} ({lang}) → {new_info.get('name')} (english {gender})")

    _voice_remap_cache[voice_id] = new_voice
    if npc_string_id:
        _npc_voice_assignment[npc_string_id] = new_voice  # keep legacy cache warm
    return _avoid_reserved_voice(new_voice, npc_gender)


def _text_score(candidate_clean, received_clean):
    """Return a similarity score between two cleaned strings."""
    if not candidate_clean:
        return 0
    if received_clean == candidate_clean:
        return 100000  # exact
    if received_clean in candidate_clean:
        return len(received_clean) * 2
    if candidate_clean in received_clean:
        return len(candidate_clean)
    recv_words = set(received_clean.split())
    cand_words = set(candidate_clean.split())
    return len(recv_words & cand_words)


def _has_unseen_npc_entry(filepath):
    """
    Returns True if the NPC file has NEW entries that proxy hasn't seen yet
    (i.e. entries beyond _npc_history_seen pointer).
    This is the most reliable way to find which NPC is currently speaking —
    AIInfluence writes the file FIRST, ChatSync mirror arrives ~0.65s later.
    """
    seen_len = _npc_history_seen.get(filepath, 0)
    try:
        with open_shared(filepath) as f:
            data = json.load(f)
        history = data.get("ConversationHistory", [])
        own_id = data.get("StringId", "")
        # Look for new lines spoken BY THIS NPC (its own StringId) beyond our pointer
        for i in range(seen_len, len(history)):
            speaker_id, _ = _entry_speaker_id(history[i])
            if speaker_id and speaker_id == own_id:
                return True, len(history), data
        return False, len(history), data
    except Exception:
        return False, seen_len, None


def find_speaker_by_text(received_text, timeout):
    """
    Identify who is speaking from WHAT they said, not from the voice id.

    AI Influence hands the same voice id to many characters, so matching on it
    is a guess. In the 2026-09-14 Lannister scene that guess named Ser Osbert
    Tempest for a line Joffrey spoke and Mina Tyrell for one of Cersei's:
    their files had never been read that session, so every old line in them
    looked "unseen". The wrong file never contained the line, so the actions
    were lost too.

    The line itself is unambiguous. AI Influence writes it, *actions* included,
    into the speaker's file ("I (Name, `id`): ...") and into every listener's
    ("Name (`id`): ..."), each tagged with the speaker's StringId. So: search the
    last few lines of recently written files for an entry matching the mod's
    text, take the speaker id from it, and load that character's own file.
    Polls until `timeout`, since the files land around the time of the request.

    Returns (speaker_data, speaker_path, full_text_with_actions), or
    (None, None, None) when no character — or more than one — said this.
    """
    if not (received_text or "").strip():
        return None, None, None
    folder = get_npc_folder()
    if not folder or not os.path.isdir(folder):
        return None, None, None

    deadline = time.time() + max(0.0, timeout)
    parsed = {}          # path -> (mtime, data), so unchanged files are read once
    attempt = 0
    while True:
        attempt += 1
        now = time.time()
        owners = {}      # StringId -> (path, data)
        found = {}       # speaker id -> (text, came from the speaker's own file)
        try:
            names = os.listdir(folder)
        except OSError:
            names = []
        for filename in names:
            if not filename.endswith(".json"):
                continue
            path = os.path.join(folder, filename)
            try:
                mtime = os.path.getmtime(path)
                if now - mtime > SPEAKER_SEARCH_RECENT_SECONDS:
                    continue
                if parsed.get(path, (None,))[0] != mtime:
                    with open_shared(path) as f:
                        parsed[path] = (mtime, json.load(f))
                data = parsed[path][1]
            except Exception:
                continue          # mid-write or unreadable — next poll
            if not isinstance(data, dict) or not data.get("StringId"):
                continue
            own_id = data["StringId"]
            owners[own_id] = (path, data)
            player_id = _player_id(data)
            for entry in (data.get("ConversationHistory") or [])[-SPEAKER_SEARCH_LAST_ENTRIES:]:
                speaker_id, body = _entry_speaker_id(entry)
                if not speaker_id or not body or speaker_id == player_id:
                    continue
                if _is_error_text(body) or not _texts_match(body, received_text):
                    continue
                own = speaker_id == own_id
                if speaker_id not in found or (own and not found[speaker_id][1]):
                    found[speaker_id] = (body, own)

        if len(found) > 1:
            print(f"  Speaker by text: {len(found)} characters said this line — "
                  f"falling back to voice matching.")
            return None, None, None
        if len(found) == 1:
            speaker_id, (body, _) = next(iter(found.items()))
            owner = owners.get(speaker_id)
            if owner is None:
                # Their own file is older than the search window; find it anyway.
                for path, data in load_all_npc_data().items():
                    if data.get("StringId") == speaker_id:
                        owner = (path, data)
                        break
            if owner is not None:
                path, data = owner
                _npc_history_seen[path] = len(data.get("ConversationHistory") or [])
                print(f"  Speaker by text: {data.get('Name')} (poll #{attempt}) ✓")
                return data, path, body
        if time.time() >= deadline:
            print(f"  Speaker by text: no recent save file has this line "
                  f"after {timeout:.1f}s — falling back to voice matching.")
            return None, None, None
        time.sleep(FILE_POLL_INTERVAL)


def find_npc(received_text, voice_id):
    """
    Find the correct NPC JSON for this TTS request.

    Strategy:
      1. Find all NPCs sharing this voice UUID
      2. If only one match → return immediately (fast path)
      3. If multiple share the UUID:
         a. Check which file has UNSEEN new NPC entries (most reliable)
         b. Fall back to text similarity scoring
         c. Fall back to most recently modified file (mtime)
      4. If UUID not found → search all NPCs by text
    """
    npc_map = load_all_npc_data()
    received_clean = received_text.strip().lower()

    uuid_matches = []
    if voice_id:
        for filepath, data in npc_map.items():
            if data.get("AssignedTTSVoice") == voice_id:
                uuid_matches.append((filepath, data))

    print(f"  UUID '{voice_id}': {len(uuid_matches)} NPC(s) found")

    if len(uuid_matches) == 1:
        filepath, data = uuid_matches[0]
        print(f"  Match: {data.get('Name')} (unique UUID)")
        return data, filepath

    search_pool = uuid_matches if uuid_matches else list(npc_map.items())
    if len(uuid_matches) > 1:
        print(f"  Multiple NPCs share this UUID — disambiguating...")
    else:
        print(f"  UUID not found — searching by text across all NPCs...")

    # ----------------------------------------------------------------
    # STEP A: unseen-entry detection (only for uuid_matches candidates)
    # AIInfluence writes the NPC file BEFORE TTS request fires.
    # ChatSync mirror copies that entry to other NPCs ~0.65s LATER.
    # So: whichever candidate has a new unseen NPC entry = the speaker.
    # ----------------------------------------------------------------
    if uuid_matches:
        unseen_candidates = []
        for filepath, data in uuid_matches:
            has_new, hist_len, fresh_data = _has_unseen_npc_entry(filepath)
            if has_new:
                unseen_candidates.append((filepath, fresh_data or data, hist_len))
                print(f"  Unseen entry found in: {data.get('Name')} ({filepath})")

        if len(unseen_candidates) == 1:
            filepath, data, _ = unseen_candidates[0]
            print(f"  Match: {data.get('Name')} (sole unseen entry) ✓")
            return data, filepath

        if len(unseen_candidates) > 1:
            # Multiple have new entries — pick one with best text score from fresh data
            print(f"  Multiple files have unseen entries — scoring by text...")
            best_path, best_data, best_score = None, None, 0
            for filepath, data, _ in unseen_candidates:
                history = data.get("ConversationHistory", [])
                own_id = data.get("StringId", "")
                seen_len = _npc_history_seen.get(filepath, 0)
                score = 0
                for entry in reversed(history[seen_len:]):
                    speaker_id, body = _entry_speaker_id(entry)
                    if not speaker_id or speaker_id != own_id:
                        continue
                    entry_clean = strip_actions(body).strip().lower()
                    s = _text_score(entry_clean, received_clean)
                    if s >= 100000:
                        print(f"  Match: {data.get('Name')} (exact unseen entry)")
                        return data, filepath
                    score = max(score, s)
                if score > best_score:
                    best_score = score
                    best_data = data
                    best_path = filepath
            if best_path:
                print(f"  Match: {best_data.get('Name')} (best unseen text score={best_score})")
                return best_data, best_path

    # ----------------------------------------------------------------
    # STEP B: text similarity across all candidates
    # (handles edge case where seen pointer is already advanced)
    # ----------------------------------------------------------------
    best_match = None
    best_path = None
    best_score = 0

    for filepath, data in search_pool:
        score = 0

        # Check LastTTSPlayedText
        last_tts = data.get("LastTTSPlayedText", "")
        last_tts_clean = strip_actions(last_tts).strip().lower()
        s1 = _text_score(last_tts_clean, received_clean)
        if s1 >= 100000:
            print(f"  Match: {data.get('Name')} (exact LastTTSPlayedText)")
            return data, filepath
        score = max(score, s1)

        # Check recent ConversationHistory NPC entries
        history = data.get("ConversationHistory", [])
        own_id = data.get("StringId", "")
        for entry in reversed(history[-20:]):
            speaker_id, body = _entry_speaker_id(entry)
            if not speaker_id or speaker_id != own_id:
                continue
            entry_clean = strip_actions(body).strip().lower()
            s2 = _text_score(entry_clean, received_clean)
            if s2 >= 100000:
                print(f"  Match: {data.get('Name')} (exact ConversationHistory)")
                return data, filepath
            score = max(score, s2)

        if score > best_score:
            best_score = score
            best_match = data
            best_path = filepath

    if best_match and best_score > 0:
        print(f"  Match: {best_match.get('Name')} (text score={best_score})")
        return best_match, best_path

    # ----------------------------------------------------------------
    # STEP C: mtime fallback — last resort
    # AIInfluence updates the file just before TTS fires, so newest = speaker.
    # Less reliable when mirror runs fast, but better than random.
    # ----------------------------------------------------------------
    if uuid_matches:
        newest_path, newest_data = max(
            ((fp, d) for fp, d in uuid_matches),
            key=lambda x: os.path.getmtime(x[0])
        )
        print(f"  Match: {newest_data.get('Name')} (mtime fallback)")
        return newest_data, newest_path

    print(f"  No NPC match found")
    return None, None


def _find_matching_entry(history, received_clean):
    """
    Scan ConversationHistory for an NPC entry whose text (actions stripped)
    best matches received_clean. Returns full entry text or None.
    """
    best_entry = None
    best_score = -1

    for entry in reversed(history):
        speaker_id, full = _entry_speaker_id(entry)
        if not speaker_id or speaker_id == "main_hero":
            continue
        clean = strip_actions(full).strip().lower()
        if not clean:
            continue

        # Exact match — best possible
        if received_clean == clean:
            return full

        # Word overlap score
        recv_words = set(received_clean.split())
        hist_words = set(clean.split())
        overlap = len(recv_words & hist_words)
        if overlap > best_score:
            best_score = overlap
            best_entry = full

    if best_entry and best_score > 3:
        return best_entry
    return None


def wait_for_new_entry(npc_path, npc_gender, npc_string_id, received_text="", timeout=None):
    """
    Poll the NPC JSON file until a NEW line spoken by THIS NPC appears in
    ConversationHistory (one that wasn't there last time we checked).

    If received_text is given (the line the mod wants spoken right now), we
    prefer a new entry that MATCHES it and return as soon as we find one. If no
    matching entry appears within MATCH_POLL_TIMEOUT, we return ("" text) to
    signal "nothing valid recovered" — the caller then narrates received_text
    directly. This stops initiative/seek-you-out events (where the lord's JSON
    isn't freshly written) from narrating a stale previous conversation.

    Returns: (updated_npc_data, full_text_with_actions)  — full_text may be ""
    when received_text was provided but no matching entry was found.
    """
    have_target = bool((received_text or "").strip())
    if timeout is None:
        timeout = MATCH_POLL_TIMEOUT if have_target else FILE_POLL_TIMEOUT
    deadline = time.time() + timeout
    attempt  = 0
    seen_len = _npc_history_seen.get(npc_path, 0)
    latest_new = None  # most recent new own-NPC line seen, matching or not
    print(f"  Polling for new entry (seen so far: {seen_len}; "
          f"{'validating against mod text' if have_target else 'no mod text to validate'})...")

    while time.time() < deadline:
        attempt += 1
        try:
            with open_shared(npc_path) as f:
                data = json.load(f)
        except Exception as e:
            print(f"  [poll #{attempt}] Read error: {e}")
            time.sleep(FILE_POLL_INTERVAL)
            continue

        history = data.get("ConversationHistory", [])
        player_id = _player_id(data)

        # Collect new lines (index >= seen_len) spoken BY THIS NPC.
        # Every line is tagged with the speaker's id in backticks; the NPC's own
        # turns are first person ("I (...)" in 5.0.3, "Я (...)" before). Matching
        # on the NPC's StringId means the player's turns are never picked up here.
        # We also skip AI Influence's "I am unable to respond" LLM-failure lines,
        # which 5.0.3 stores like any other NPC line.
        new_npc_entries = []
        for i, entry in enumerate(history):
            if i < seen_len:
                continue
            speaker_id, body = _entry_speaker_id(entry)
            if not speaker_id:
                continue
            if speaker_id == player_id:
                continue  # explicitly skip the player's turns
            if npc_string_id and speaker_id != npc_string_id:
                continue  # skip overheard third-party NPCs; we want THIS npc only
            if _is_error_text(body):
                continue  # skip LLM-failure fallback lines — never narrate these
            new_npc_entries.append((i, body))

        # When we have the mod's line to validate against, search the WHOLE
        # history rather than only entries past the "seen" pointer.
        #
        # AI Influence rewrites ConversationHistory as it goes — old turns are
        # compacted into "Your last conversation was N days ago." summaries and
        # some lines are stored without the `id` tag. The entry count can stay
        # flat while new lines arrive, which makes an index-based pointer say
        # "nothing new" and costs us the *action* asterisks. Matching on the text
        # itself can't pick a stale line, because it has to match the line the
        # mod is asking for right now.
        if have_target:
            for idx in range(len(history) - 1, -1, -1):
                entry = history[idx]
                speaker_id, body = _entry_speaker_id(entry)
                if body is None:
                    continue
                if speaker_id == player_id:
                    continue                     # never the player's turn
                if speaker_id and npc_string_id and speaker_id != npc_string_id:
                    continue                     # a third party we overheard
                if _is_error_text(body):
                    continue
                if _texts_match(body, received_text):
                    _npc_history_seen[npc_path] = len(history)
                    tagged = "" if speaker_id else " (untagged entry)"
                    print(f"  [poll #{attempt}] Matched mod text at index {idx}{tagged} ✓")
                    return data, body

        if new_npc_entries:
            # The ConversationHistory line is the source of truth: in 5.0.3 it
            # keeps the *action* asterisks, whereas LastAIResponseSummary strips
            # them and can be stale. So we return the history body verbatim.
            if have_target:
                # Remember the newest new line in case nothing ever matches.
                latest_new = (data, new_npc_entries[-1][1], len(history))
            else:
                last_idx, body = new_npc_entries[-1]
                _npc_history_seen[npc_path] = len(history)
                print(f"  [poll #{attempt}] New NPC entry at index {last_idx} ✓")
                return data, body

        print(f"  [poll #{attempt}] Waiting... (file has {len(history)} entries, need > {seen_len})")
        time.sleep(FILE_POLL_INTERVAL)

    # --- Timed out ---
    if have_target:
        # We were validating and never found a line matching the mod's text.
        # This is the initiative/stale case: tell the caller to use received_text.
        if latest_new:
            _npc_history_seen[npc_path] = latest_new[2]
        print(f"  [poll] Timeout ({timeout}s) — no entry matched the mod's current line; "
              f"caller will narrate the mod text directly.")
        try:
            with open_shared(npc_path) as f:
                return json.load(f), ""
        except Exception:
            return (latest_new[0] if latest_new else None), ""

    # No mod text to validate against — fall back to the latest own line.
    print(f"  [poll] Timeout ({timeout}s) — falling back to latest history entry")
    try:
        with open_shared(npc_path) as f:
            data = json.load(f)
        history = data.get("ConversationHistory", [])
        _npc_history_seen[npc_path] = len(history)
        player_id = _player_id(data)
        for entry in reversed(history):
            speaker_id, body = _entry_speaker_id(entry)
            if not speaker_id or speaker_id == player_id:
                continue
            if npc_string_id and speaker_id != npc_string_id:
                continue
            if _is_error_text(body):
                continue  # never fall back onto an LLM-failure line
            return data, body  # keeps *action* asterisks
        # Nothing usable in history (LastTTSPlayedText is unreliable in 5.0.3 —
        # often empty — so we don't lean on it). Signal "no text recovered".
        return data, ""
    except Exception as e:
        print(f"  [poll] Fallback read error: {e}")
        return None, ""



# ============================================================
#  TTS CONTENT FILTER BYPASS
# ============================================================

_WORD_REPLACEMENTS = [
    # Phonetic respellings that ACTUALLY transform the word (self-mapping
    # no-ops and dead group-pattern entries were removed). Applied to every
    # TTS segment via sanitize_for_tts() with re.IGNORECASE.

    # --- Names the TTS gets wrong ---
    # These used to live in Player2's Global prompt, where they were billed on
    # every request and then thrown away: that prompt reaches the LANGUAGE model,
    # which turns it into per-turn voice instructions, and those are exactly what
    # we stopped forwarding. Here they reach the TTS for every voice instead.

    # --- Westeros pronunciation (added 2026-11-16) ---
    # Spoken-only respellings: these rewrite the text handed to the TTS, never
    # the subtitles or the chat log. Kept here rather than in any LLM prompt for
    # the reason recorded above - the language model writes words, it does not
    # say them, and prompt-side pronunciation notes were billed and discarded.

    # --- Westeros: people ---
    (r'\bMelisandre\b'       , 'Mellisandray'),
    (r'\bMissandei\b'        , 'Missanday'),
    (r'\bMargaery\b'         , 'Marjeree'),
    (r'\bDaenerys\b'         , 'Duhnairiss'),
    (r'\bMyrcella\b'         , 'Mersella'),
    (r'\bCatelyn\b'          , 'Catlin'),
    (r'\bBaelish\b'          , 'Baylish'),
    (r'\bBrienne\b'          , 'Bree Enn'),
    (r'\bRhaegar\b'          , 'Raygar'),
    (r'\bViserys\b'          , 'Visseriss'),
    (r'\bIllyrio\b'          , 'Illeerio'),
    (r'\bShireen\b'          , 'Shyreen'),
    (r'\bYgritte\b'          , 'Igrit'),
    (r'\bNymeria\b'          , 'Nimeeria'),
    (r'\bAlliser\b'          , 'Alisser'),
    (r'\bCersei\b'           , 'Sursay'),
    (r'\bTyrion\b'           , 'Teerion'),
    (r'\bEddard\b'           , 'Edard'),
    (r'\bQyburn\b'           , 'Kwyburn'),
    (r'\bOberyn\b'           , 'Oberin'),
    (r'\bSelyse\b'           , 'Selleese'),
    (r'\bEdmure\b'           , 'Edmyoor'),
    (r'\bJaime\b'            , 'Jaymee'),
    (r'\bTywin\b'            , 'Tiewin'),
    (r'\bPetyr\b'            , 'Peter'),
    (r'\bTheon\b'            , 'Theeon'),
    (r'\bVarys\b'            , 'Vairiss'),
    (r'\bAegon\b'            , 'Aygon'),
    (r'\bAerys\b'            , 'Airiss'),
    (r'\bBeric\b'            , 'Berrik'),
    (r'\bSyrio\b'            , 'Seerio'),
    (r'\bDavos\b'            , 'Dahvos'),
    (r'\bMance\b'            , 'Mants'),
    (r'\bArya\b'             , 'Aryuh'),
    (r'\bJeor\b'             , 'Jore'),

    # --- Westeros: houses ---
    (r'\bTargaryens\b'       , 'Targairyens'),
    (r'\bBaratheons\b'       , 'Baratheeons'),
    (r'\bDondarrion\b'       , 'Dondairion'),
    (r'\bTargaryen\b'        , 'Targairyen'),
    (r'\bBaratheon\b'        , 'Baratheeon'),
    (r'\bTyrells\b'          , 'Tirells'),
    (r'\bClegane\b'          , 'Clegayn'),
    (r'\bArryns\b'           , 'Airins'),
    (r'\bTyrell\b'           , 'Tirell'),
    (r'\bArryn\b'            , 'Airin'),

    # --- Westeros: titles and words ---
    (r'\bmaesters\b'         , 'maysters'),
    (r'\bkhaleesi\b'         , 'kahleesee'),
    (r'\bkhalasar\b'         , 'kahlasar'),
    (r'\bValyrian\b'         , 'Vuhleerian'),
    (r'\bDothraki\b'         , 'Dothrakee'),
    (r'\bmaester\b'          , 'mayster'),
    (r'\bsers\b'             , 'sirs'),
    (r'\bkhal\b'             , 'kahl'),
    (r'\bser\b'              , 'sir'),

    # --- Westeros: places ---
    (r'\bBraavosi\b'         , 'Brahvosee'),
    (r'\bQartheen\b'         , 'Kartheen'),
    (r'\bBraavos\b'          , 'Brahvos'),
    (r'\bMeereen\b'          , 'Mereen'),
    (r'\bYunkai\b'           , 'Yoonkye'),
    (r'\bAsshai\b'           , 'Asheye'),
    (r'\bMyrish\b'           , 'Meerish'),
    (r'\bQarth\b'            , 'Karth'),
    (r'\bQohor\b'            , 'Kohor'),
    (r'\bEyrie\b'            , 'Eyeree'),
    (r'\bMyr\b'              , 'Meer'),
    (r'\bLys\b'              , 'Leess'),
    (r'\bfuck\b'          , 'fuhk'),
    (r'\bfucking\b'       , 'fuhking'),
    (r'\bfucked\b'        , 'fuhkd'),
    (r'\bfucks\b'         , 'fuhks'),
    (r'\bfucker\b'        , 'fuhker'),
    (r'\bfuckers\b'       , 'fuhkers'),
    (r'\bfuckin\b'        , 'fuhkin'),
    (r'\bfuckn\b'         , 'fuhkn'),
    (r'\bmotherfucker\b'  , 'muhthafuhker'),
    (r'\bmotherfucking\b' , 'muhthafuhking'),
    (r'\bmotherfuckers\b' , 'muhthafuhkers'),
    (r'\bmotherfuckin\b'  , 'muhthafuhkin'),
    (r'\bunfuck\b'        , 'unfuhk'),
    (r'\bunfucked\b'      , 'unfuhkd'),
    (r'\bfuckery\b'       , 'fuhkery'),
    (r'\bfuckup\b'        , 'fuhkup'),
    (r'\bfuck-ups\b'      , 'fuhk-ups'),
    (r'\bfucktard\b'      , 'fuhktard'),
    (r'\bfuckwad\b'       , 'fuhkwad'),
    (r'\bfuckwit\b'       , 'fuhkwit'),
    (r'\bfuckface\b'      , 'fuhkface'),
    (r'\bfuckhead\b'      , 'fuhkhed'),
    (r'\bfuckhole\b'      , 'fuhkhol'),
    (r'\bfuckstick\b'     , 'fuhkstik'),
    (r'\bfucktrumpet\b'   , 'fuhktrumpet'),
    (r'\bwhat the fuck\b' , 'wut the fuhk'),
    (r'\bthe fuck\b'      , 'the fuhk'),
    (r'\bto fuck\b'       , 'to fuhk'),
    (r'\bshit\b'          , 'sheit'),
    (r'\bshits\b'         , 'sheits'),
    (r'\bshitting\b'      , 'sheitin'),
    (r'\bshitted\b'       , 'sheited'),
    (r'\bshitty\b'        , 'sheity'),
    (r'\bbullshit\b'      , 'bullsheit'),
    (r'\bhorseshit\b'     , 'horsesheit'),
    (r'\bdogshit\b'       , 'dogsheit'),
    (r'\bcrap\b'          , 'krap'),
    (r'\bcrappy\b'        , 'krapy'),
    (r'\bpiece of shit\b' , 'pees of sheit'),
    (r'\bshithole\b'      , 'sheithol'),
    (r'\bshithead\b'      , 'sheithed'),
    (r'\bshitface\b'      , 'sheitface'),
    (r'\bshitload\b'      , 'sheitlod'),
    (r'\bshitstorm\b'     , 'sheitstorm'),
    (r'\bshitfaced\b'     , 'sheitfaced'),
    (r'\bshitlist\b'      , 'sheitlist'),
    (r'\bshitshow\b'      , 'sheitshow'),
    (r'\bshitton\b'       , 'sheiton'),
    (r'\boh shit\b'       , 'oh sheit'),
    (r'\bholy shit\b'     , 'holy sheit'),
    (r'\bcunt\b'          , 'kuhnt'),
    (r'\bcunts\b'         , 'kuhnts'),
    (r'\bcunting\b'       , 'kuhnting'),
    (r'\bcuntish\b'       , 'kuhntish'),
    (r'\bcuntface\b'      , 'kuhntface'),
    (r'\bcuntrag\b'       , 'kuhntrag'),
    (r'\bcuntstruck\b'    , 'kuhntstruck'),
    (r'\bcock\b'          , 'kok'),
    (r'\bcocks\b'         , 'koks'),
    (r'\bcocked\b'        , 'kokt'),
    (r'\bcocking\b'       , 'kokking'),
    (r'\bcocksucker\b'    , 'koksuhker'),
    (r'\bcocksucking\b'   , 'koksuhkin'),
    (r'\bcocksuckers\b'   , 'koksuhkers'),
    (r'\bcockhead\b'      , 'kokhed'),
    (r'\bcockhole\b'      , 'kokhol'),
    (r'\bcockwaffle\b'    , 'kokwoffl'),
    (r'\bcockbite\b'      , 'kokbait'),
    (r'\bcockbreath\b'    , 'kokbreth'),
    (r'\bcockmongler\b'   , 'kokmongler'),
    (r'\bcockmaster\b'    , 'kokmaster'),
    (r'\bcockknocker\b'   , 'koknoker'),
    (r'\bcocksplat\b'     , 'koksplat'),
    (r'\bcocktease\b'     , 'kokteez'),
    (r'\bcockteaser\b'    , 'koktezer'),
    (r'\bdick\b'          , 'dik'),
    (r'\bdicks\b'         , 'diks'),
    (r'\bdicked\b'        , 'dikt'),
    (r'\bdicking\b'       , 'diking'),
    (r'\bdickhead\b'      , 'dikhed'),
    (r'\bdickheads\b'     , 'dikheds'),
    (r'\bdickhole\b'      , 'dikhol'),
    (r'\bdickface\b'      , 'dikface'),
    (r'\bdickwad\b'       , 'dikwad'),
    (r'\bdickweed\b'      , 'dikweed'),
    (r'\bdickbag\b'       , 'dikbag'),
    (r'\bdickbrain\b'     , 'dikbrain'),
    (r'\bdickbreath\b'    , 'dikbreth'),
    (r'\bdickcheese\b'    , 'dikcheez'),
    (r'\bdickless\b'      , 'dikles'),
    (r'\bdicklicker\b'    , 'dikliker'),
    (r'\bdicknose\b'      , 'diknoz'),
    (r'\bdickpimple\b'    , 'dikpimpl'),
    (r'\bdickskin\b'      , 'dikskin'),
    (r'\bdickstain\b'     , 'dikstain'),
    (r'\bprick\b'         , 'prik'),
    (r'\bpricks\b'        , 'priks'),
    (r'\bprickhead\b'     , 'prikhed'),
    (r'\bpussy\b'         , 'pussi'),
    (r'\bpussies\b'       , 'pussiz'),
    (r'\bpussyhole\b'     , 'pussihol'),
    (r'\bpussyface\b'     , 'pussiface'),
    (r'\bpussywhipped\b'  , 'pussiwipd'),
    (r'\bpenis\b'         , 'peenis'),
    (r'\bpenises\b'       , 'peenises'),
    (r'\bpenile\b'        , 'peenile'),
    (r'\bpecker\b'        , 'peker'),
    (r'\bpeckers\b'       , 'pekers'),
    (r'\bpeckerhead\b'    , 'pekerhed'),
    (r'\bpeckerwood\b'    , 'pekerwood'),
    (r'\bass\b'           , 'ahss'),
    (r'\basses\b'         , 'ahsses'),
    (r'\basshole\b'       , 'ahsshol'),
    (r'\bassholes\b'      , 'ahssholes'),
    (r'\basshat\b'        , 'ahsshat'),
    (r'\basshead\b'       , 'ahsshed'),
    (r'\basswipe\b'       , 'ahsswipe'),
    (r'\bassclown\b'      , 'ahssclown'),
    (r'\bassmonkey\b'     , 'ahssmonkey'),
    (r'\bassbite\b'       , 'ahssbite'),
    (r'\bassbanger\b'     , 'ahssbanger'),
    (r'\bassbreath\b'     , 'ahssbreth'),
    (r'\bassface\b'       , 'ahssface'),
    (r'\bassholeish\b'    , 'ahssholish'),
    (r'\bassholery\b'     , 'ahssholery'),
    (r'\bdumbass\b'       , 'dumbahss'),
    (r'\bdumbasses\b'     , 'dumbahsses'),
    (r'\bsmartass\b'      , 'smartahss'),
    (r'\bsmartasses\b'    , 'smartahsses'),
    (r'\blazyass\b'       , 'lazyahss'),
    (r'\bhardass\b'       , 'hardahss'),
    (r'\bbadass\b'        , 'badahss'),
    (r'\bbadassery\b'     , 'badahssery'),
    (r'\barse\b'          , 'ahrs'),
    (r'\barsi\b'          , 'ahrsi'),
    (r'\bbitch\b'         , 'bytch'),
    (r'\bbitches\b'       , 'bytches'),
    (r'\bbitchy\b'        , 'bychy'),
    (r'\bbitchin\b'       , 'bychin'),
    (r'\bbitchass\b'      , 'bychahss'),
    (r'\bbitchface\b'     , 'bychface'),
    (r'\bbitchtits\b'     , 'bychtits'),
    (r'\bbastard\b'       , 'bahsterd'),
    (r'\bbastards\b'      , 'bahsterds'),
    (r'\bbastardly\b'     , 'bahsterdly'),
    (r'\bbastardized\b'   , 'bahsterdized'),
    (r'\bbastardization\b', 'bahsterdization'),
    (r'\bwhore\b'         , 'hoar'),
    (r'\bwhores\b'        , 'hoarz'),
    (r'\bwhoring\b'       , 'hoaring'),
    (r'\bwhorish\b'       , 'hoarish'),
    (r'\bwhorehouse\b'    , 'hoarhouse'),
    (r'\bwhorebag\b'      , 'hoarbag'),
    (r'\bwhoreface\b'     , 'hoarface'),
    (r'\bslut\b'          , 'sluht'),
    (r'\bsluts\b'         , 'sluhts'),
    (r'\bslutty\b'        , 'sluhty'),
    (r'\bslutted\b'       , 'sluhted'),
    (r'\bslutface\b'      , 'sluhtface'),
    (r'\bslutbag\b'       , 'sluhtbag'),
    (r'\bslutbucket\b'    , 'sluhtbucket'),
    (r'\bgoddamn\b'       , 'gohdehm'),
    (r'\bgoddamned\b'     , 'gohdehmd'),
    (r'\bgoddammit\b'     , 'gohdehmit'),
    (r'\bdamn\b'          , 'dehm'),
    (r'\bdamned\b'        , 'dehmd'),
    (r'\bdamnit\b'        , 'dehmit'),
    (r'\bdammit\b'        , 'dehmit'),
    (r'\bhell\b'          , 'hel'),
    (r'\bhellish\b'       , 'helish'),
    (r'\bhellhole\b'      , 'helhol'),
    (r'\bhellfire\b'      , 'helfyr'),
    (r'\bhellhound\b'     , 'helhound'),
    (r'\bpiss\b'          , 'pis'),
    (r'\bpissed\b'        , 'pist'),
    (r'\bpissing\b'       , 'pising'),
    (r'\bpisses\b'        , 'pises'),
    (r'\bpissed off\b'    , 'pist off'),
    (r'\bpisshole\b'      , 'pishol'),
    (r'\bpisspot\b'       , 'pispot'),
    (r'\bpissface\b'      , 'pisface'),
    (r'\bpisshead\b'      , 'pished'),
    (r'\bcum\b'           , 'kuhm'),
    (r'\bcums\b'          , 'kuhms'),
    (r'\bcumming\b'       , 'kuhming'),
    (r'\bcummed\b'        , 'kuhmd'),
    (r'\bjizz\b'          , 'jiz'),
    (r'\bjizzed\b'        , 'jizd'),
    (r'\bjizzing\b'       , 'jizing'),
    (r'\bspunk\b'         , 'spuhnk'),
    (r'\bspunked\b'       , 'spuhnkd'),
    (r'\bsemen\b'         , 'seemen'),
    (r'\bboner\b'         , 'bohnur'),
    (r'\bboners\b'        , 'bohnurs'),
    (r'\berection\b'      , 'erekshun'),
    (r'\berections\b'     , 'erekshuns'),
    (r'\baroused\b'       , 'arouzd'),
    (r'\barousal\b'       , 'arouzal'),
    (r'\barousing\b'      , 'arouzing'),
    (r'\blust\b'          , 'luhst'),
    (r'\blusty\b'         , 'luhsty'),
    (r'\blustful\b'       , 'luhstful'),
    (r'\bsex\b'           , 'seks'),
    (r'\bsexual\b'        , 'seksual'),
    (r'\bsexually\b'      , 'seksuali'),
    (r'\bsexy\b'          , 'seksi'),
    (r'\bintercourse\b'   , 'interkors'),
    (r'\bcoitus\b'        , 'koytus'),
    (r'\bcoital\b'        , 'koytal'),
    (r'\bcopulate\b'      , 'kopyulayt'),
    (r'\bcopulation\b'    , 'kopyulayshun'),
    (r'\bfornication\b'   , 'fornikayshun'),
    (r'\bballs\b'         , 'balz'),
    (r'\bball sack\b'     , 'bal sak'),
    (r'\btesticles\b'     , 'testikulz'),
    (r'\btestes\b'        , 'testeez'),
    (r'\btesticular\b'    , 'testikular'),
    (r'\bnut sack\b'      , 'nut sak'),
    (r'\bscrotum\b'       , 'skrohtum'),
    (r'\bscrotal\b'       , 'skrohtal'),
    (r'\bvagina\b'        , 'vajayna'),
    (r'\bvaginal\b'       , 'vajaynal'),
    (r'\blabia\b'         , 'laybia'),
    (r'\bclitoris\b'      , 'klitoris'),
    (r'\bclit\b'          , 'kliht'),
    (r'\bclitoral\b'      , 'klitoral'),
    (r'\bnipples\b'       , 'nipulz'),
    (r'\bnipple\b'        , 'nipul'),
    (r'\bbreasts\b'       , 'brests'),
    (r'\btitties\b'       , 'titz'),
    (r'\bboobs\b'         , 'boobz'),
    (r'\bboobies\b'       , 'boobiz'),
    (r'\bknockers\b'      , 'nokkers'),
    (r'\bheadlights\b'    , 'hedlyts'),
    (r'\bforeskin\b'      , 'fohrskin'),
    (r'\buncircumcised\b' , 'unsirkumsyzd'),
    (r'\bcircumcised\b'   , 'sirkumsyzd'),
    (r'\banus\b'          , 'aynas'),
    (r'\banal\b'          , 'aynal'),
    (r'\bbutt\b'          , 'buht'),
    (r'\bbuttocks\b'      , 'buhtoks'),
    (r'\bbuttcheeks\b'    , 'buhtcheeks'),
    (r'\bbutthole\b'      , 'buhtol'),
    (r'\brosebud\b'       , 'rozbud'),
    (r'\bcherry\b'        , 'cheri'),
    (r'\bfellatio\b'      , 'felaysho'),
    (r'\bcunnilingus\b'   , 'kunilingus'),
    (r'\bdeepthroat\b'    , 'deepthroht'),
    (r'\bdeepthroating\b' , 'deepthrohting'),
    (r'\bthroat\b'        , 'throht'),
    (r'\btongue\b'        , 'tuhng'),
    (r'\bpounded\b'       , 'poundid'),
    (r'\bstroke\b'        , 'strohk'),
    (r'\bstroking\b'      , 'strohking'),
    (r'\bstroked\b'       , 'strohkd'),
    (r'\bsuck\b'          , 'suhk'),
    (r'\bsucking\b'       , 'suhking'),
    (r'\bsucked\b'        , 'suhkd'),
    (r'\bswallow\b'       , 'swalo'),
    (r'\bswallowing\b'    , 'swalowing'),
    (r'\bswallowed\b'     , 'swalod'),
    (r'\bchoke\b'         , 'choak'),
    (r'\bchoking\b'       , 'choaking'),
    (r'\bchoked\b'        , 'choakt'),
    (r'\bgagging\b'       , 'gaging'),
    (r'\bgagged\b'        , 'gagd'),
    (r'\bslide\b'         , 'slid'),
    (r'\bdripped\b'       , 'dript'),
    (r'\bmoan\b'          , 'mohn'),
    (r'\bmoaning\b'       , 'mohning'),
    (r'\bscream\b'        , 'skreem'),
    (r'\bscreaming\b'     , 'skreeming'),
    (r'\byell\b'          , 'yel'),
    (r'\byelling\b'       , 'yeling'),
    (r'\bcry\b'           , 'kry'),
    (r'\bcrying\b'        , 'krying'),
    (r'\bclimax\b'        , 'klimax'),
    (r'\bclimaxed\b'      , 'klimaxd'),
    (r'\bclimaxing\b'     , 'klimaxing'),
    (r'\borgasm\b'        , 'orgazm'),
    (r'\borgasms\b'       , 'orgazms'),
    (r'\borgasmic\b'      , 'orgazmik'),
    (r'\bcoming\b'        , 'kumming'),
    (r'\bcame\b'          , 'kaym'),
    (r'\bspill\b'         , 'spil'),
    (r'\bspilled\b'       , 'spild'),
    (r'\brelease\b'       , 'relees'),
    (r'\breleased\b'      , 'releest'),
    (r'\bcreampie\b'      , 'kreempie'),
    (r'\bcreampied\b'     , 'kreempied'),
    (r'\bflooded\b'       , 'floded'),
    (r'\bflooding\b'      , 'floding'),
    (r'\bsoaked\b'        , 'soakt'),
    (r'\bwetness\b'       , 'wetnes'),
    (r'\bloose\b'         , 'loos'),
    (r'\bhole\b'          , 'hol'),
    (r'\bentrance\b'      , 'entrans'),
    (r'\binside\b'        , 'insaid'),
    (r'\bcold\b'          , 'kold'),
    (r'\bcolder\b'        , 'kolder'),
    (r'\bcoldest\b'       , 'koldest'),
    (r'\bfull\b'          , 'ful'),
    (r'\bfuller\b'        , 'fuler'),
    (r'\bfullest\b'       , 'fulest'),
    (r'\bfilled\b'        , 'fild'),
    (r'\bfilling\b'       , 'filing'),
    (r'\bstuffed\b'       , 'stufft'),
    (r'\bpacked\b'        , 'pakt'),
    (r'\bpacking\b'       , 'paking'),
    (r'\bbeat\b'          , 'beet'),
    (r'\bbeaten\b'        , 'beeten'),
    (r'\bbeating\b'       , 'beeting'),
    (r'\bslapped\b'       , 'slapt'),
    (r'\bslapping\b'      , 'slaping'),
    (r'\bstrangle\b'      , 'strangl'),
    (r'\bstrangled\b'     , 'strangld'),
    (r'\bsqueeze\b'       , 'skweez'),
    (r'\bsqueezed\b'      , 'skweezd'),
    (r'\bsqueezing\b'     , 'skweezeing'),
    (r'\bcrush\b'         , 'krush'),
    (r'\bcrushed\b'       , 'krusht'),
    (r'\bcrushing\b'      , 'krushing'),
    (r'\bbreak\b'         , 'brake'),
    (r'\bbreaking\b'      , 'braking'),
    (r'\btear\b'          , 'tair'),
    (r'\btearing\b'       , 'tairing'),
    (r'\bjuices\b'        , 'jooses'),
    (r'\bjuice\b'         , 'joose'),
    (r'\bliquid\b'        , 'likwid'),
    (r'\bsweat\b'         , 'swet'),
    (r'\bdracarys\b'      , 'dracaris'),
    (r'\bgripped\b'       , 'gript'),
    (r'\bclutched\b'      , 'clutcht'),
    (r'\bpressed\b'       , 'prest'),
    (r'\bmilked\b'        , 'milkt'),
    (r'\bexploded\b'      , 'explodid'),
    (r'\bdrowned\b'       , 'drownd'),
    (r'\bdevoured\b'      , 'devourd'),
    (r'\bconsumed\b'      , 'consumd'),
]

def sanitize_for_tts(text):
    for pattern, replacement in _WORD_REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def split_text(text):
    """
    Split text into segments:
      *action text* → narrator voice   (also handles **double asterisks**)
      regular text  → NPC voice
    Matching a run of asterisks (\\*+) on each side means a **bold** action is
    captured whole, leaving no stray "*" to be spoken or to split oddly. An
    action opened but never closed is closed at the end of the message first
    (see _autoclose_actions), so forgetting the trailing ** still narrates.
    """
    parts = re.split(r'(\*+[^*]+\*+)', _autoclose_actions(text))
    segments = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if p.startswith('*') and p.endswith('*'):
            inner = p.strip('*').strip()
            if inner:
                segments.append((NARRATOR_VOICE, inner))
        else:
            segments.append((None, p))
    return _merge_adjacent(_fold_short_narrator_segments(_merge_adjacent(segments)))


def _fold_short_narrator_segments(segments):
    """
    Keep tiny narrator asides out of their own TTS call.

    Each call is generated from scratch, so a two-word fragment is where the
    voice drifts most. Folding one into the line's next narrator segment keeps
    the words but spends one fewer generation on them. A fragment with no later
    narration to join is dropped — there is nothing to attach it to.
    """
    mode = (SHORT_NARRATOR_ACTION or "keep").lower()
    if mode == "keep" or not segments:
        return segments

    out, pending = [], []
    for voice, text in segments:
        if voice != NARRATOR_VOICE:
            out.append((voice, text))
            continue
        if len(text.split()) < MIN_NARRATOR_WORDS:
            if mode == "merge":
                pending.append(text)
                print(f"  [narrator] Folding short action {text!r} into the next narration.")
            else:
                print(f"  [narrator] Skipping short action {text!r}.")
            continue
        if pending:
            lead = " ".join(_ensure_sentence_punctuation(p) for p in pending)
            text = lead + " " + text
            pending = []
        out.append((voice, text))

    if pending:
        print(f"  [narrator] Dropped short action(s) {pending} — "
              f"no later narration in this line to fold them into.")
    return out


def _merge_adjacent(segments):
    """
    Join neighbouring segments that use the same voice into one call. Every
    /tts/speak is an independent generation — and another chance for Player2 to
    render the voice differently — so speaking "*he nods* *he smiles*" as one
    narrator line instead of two removes a drift point for free.
    """
    if not MERGE_ADJACENT_SEGMENTS:
        return segments
    merged = []
    for voice, text in segments:
        if merged and merged[-1][0] == voice:
            # Give the joined halves a sentence break, so two actions don't run
            # together as "he nods he smiles".
            left = _ensure_sentence_punctuation(merged[-1][1])
            merged[-1] = (voice, left + " " + text.lstrip())
        else:
            merged.append((voice, text))
    return merged


# ============================================================
#  TTS ROUTE
# ============================================================

# ============================================================
#  LIPSYNC BYTES INTERCEPT
#  Mod sends /v1/tts/bytes BEFORE showing "Ready to Respond" to pre-generate
#  lipsync audio. If this returns empty data, mod skips ALL playback.
#  We return a minimal silent WAV so the mod's check passes, while our
#  background thread handles real TTS playback via /v1/tts/speak.
# ============================================================

# Minimal silent 0.1s WAV in base64 (44 bytes header + silence)
_SILENT_WAV_B64 = (
    "UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA="
)

@app.route('/v1/tts/bytes', methods=['POST'])
@app.route('/tts/bytes', methods=['POST'])
def tts_bytes():
    """
    Intercept lipsync pre-generation bytes request.
    Return a minimal valid response so mod proceeds to show 'Ready to Respond'
    and trigger /v1/tts/speak — which our proxy handles properly.
    """
    print("  [BYTES] Lipsync bytes request intercepted — returning silent placeholder")
    return jsonify({"data": _SILENT_WAV_B64, "status": "ok"})


# ============================================================
#  ANSWERING A MOD THAT WANTS THE AUDIO ITSELF  (7.0 and later)
# ============================================================
# Player2 has no "bytes" endpoint: asking for audio IS /tts/speak with
# play_in_app false, and the audio comes back as a data URI holding a WAV —
# even when mp3 was asked for. Its WAV header carries a placeholder length
# (streamed), so never trust the frame count in it; read the frames instead.

def _audio_from_player2(text, voice, instructions, speed):
    """One segment, spoken by Player2 and handed back as WAV bytes."""
    body = {"text": text, "voice_ids": [voice], "play_in_app": False,
            "audio_format": "mp3", "speed": _capped_speed(speed)}
    if instructions:
        body["advanced_voice"] = {"instructions": instructions}
    r = requests.post(f"{REAL_PLAYER2}/v1/tts/speak", json=body,
                      headers=_game_headers(), timeout=_tts_timeout(text))
    r.raise_for_status()
    payload = (r.json() or {}).get("data") or ""
    if payload.startswith("data:"):
        payload = payload.split(",", 1)[1]
    return base64.b64decode(payload + "=" * (-len(payload) % 4))


def _join_wavs(clips):
    """Join segment clips end to end into one WAV."""
    import wave
    params, frames = None, []
    for c in clips:
        with wave.open(io.BytesIO(c)) as w:
            if params is None:
                params = w.getparams()
            frames.append(w.readframes(w.getnframes()))
    if params is None:
        return b""
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setparams(params)
        for f in frames:
            w.writeframes(f)
    return out.getvalue()


def _silent_wav(seconds=None):
    """A short run of silence, in the same format Player2 returns."""
    import wave
    secs = SILENT_REPLY_SECONDS if seconds is None else seconds
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(b"\x00\x00" * int(24000 * max(0.05, secs)))
    return out.getvalue()


def _as_data_uri(wav_bytes):
    """The shape the mod expects a spoken line to come back in."""
    return "data:audio/wav;base64," + base64.b64encode(wav_bytes).decode()


# ============================================================
#  WATCH MODE  —  narrate from the save files, out of the mod's way
# ============================================================
_watch_seen = {}            # save file -> how many history entries we have read


def _chunk_for_quick_start(segments):
    """
    Break long segments so the first words are heard sooner.

    Only length is at stake, never who speaks: each piece keeps its segment's
    voice. The first piece of the line is kept short on purpose — that one wait
    is the only one you actually feel, because every later piece is generated
    while the previous is still being spoken.
    """
    if not WATCHED_CHUNK_CHARS:
        return segments
    out = []
    for voice, text in segments:
        limit = (WATCHED_FIRST_CHUNK_CHARS if not out else WATCHED_CHUNK_CHARS)
        if len(text) <= limit:
            out.append((voice, text))
            continue
        pieces = _split_sentences(text, limit) or [text]
        # Only the opening piece is short; the rest are re-joined up to the
        # normal size so the line does not become a string of fragments.
        first, rest = pieces[0], " ".join(pieces[1:]).strip()
        out.append((voice, first))
        if rest:
            for piece in (_split_sentences(rest, WATCHED_CHUNK_CHARS) or [rest]):
                out.append((voice, piece))
    return out


def _watch_voice_for(npc_data):
    """The voice this character should speak in, pinned as always."""
    string_id = npc_data.get("StringId", "")
    gender = (npc_data.get("Gender", "male") or "male").lower()
    # 7.0 assigns each character a voice of its own; it is only a starting
    # point — the pin is what keeps them sounding the same from turn to turn.
    source = (npc_data.get("AssignedTTSVoice")
              or npc_data.get("CharacterVoice") or "")
    return pin_npc_voice(string_id, npc_data.get("Name"),
                         resolve_voice(source, gender, string_id),
                         source, gender)


def _watch_speak(npc_data, text):
    """Queue one newly-written line to be spoken, exactly as a request would."""
    global _play_seq_counter
    voice = _watch_voice_for(npc_data)
    with _play_cond:
        _play_seq_counter += 1
        seq = _play_seq_counter
        _play_queue.append({
            "seq": seq, "text": text, "voice_id": voice,
            "speed": 1.0, "ts": time.time(), "kind": "watched",
            "npc_data": npc_data,
        })
        _play_cond.notify()
    print(f"\n--- NEW LINE (watched, seq {seq}) ---")
    print(f"  {npc_data.get('Name')} | "
          f"{VOICE_DB.get(voice, {}).get('name', voice)}")
    print(f"  {text[:110]}...")


def _watch_scan(prime=False):
    """
    Look for lines that have appeared since the last look.

    A character's own lines are the ones labelled with their id; the player's
    turns live in the same history and are skipped. On the first pass we only
    take note of how much is already there, so starting the proxy in the middle
    of a conversation does not read the backlog aloud.
    """
    for path, data in load_all_npc_data().items():
        history = data.get("ConversationHistory") or []
        known = _watch_seen.get(path)
        if known is None:
            _watch_seen[path] = 0 if (WATCH_SPEAK_BACKLOG and not prime) else len(history)
            if _watch_seen[path] == len(history):
                continue
            known = _watch_seen[path]
        if len(history) <= known:
            if len(history) < known:        # a new campaign, or a reset file
                _watch_seen[path] = len(history)
            continue
        fresh = history[known:]
        _watch_seen[path] = len(history)
        if prime:
            continue
        own_id = data.get("StringId", "")
        for entry in fresh:
            speaker_id, body = _entry_speaker_id(entry)
            if not body or not body.strip():
                continue
            if speaker_id != own_id:        # the player's turn, or someone else's
                continue
            _watch_speak(data, body)


def _watch_loop():
    """Watch the save folder for new lines, for as long as the proxy runs."""
    try:
        _watch_scan(prime=True)
        print(f"  [watch] Watching {len(_watch_seen)} character file(s) for new "
              f"lines — the mod is left entirely alone.")
    except Exception as e:
        print(f"  [watch] Could not read the save folder yet: {e}")
    while True:
        time.sleep(WATCH_POLL_SECONDS)
        try:
            _watch_scan()
        except Exception as e:
            print(f"  [watch] Scan failed: {e}")
            time.sleep(2.0)


def _recover_line_for_audio(received_text, voice_id):
    """
    Work out who is speaking and get their line back WITH its actions.

    The mod strips the *actions* before asking for speech, so the text we are
    handed has nothing to narrate. The save file keeps the whole line, so the
    speaker is found by what was said and the full line recovered from there —
    the same way the playback worker does it. Returns
    (full line, character id, voice to speak it in); falls back to the mod's own
    text and voice when nothing can be confirmed, so a line is never lost.
    """
    npc_data, _npc_path, full_text = find_speaker_by_text(
        received_text, MATCH_POLL_TIMEOUT)
    if not npc_data:
        print("  [compose] speaker unconfirmed — using the mod's own line.")
        return received_text, None, voice_id
    string_id = npc_data.get("StringId", "")
    gender = (npc_data.get("Gender", "male")).lower()
    if not full_text or not _texts_match(full_text, received_text):
        # What we recovered is not this line (a stale or same-voice
        # conversation). Speak what the mod asked for rather than the wrong text.
        print("  [compose] recovered line does not match — using the mod's own.")
        return received_text, string_id, resolve_voice(voice_id, gender, string_id)
    voice = pin_npc_voice(string_id, npc_data.get("Name"),
                          resolve_voice(voice_id, gender, string_id),
                          voice_id, gender)
    print(f"  [compose] {npc_data.get('Name')} | "
          f"{VOICE_DB.get(voice, {}).get('name', voice)}")
    return full_text, string_id, voice


def _compose_line_audio(text, npc_voice, speed, mod_instructions=None,
                        string_id=None):
    """
    Build ONE clip of a whole line: narrated actions in the narrator's voice,
    speech in the character's own, with our casting and delivery notes.

    The text the mod sends has had its actions stripped (7.0 does this exactly
    as 6.x did), so the caller is expected to have recovered the full line from
    the save file first — otherwise there is nothing to narrate.
    """
    segments = split_text(text)
    dial = _effective_speed(speed)
    clips = []
    for who, seg_text in segments:
        is_narr = (who == NARRATOR_VOICE)
        voice = NARRATOR_VOICE if is_narr else npc_voice
        if is_narr:
            instructions = narrator_instructions()
            spoken = (_normalize_narrator_text(seg_text)
                      if NARRATOR_NORMALIZE_TEXT else seg_text)
        else:
            instructions = (mod_instructions
                            if (USE_MOD_INSTRUCTIONS and mod_instructions)
                            else (pinned_character_instructions(string_id)
                                  or voice_accent_instructions(voice)))
            spoken = seg_text
        seg_speed = _narrator_speed(dial) if is_narr else dial
        clips.append(_audio_from_player2(spoken, voice, instructions, seg_speed))
        print(f"    [compose] {'NARR' if is_narr else 'NPC '} "
              f"{VOICE_DB.get(voice, {}).get('name', '?'):<9} {spoken[:48]}")
    return _join_wavs(clips)


_mod_speed = None
_mod_speed_mtime = None


def mod_tts_speed():
    """
    The MCM "TTS Speed" slider value, or None if it can't be read. MCM writes
    the file when its menu is closed; this re-reads on every change, and falls
    back to None (request speed) if the file disappears.
    """
    global _mod_speed, _mod_speed_mtime
    try:
        mtime = os.path.getmtime(MOD_SETTINGS_FILE)
    except OSError:
        _mod_speed, _mod_speed_mtime = None, None
        return None
    if mtime != _mod_speed_mtime:
        try:
            with open_shared(MOD_SETTINGS_FILE, "utf-8") as f:
                val = float(json.load(f).get("TTSSpeed"))
            if val != _mod_speed:
                print(f"  [speed] MCM TTS Speed slider -> {val:g}")
            _mod_speed = val
        except Exception as e:
            print(f"  [speed] Could not read TTSSpeed from MCM settings: {e}")
            _mod_speed = None
        _mod_speed_mtime = mtime
    return _mod_speed


TTS_SPEED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "tts_speed.txt")
_own_speed = None
_own_speed_mtime = None


def speed_name(value):
    """The nearest preset's name, for printing and for the tray header."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "normal"
    name, best = None, None
    for n, preset in TTS_SPEED_PRESETS:
        gap = abs(preset - v)
        if best is None or gap < best:
            name, best = n, gap
    if best is not None and best <= 0.03:
        return name.lower()
    return f"{name.lower()} (set by hand)" if name else "normal"


def tts_speed():
    """
    Our own speech speed, or None if it was never set.

    Kept in tts_speed.txt and re-read whenever the file changes, so a pick from
    the tray menu reaches the next line with no restart. If the file is deleted
    the dial is forgotten and the MCM slider takes over again.
    """
    global _own_speed, _own_speed_mtime
    try:
        mtime = os.path.getmtime(TTS_SPEED_FILE)
    except OSError:
        if _own_speed is not None:
            print("  [speed] tts_speed.txt is gone — back to the mod's slider.")
        _own_speed, _own_speed_mtime = None, None
        return None
    if mtime != _own_speed_mtime:
        value = None
        try:
            with open(TTS_SPEED_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        value = _capped_speed(float(line.split()[0]))
                        break
        except Exception as e:
            print(f"  [speed] Could not read tts_speed.txt: {e}")
        if value is not None and value != _own_speed:
            print(f"  [speed] Speech speed -> {speed_name(value)}.")
        _own_speed = value
        _own_speed_mtime = mtime
    return _own_speed


def set_tts_speed(value):
    """Set the dial and remember it. Applies to the next line spoken."""
    global _own_speed, _own_speed_mtime
    speed = _capped_speed(value)
    try:
        with open(TTS_SPEED_FILE, "w", encoding="utf-8") as f:
            f.write("# Speech speed — set from the tray menu "
                    "(\"Speech speed\"), or edit the number below.\n")
            f.write("# 1.0 is Player2's normal pace. Delete this file to go "
                    "back to the mod's own slider.\n")
            f.write(f"{speed:g}\n")
    except Exception as e:
        print(f"  [speed] Could not save the speech speed: {e}")
        return None
    _own_speed, _own_speed_mtime = None, None     # re-read, and announce it
    tts_speed()
    return speed


TTS_VOLUME_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "tts_volume.txt")
_own_volume = None
_own_volume_mtime = None


def _capped_volume(value):
    """Hold a volume inside the range, whoever set it."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return TTS_VOLUME_DEFAULT
    return max(MIN_TTS_VOLUME, min(MAX_TTS_VOLUME, v))


def volume_name(value):
    """The nearest preset's name, for printing and for the tray header."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "normal"
    name, best = None, None
    for n, preset in TTS_VOLUME_PRESETS:
        gap = abs(preset - v)
        if best is None or gap < best:
            name, best = n, gap
    if best is not None and best <= 0.03:
        return name.lower()
    return f"{name.lower()} (set by hand)" if name else "normal"


def tts_volume():
    """
    Our own volume, or None if it was never set.

    Kept in tts_volume.txt and re-read whenever the file changes, so a pick
    from the tray menu reaches the next line with no restart. Deleting the
    file forgets the dial and leaves every clip at the loudness it was made.
    """
    global _own_volume, _own_volume_mtime
    if not OWN_TTS_VOLUME:
        return None
    try:
        mtime = os.path.getmtime(TTS_VOLUME_FILE)
    except OSError:
        if _own_volume is not None:
            print("  [volume] tts_volume.txt is gone — back to full volume.")
        _own_volume, _own_volume_mtime = None, None
        return None
    if mtime != _own_volume_mtime:
        value = None
        try:
            with open(TTS_VOLUME_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        value = _capped_volume(float(line.split()[0]))
                        break
        except Exception as e:
            print(f"  [volume] Could not read tts_volume.txt: {e}")
        if value is not None and value != _own_volume:
            print(f"  [volume] Volume -> {volume_name(value)}.")
        _own_volume = value
        _own_volume_mtime = mtime
    return _own_volume


def set_tts_volume(value):
    """Set the dial and remember it. Applies to the next clip played."""
    global _own_volume, _own_volume_mtime
    volume = _capped_volume(value)
    try:
        with open(TTS_VOLUME_FILE, "w", encoding="utf-8") as f:
            f.write("# Volume — set from the tray menu (\"Volume\"), or edit "
                    "the number below.\n")
            f.write("# 1.0 is the loudness the clip was made at, which is the "
                    "mod's own TTS Volume\n")
            f.write("# slider. Delete this file to go back to that.\n")
            f.write(f"{volume:g}\n")
    except Exception as e:
        print(f"  [volume] Could not save the volume: {e}")
        return None
    _own_volume, _own_volume_mtime = None, None     # re-read, and announce it
    tts_volume()
    return volume


def _narrator_speed(dial):
    """
    The narrator's pace at this dial setting.

    It follows the dial only part of the way and never leaves its clean band: a
    narrator pushed fast rushes, drops pitch and slurs. NARRATOR_SPEED = None
    keeps the old behaviour of following the dial exactly.
    """
    if not NARRATOR_SPEED:
        return dial
    moved = NARRATOR_SPEED + (dial - 1.0) * NARRATOR_SPEED_FOLLOW
    lo, hi = NARRATOR_SPEED_BAND
    return max(lo, min(hi, moved))


def _effective_speed(requested):
    """
    The speed to use: our own dial first, then the MCM slider, then whatever the
    request carried (which has only ever been normal).
    """
    if OWN_TTS_SPEED:
        own = tts_speed()
        if own is not None:
            return own
    if USE_MOD_TTS_SPEED:
        slider = mod_tts_speed()
        if slider is not None:
            return slider
    return requested


def _capped_speed(speed):
    """
    Clamp the requested TTS speed to [0.25, MAX_TTS_SPEED]. Guards against a
    cranked MCM "TTS Speed" slider (the mod forwards it as the request speed)
    making speech unintelligibly fast.
    """
    try:
        s = float(speed)
    except (TypeError, ValueError):
        s = 1.0
    return max(0.25, min(MAX_TTS_SPEED, s))


def _tts_timeout(text):
    """Seconds to wait on one Player2 attempt for this text (see TTS_TIMEOUT_*)."""
    t = TTS_TIMEOUT_BASE + TTS_TIMEOUT_PER_CHAR * len(text or "")
    return max(TTS_TIMEOUT_MIN, min(TTS_TIMEOUT_MAX, t))


def _speak_once(text, voice, instructions, label, playback_speed):
    """
    Send one piece of text to Player2 TTS, retrying on non-200 / errors.
    Returns True on a 200. Blocks until Player2 finishes generating + playing
    (play_in_app), which is what lets the single worker keep lines in order.
    """
    payload = {"text": sanitize_for_tts(text), "play_in_app": True,
               "speed": _capped_speed(playback_speed), "voice_ids": [voice]}
    if instructions:
        payload["advanced_voice"] = {"instructions": instructions}
    for attempt in range(1, TTS_RETRIES + 2):
        # If playback was cut short (e.g. the NPC's reply arrived while the
        # player's line was speaking), stop here — never retry a cancelled line,
        # or it would start over after being interrupted.
        if _playback_cancel.is_set():
            return False
        try:
            t0 = time.time()
            resp = requests.post(f"{REAL_PLAYER2}/v1/tts/speak", json=payload,
                                 headers=_game_headers(),
                                 timeout=_tts_timeout(payload["text"]))
            dt = time.time() - t0
            if resp.status_code == 200:
                extra = f" (attempt {attempt})" if attempt > 1 else ""
                vname = VOICE_DB.get(voice, {}).get("name", str(voice)[:8])
                if instructions == _accent_instructions_cache.get(voice):
                    instr = " +accent"
                else:
                    instr = " +instr" if instructions else ""
                print(f"  [BG] {label} 200 in {dt:.2f}s  voice={vname}{instr}{extra}")
                return True
            print(f"  [BG] {label} {resp.status_code} in {dt:.2f}s (attempt {attempt})")
        except Exception as e:
            print(f"  [BG] {label} ERROR: {e} (attempt {attempt})")
        if attempt <= TTS_RETRIES and not _playback_cancel.is_set():
            time.sleep(TTS_RETRY_DELAY)
    return False


def _split_sentences(text, max_chars):
    """Break text at sentence boundaries into chunks up to ~max_chars."""
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks, cur = [], ""
    for p in parts:
        if not cur:
            cur = p
        elif len(cur) + 1 + len(p) <= max_chars:
            cur += " " + p
        else:
            chunks.append(cur); cur = p
    if cur:
        chunks.append(cur)
    return chunks


def _ensure_sentence_punctuation(text):
    """
    Give short action fragments a sentence-ending period so the TTS voice paces
    them like a sentence instead of rushing an unpunctuated fragment. Trailing
    commas/semicolons/colons are treated as fragment-y and replaced.
    """
    t = (text or "").strip().rstrip(" ,;:")
    if t and t[-1] not in ".!?…":
        t += "."
    return t


SPEECH_RATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "speech_rate.txt")
_speech_rate = None
_speech_rate_mtime = None


def speech_rate():
    """
    Characters per second, from speech_rate.txt if --calibrate has written one,
    otherwise the constant. Re-read when the file changes, so a fresh
    calibration applies without restarting the proxy.
    """
    global _speech_rate, _speech_rate_mtime
    try:
        mtime = os.path.getmtime(SPEECH_RATE_FILE)
    except OSError:
        mtime = None
    if mtime is None and _speech_rate is not None:
        # The file was deleted. Fall back to the constant instead of holding on
        # to the last value read — otherwise a bad calibration cannot be undone
        # by removing the file, which is the obvious way to undo it.
        print(f"  [speed] {os.path.basename(SPEECH_RATE_FILE)} removed — "
              f"back to {SPEECH_CHARS_PER_SECOND:.1f} ch/s")
        _speech_rate = None
        _speech_rate_mtime = None
    if mtime is not None and mtime != _speech_rate_mtime:
        try:
            with open(SPEECH_RATE_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.split("#")[0].strip()
                    if not line:
                        continue
                    val = float(line)
                    if 4.0 <= val <= 40.0:      # anything outside is a typo
                        if val != _speech_rate:
                            print(f"  [speed] Speech rate -> {val:.1f} ch/s (from file)")
                        _speech_rate = val
                    else:
                        print(f"  [speed] Ignoring implausible rate in "
                              f"{os.path.basename(SPEECH_RATE_FILE)}: {val}")
                    break
            _speech_rate_mtime = mtime
        except Exception as e:
            print(f"  [speed] Could not read {SPEECH_RATE_FILE}: {e}")
    return _speech_rate or SPEECH_CHARS_PER_SECOND


def _normalize_narrator_text(text):
    """
    Plain, evenly punctuated narrator text. Player2 mispronounces and trips over
    typographic punctuation in fragments — "a shaky breath; he lifts his chin",
    "voice — low", curly apostrophes — so those become commas, straight quotes
    and full stops. The words themselves are never changed.
    """
    t = (text or "").replace("\u2019", "'").replace("\u2018", "'")
    t = re.sub(r'[\u201c\u201d"]', "", t)                 # quote marks add nothing spoken
    t = re.sub(r"\s*[\u2014\u2013]\s*|\s+-\s+", ", ", t)   # em/en dash, spaced hyphen
    # An ellipsis is a pause inside a sentence, not the end of one. Turning it
    # into a full stop left the next word lowercase after it ("A long pause.
    # then a nod."), which is broken text for a voice to read; a comma keeps
    # the pause and keeps the sentence whole.
    t = re.sub(r"\s*(\.{2,}|\u2026)\s*", ", ", t)
    t = t.replace(";", ",")
    t = re.sub(r"\s*,(\s*,)+", ",", t)                      # doubled commas
    t = re.sub(r"\s+", " ", t).strip(" ,")
    t = _ensure_sentence_punctuation(t)
    return t[:1].upper() + t[1:]


def _estimated_speech_seconds(text, speed):
    """Roughly how long Player2 will take to speak this text, in seconds."""
    n = len(text or "")
    if not n:
        return 0.0
    try:
        spd = float(speed) or 1.0
    except (TypeError, ValueError):
        spd = 1.0
    return n / (speech_rate() * max(0.25, spd))


def _pad_for_audio(text, speed, elapsed, label):
    """
    Wait out whatever is left of a segment's speech after its call returned, so
    the next segment doesn't start while this one is still audible. Skipped when
    playback has been cut short.
    """
    if not PAD_SEGMENTS_TO_AUDIO_LENGTH or _playback_cancel.is_set():
        return
    # Estimate from the speed Player2 is actually given. Above MAX_TTS_SPEED
    # the audio is capped, so using the raw value would under-wait and overlap.
    remaining = _estimated_speech_seconds(text, _capped_speed(speed)) - elapsed
    if remaining <= 0.05:
        return
    wait = min(remaining, MAX_SEGMENT_PAD)
    print(f"  [BG] {label} waiting {wait:.1f}s for audio to finish")
    # Wake immediately if the line gets cut off while we're waiting.
    _playback_cancel.wait(wait)


def _play_segments(segments, resolved_voice, npc_instructions, playback_speed,
                   character_anchor=None):
    """Play all segments of one line sequentially (called by the worker)."""
    for i, (forced_voice, seg_text) in enumerate(segments):
        if _playback_cancel.is_set():
            print(f"  [BG] Cut off before segment {i+1}.")
            # A segment already handed to Player2 can still be sounding; the
            # generation that was in flight when the cancel landed would
            # otherwise play over whatever comes next.
            _stop_player2_audio()
            return
        is_narrator = (forced_voice == NARRATOR_VOICE)
        voice = NARRATOR_VOICE if is_narrator else resolved_voice
        if not voice:
            print(f"  [BG] No voice for segment {i+1}, skipping")
            continue
        if is_narrator:
            instructions = narrator_instructions()
        else:
            # A constant per-voice accent anchor rather than the per-turn LLM
            # notes: identical text on every call is what keeps the accent put.
            instructions = (character_anchor
                            or (npc_instructions
                                if (SEND_VOICE_INSTRUCTIONS and npc_instructions)
                                else voice_accent_instructions(voice)))

        # Narrator: follows the speed dial part of the way, and tidy punctuation.
        # Characters: the dial in full, and their text untouched.
        seg_speed = _narrator_speed(playback_speed) if is_narrator else playback_speed
        if is_narrator and NARRATOR_NORMALIZE_TEXT:
            text_to_speak = _normalize_narrator_text(seg_text)
        elif is_narrator and NARRATOR_FORCE_PUNCTUATION:
            text_to_speak = _ensure_sentence_punctuation(seg_text)
        else:
            text_to_speak = seg_text

        t_seg = time.time()
        ok = _speak_once(text_to_speak, voice, instructions, f"[{i+1}]", seg_speed)
        _pad_for_audio(text_to_speak, seg_speed, time.time() - t_seg, f"[{i+1}]")

        # Recovery: if Player2 failed this segment (typically a long character
        # line that timed out into a 500), speak it as smaller sentence chunks
        # so the character isn't lost entirely.
        if not ok and TTS_CHUNK_ON_FAILURE and not _playback_cancel.is_set():
            chunks = _split_sentences(text_to_speak, TTS_CHUNK_MAX_CHARS)
            if len(chunks) > 1:
                print(f"  [BG] [{i+1}] failed — retrying as {len(chunks)} "
                      f"sentence chunks...")
                for j, ch in enumerate(chunks):
                    if _playback_cancel.is_set():
                        break
                    t_ch = time.time()
                    _speak_once(ch, voice, instructions, f"[{i+1}.{j+1}]", seg_speed)
                    _pad_for_audio(ch, seg_speed, time.time() - t_ch, f"[{i+1}.{j+1}]")

        if i < len(segments) - 1:
            time.sleep(PAUSE)


def _process_job(job):
    """
    Resolve and voice one queued TTS line. Runs on the single playback worker,
    so everything here — NPC matching, JSON polling and audio — happens in strict
    arrival order and never overlaps another line.
    """
    received_text  = job["text"]
    voice_id       = job["voice_id"]
    # The MCM slider, not the request: the mod has only ever sent 1.0.
    playback_speed = _effective_speed(job["speed"])

    # A line read straight out of the save file (watch mode). We already know
    # who said it and in what voice, and the text still has its *actions*, so
    # none of the matching below is needed — split it and speak it.
    if job.get("kind") == "watched":
        npc_data = job.get("npc_data") or {}
        print(f"\n--- SPEAKING (watched, seq {job['seq']}) ---")
        segments = split_text(received_text)
        if is_group_conversation(npc_data):
            segments = announce_speaker(segments, npc_data)
        else:
            _reset_announced_speaker()
        segments = _chunk_for_quick_start(segments)
        anchor = pinned_character_instructions(npc_data.get("StringId", ""))
        for i, (who, seg) in enumerate(segments, 1):
            print(f"    [{i}] {'NARR' if who == NARRATOR_VOICE else 'NPC '}: "
                  f"{seg[:70]}")
        _play_segments(segments, voice_id, "", playback_speed, anchor)
        print(f"  [BG] Line done (seq {job['seq']}).")
        return

    # A world event: narrator voice throughout, spoken in sentence-sized pieces
    # so one long description can't become a single stalling call.
    if job.get("kind") in _NARRATION_KINDS:
        what = "LETTER" if job.get("kind") == "letter" else "WORLD EVENT"
        print(f"\n--- READING {what} (seq {job['seq']}) ---")
        text = _normalize_narrator_text(received_text)
        chunks = _split_sentences(text, WORLD_EVENT_CHUNK_CHARS) or [text]
        print(f"  {len(chunks)} piece(s): {text[:90]}...")
        _play_segments([(NARRATOR_VOICE, c) for c in chunks],
                       NARRATOR_VOICE, "", playback_speed)
        print(f"  [BG] {what.capitalize()} done (seq {job['seq']}).")
        return

    # The player's own line: no NPC lookup or JSON recovery needed — just speak it
    # in the player's voice. Queued when the request passed through, so it plays
    # during the gap while the LLM is still generating the reply.
    global _player_audio_pending
    if job.get("kind") == "player":
        print(f"\n--- PLAYING PLAYER LINE (seq {job['seq']}) ---")
        _player_audio_pending = True     # stays true after the job, until stopped
        if VOICE_PLAYER_ACTIONS:
            segments = split_text(received_text)
        else:
            spoken = strip_actions(received_text)
            segments = [(None, spoken)] if spoken else []
        if not segments:
            print("  Nothing to speak.")
            return
        for i, (v, t) in enumerate(segments):
            label = "NARR" if v == NARRATOR_VOICE else "YOU "
            print(f"    [{i+1}] {label}: {t[:70]}{'...' if len(t) > 70 else ''}")
        _play_segments(segments, job.get("voice_id") or get_player_voice(),
                       "", playback_speed)
        print(f"  [BG] Player line done (seq {job['seq']}).")
        return

    # An NPC line is taking over — nothing of the player's is left to silence.
    _player_audio_pending = False

    print(f"\n--- PLAYING (seq {job['seq']}) ---")
    print(f"  Text:  {received_text[:120]}...")
    print(f"  Voice: {voice_id}")
    _capped = _capped_speed(playback_speed)
    if _capped != playback_speed:
        print(f"  Speed: {playback_speed} -> capped to {_capped} (MAX_TTS_SPEED)")
    else:
        print(f"  Speed: {playback_speed}")

    # Decide who is speaking from WHAT was said: find the save file whose recent
    # lines contain this line. The voice id is shared between characters and is
    # only a fallback — see find_speaker_by_text.
    npc_data, npc_path, full_text = find_speaker_by_text(received_text, MATCH_POLL_TIMEOUT)
    speaker_verified = npc_data is not None
    character_anchor = None
    if not speaker_verified:
        npc_data, npc_path = find_npc(received_text, voice_id)

    if npc_data and npc_path:
        npc_gender    = (npc_data.get("Gender", "male")).lower()
        npc_string_id = npc_data.get("StringId", "")

        if not speaker_verified:
            # Wait for the NEW entry to appear in the JSON file, validated against
            # the line the mod actually wants spoken right now (received_text).
            # The text search has already waited for it, so only glance here.
            npc_data, full_text = wait_for_new_entry(
                npc_path, npc_gender, npc_string_id, received_text,
                timeout=FALLBACK_POLL_TIMEOUT if received_text else None)

        if not npc_data:
            print("  Could not read NPC data after polling — falling back")
            full_text        = received_text
            resolved_voice   = voice_id
            npc_instructions = ""
        else:
            text_ok = (not received_text) or (
                bool(full_text) and _texts_match(full_text, received_text))
            speaker_verified = speaker_verified or text_ok
            npc_instructions = npc_data.get("LastTTSInstructions", "")
            if speaker_verified:
                resolved_voice = resolve_voice(voice_id, npc_gender, npc_string_id)
                # The mod's voice id for this character changes between turns; the
                # character doesn't. Keep them on the voice they were first heard with.
                resolved_voice = pin_npc_voice(npc_string_id, npc_data.get("Name"),
                                               resolved_voice, voice_id, npc_gender)
                character_anchor = pinned_character_instructions(npc_string_id)
                print(f"  NPC: {npc_data.get('Name')} | Voice: {VOICE_DB.get(resolved_voice, {}).get('name', resolved_voice)}"
                      f"{' +character' if character_anchor else ''}")
            else:
                # Nothing confirms this is really that character — the voice id is
                # shared. Don't give the line (or pin) that character's voice; use
                # the mod's own voice, and the name won't be announced either.
                voice_gender = VOICE_DB.get(voice_id, {}).get("gender") or npc_gender
                resolved_voice = resolve_voice(voice_id, voice_gender, "")
                print(f"  Speaker unconfirmed (voice match guessed {npc_data.get('Name')}) | "
                      f"Voice: {VOICE_DB.get(resolved_voice, {}).get('name', resolved_voice)}")

            # --- Validation guard ---
            # If we recovered nothing, or what we recovered doesn't match the line
            # the mod asked for (stale/wrong same-voice conversation, e.g. an
            # initiative attack or a lord seeking you out), narrate the mod's own
            # text instead. This can lose recovered *action* asterisks for that one
            # line, but it can never narrate a different past conversation.
            if received_text and not text_ok:
                print("  [GUARD] Recovered text missing or != mod's current line — "
                      "narrating the mod text directly.")
                full_text        = received_text
                npc_instructions = ""  # the instructions belonged to the stale line
                character_anchor = None
    else:
        # Fallback — use received text and voice as-is (no narrator split)
        full_text        = received_text
        resolved_voice   = voice_id
        npc_instructions = ""
        print(f"  Fallback: using received text + voice as-is")

    if not full_text:
        print("  Empty text — nothing to play")
        return

    # Never voice AI Influence's "I am unable to respond / check if Player2 is
    # running" fallback. When Player2's LLM fails the mod sends that as the line;
    # staying silent is far less jarring than a lord reciting a tech-support note.
    if _is_error_text(full_text):
        print("  [SKIP] Text is an LLM-failure fallback message — not narrating.")
        return

    # Strip leaked internal thoughts (the model dumping its "FACT CHECK: STEP 1:"
    # reasoning instead of returning JSON) so the character's private planning is
    # never read aloud.
    if STRIP_INTERNAL_THOUGHTS:
        cleaned, leaked = strip_internal_thoughts(full_text)
        if leaked:
            if cleaned:
                print(f"  [THOUGHTS] Internal-thought leak detected — stripped "
                      f"{len(full_text) - len(cleaned)} chars of reasoning.")
                full_text = cleaned
            elif SKIP_LINE_IF_THOUGHTS_UNSEPARABLE:
                print("  [THOUGHTS] Internal-thought leak detected and dialogue could "
                      "not be separated — staying silent for this line.")
                return
            else:
                print("  [THOUGHTS] Leak detected but unseparable — speaking as-is.")

    # In a group conversation, suppress the narrator: speak the line in the
    # character's own voice with *actions* stripped out, rather than routing the
    # actions to the narrator voice. 1-on-1 conversations are unchanged.
    if not NARRATE_ACTIONS_IN_GROUP and is_group_conversation(npc_data):
        spoken = strip_actions(full_text)
        if not spoken:
            print("  [GROUP] Group conversation; line was only action text — staying silent.")
            return
        print("  [GROUP] Group conversation — narrator suppressed, actions stripped.")
        segments = [(None, spoken)]
    else:
        segments = split_text(full_text)
        # Group conversations only — in a 1-on-1 there is nobody to confuse them with.
        if is_group_conversation(npc_data):
            if speaker_verified:
                segments = announce_speaker(segments, npc_data)
            else:
                print("  [GROUP] Speaker unconfirmed — no name announced rather "
                      "than risk the wrong one.")
        else:
            _reset_announced_speaker()

    print(f"  Segments: {len(segments)}")
    for i, (v, t) in enumerate(segments):
        label = "NARR" if v == NARRATOR_VOICE else "NPC "
        print(f"    [{i+1}] {label}: {t[:70]}{'...' if len(t) > 70 else ''}")

    _play_segments(segments, resolved_voice, npc_instructions, playback_speed,
                   character_anchor)
    print(f"  [BG] Playback done (seq {job['seq']}).")


def _playback_worker():
    """
    Single consumer of the playback queue. Voices lines one at a time in the
    exact order the mod sent them, so group-conversation replies can never be
    spoken before the line they answer, and two lines' audio never overlap.
    """
    print("  [worker] Playback worker started (serialized, in arrival order).")
    while True:
        with _play_cond:
            while not _play_queue:
                _play_cond.wait()
            job = _play_queue.popleft()
        # Optional staleness guard: skip a line that waited too long (a queue
        # left behind after a conversation moved on). Off by default (0).
        if MAX_QUEUE_AGE > 0 and (time.time() - job["ts"]) > MAX_QUEUE_AGE:
            print(f"  [worker] Dropping stale seq {job['seq']} "
                  f"(waited {time.time() - job['ts']:.1f}s > {MAX_QUEUE_AGE}s).")
            continue
        # Start each job with a clean slate, and record what's playing so an
        # arriving NPC reply knows whether it's cutting off a player line.
        _playback_cancel.clear()
        _playback_state["kind"] = job.get("kind")
        _playback_state["seq"] = job.get("seq")
        try:
            _process_job(job)
        except Exception as e:
            print(f"  [worker] Job seq {job.get('seq')} error: {e}")
        finally:
            _playback_state["kind"] = None
            _playback_state["seq"] = None


@app.route('/v1/tts/speak', methods=['POST'])
@app.route('/tts/speak', methods=['POST'])
def tts_speak():
    req_data = request.get_json(silent=True) or {}
    received_text = req_data.get('text', '')
    voice_id = req_data.get('voice_ids', [None])[0]
    playback_speed = req_data.get('speed', 1.0)

    # The NPC's reply is ready. If we're still voicing the player's own line —
    # which only exists to fill the thinking gap — cut it off so the reply starts
    # straight away rather than queueing behind it.
    global _player_audio_pending
    if INTERRUPT_PLAYER_LINE_ON_REPLY and player_lines_enabled():
        playing_now = _playback_state.get("kind") == "player"
        if playing_now or _player_audio_pending:
            why = "still speaking" if playing_now else "audio still playing out"
            print(f"  [interrupt] Reply ready — cutting off the player line ({why}).")
            if playing_now:
                _playback_cancel.set()      # stop queueing further segments
            _stop_player2_audio()           # and silence what's already sounding
            _player_audio_pending = False

    # Enqueue for the single worker and return immediately. The mod shows
    # "Ready to Respond" as soon as it gets this response; the worker voices the
    # line (and every other queued line) strictly in arrival order.
    global _play_seq_counter
    with _play_cond:
        _play_seq_counter += 1
        seq = _play_seq_counter
        _play_queue.append({
            "seq": seq, "text": received_text, "voice_id": voice_id,
            "speed": playback_speed, "ts": time.time(),
        })
        depth = len(_play_queue)
        _play_cond.notify()

    print(f"\n--- TTS REQUEST (queued seq {seq}, depth {depth}) ---")
    print(f"  Text:  {received_text[:120]}...")
    print(f"  Voice: {voice_id}")

    # AI Influence 7.0 asks for the AUDIO rather than asking us to play it
    # (play_in_app false). Answering "ok" with nothing attached would leave the
    # character silent, so say something in the shape it expects.
    if not req_data.get("play_in_app", True):
        if (AUDIO_REPLY_MODE or "background").lower() == "compose":
            # Take the line back off the queue — in this mode WE do not play it,
            # the mod does, from the clip we are about to build. (A deque, so it
            # is rebuilt rather than sliced.)
            with _play_cond:
                keep = [j for j in _play_queue if j.get("seq") != seq]
                _play_queue.clear()
                _play_queue.extend(keep)
            try:
                full, string_id, npc_voice = _recover_line_for_audio(
                    received_text, voice_id)
                mod_note = ((req_data.get("advanced_voice") or {})
                            .get("instructions"))
                print(f"  [compose] building one clip for the mod to play...")
                wav = _compose_line_audio(full, npc_voice, playback_speed,
                                          mod_note, string_id)
                if wav:
                    return jsonify({"data": _as_data_uri(wav)})
                print("  [compose] nothing came back — letting Player2 speak it.")
            except Exception as e:
                print(f"  [compose] failed ({e}) — letting Player2 speak it.")
            # Last resort: let Player2 voice the mod's own request unchanged, so
            # the character is never left mute.
            try:
                r = requests.post(f"{REAL_PLAYER2}/v1/tts/speak", json=req_data,
                                  headers=_game_headers(), timeout=60)
                return Response(r.content, r.status_code,
                                content_type="application/json")
            except Exception as e:
                print(f"  [compose] upstream also failed: {e}")
                return jsonify({"data": _as_data_uri(_silent_wav())})

        # "background": hand back a moment of silence so the mod releases its
        # dialogue lock at once, and let our own worker voice the line while you
        # read ahead and type.
        print(f"  [background] answering with silence; we voice it ourselves.")
        return jsonify({"data": _as_data_uri(_silent_wav())})

    return jsonify({"status": "ok"})


# ============================================================
#  PASSTHROUGH PROXY  (all other routes forwarded to Player2)
# ============================================================

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def proxy(path):
    url = f"{REAL_PLAYER2}/{path}"
    # Forward all original headers except host, then inject game key
    fwd_headers = {k: v for k, v in request.headers if k.lower() != 'host'}
    headers = _game_headers(fwd_headers)

    is_health = path in ("v1/health", "health")
    log_this  = (LOG_CHAT or DEBUG_REQUESTS) and not is_health

    body = request.get_data()
    # A letter is only ever stored in the sender's save file, never spoken — but
    # the mod asks for it through here, so this is the one place it can be
    # caught as it is written.
    is_letter = (request.method == "POST" and "chat/completions" in path
                 and _is_letter_request(body))

    # Voice the player's line now, while the LLM works on the reply.
    if player_lines_enabled() and request.method == "POST" and "chat/completions" in path:
        maybe_voice_player_line(body)

    if log_this:
        req_preview = ""
        try:
            req_preview = body[:600].decode("utf-8", "replace").replace("\n", " ")
        except Exception:
            pass
        print(f"  [PASS>] {request.method} /{path}  req={req_preview[:400]}")

    t0 = time.time()
    try:
        resp = requests.request(
            method=request.method, url=url, headers=headers,
            data=body, params=request.args,
            cookies=request.cookies, stream=True, timeout=PASSTHROUGH_TIMEOUT
        )
    except Exception as e:
        dt = time.time() - t0
        # A timeout/abort here is exactly what makes a slow model look like a
        # total failure to the mod — call it out clearly in the log.
        print(f"  [PASS!] /{path} FAILED after {dt:.1f}s (timeout={PASSTHROUGH_TIMEOUT}s): {e}")
        return jsonify({"error": str(e)}), 500

    excl = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    resp_headers = [(n, v) for n, v in resp.raw.headers.items() if n.lower() not in excl]

    if not log_this and not is_letter:
        return Response(stream_with_context(resp.iter_content(8192)), resp.status_code, resp_headers)

    # Observe the response non-invasively: count bytes, keep a small preview, and
    # log after streaming — never buffering the whole body or blocking the stream.
    status = resp.status_code

    def _gen():
        total = 0
        preview = bytearray()
        # A letter needs the whole reply, not the preview — it is longer than
        # that. Everything else is still passed straight through unbuffered.
        full = bytearray() if is_letter else None
        try:
            for chunk in resp.iter_content(8192):
                total += len(chunk)
                if len(preview) < 1200:
                    preview.extend(chunk[:1200 - len(preview)])
                if full is not None and len(full) < LETTER_MAX_BYTES:
                    full.extend(chunk[:LETTER_MAX_BYTES - len(full)])
                yield chunk
        finally:
            dt = time.time() - t0
            if log_this:
                try:
                    txt = bytes(preview).decode("utf-8", "replace").replace("\n", " ")
                except Exception:
                    txt = "<binary>"
                flag = "  *** EMPTY BODY ***" if total == 0 else ""
                print(f"  [PASS<] /{path} -> {status} in {dt:.1f}s, {total}B{flag}")
                if txt.strip():
                    print(f"           body: {txt[:500]}")
            if full is not None and status == 200:
                try:
                    _capture_letter(bytes(full))
                except Exception as e:
                    print(f"  [letters] Could not capture the letter: {e}")

    return Response(stream_with_context(_gen()), status, resp_headers)


# ============================================================
#  HEALTH PING  (Player2 recommends every 60s for revenue share)
# ============================================================

def _health_ping_loop():
    """Ping /health every 60s so Player2 can track time-spent for revenue share."""
    if not GAME_CLIENT_ID:
        return  # No point pinging without a registered game key
    time.sleep(10)  # Small delay before first ping
    while True:
        try:
            requests.get(f"{REAL_PLAYER2}/v1/health",
                         headers=_game_headers(), timeout=10)
        except Exception:
            pass
        time.sleep(60)


# ============================================================
#  ENTRY POINT
# ============================================================

def _get_console_hwnd():
    """Handle to this process's console window (Windows only)."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        k32.GetConsoleWindow.restype = ctypes.c_void_p
        return k32.GetConsoleWindow()
    except Exception:
        return None


def _show_console(show=True):
    """Show or hide the console window (Windows only)."""
    hwnd = _get_console_hwnd()
    if not hwnd:
        return
    try:
        import ctypes
        user32 = ctypes.windll.user32
        user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
        user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
        SW_HIDE, SW_SHOW = 0, 5
        user32.ShowWindow(hwnd, SW_SHOW if show else SW_HIDE)
        if show:
            user32.SetForegroundWindow(hwnd)
    except Exception:
        pass


def _hide_console_from_taskbar(keep_visible=True):
    """
    Turn the console into a 'tool window' so it no longer appears in the Windows
    taskbar or the alt-tab list — leaving the tray icon as its only presence.
    The window can still be shown/hidden normally from the tray. Windows-only.
    """
    if os.name != "nt":
        return
    hwnd = _get_console_hwnd()
    if not hwnd:
        return
    try:
        import ctypes
        user32 = ctypes.windll.user32
        user32.GetWindowLongW.restype  = ctypes.c_long
        user32.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
        user32.SetWindowLongW.restype  = ctypes.c_long
        user32.SetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_long]
        user32.ShowWindow.argtypes     = [ctypes.c_void_p, ctypes.c_int]
        GWL_EXSTYLE      = -20
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_APPWINDOW  = 0x00040000
        SW_HIDE, SW_SHOW = 0, 5
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = (style | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
        # Window must be hidden while the style changes for the taskbar to update.
        user32.ShowWindow(hwnd, SW_HIDE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        user32.ShowWindow(hwnd, SW_SHOW if keep_visible else SW_HIDE)
    except Exception as e:
        print(f"  [tray] Could not remove console from taskbar: {e}")


def _start_tray():
    """
    Create a system-tray icon so the proxy can run without an open console.
    Returns True if the tray started. Degrades gracefully: if pystray/Pillow
    are missing it prints a hint and runs with the console as normal — it will
    never hide the console unless the tray actually came up.
    """
    try:
        import pystray
        from PIL import Image, ImageDraw
    except Exception as e:
        print(f"  [tray] System tray unavailable ({e}).")
        print(f"  [tray] To enable it: pip install pystray pillow")
        return False

    # Simple icon: purple disc with two light bars (no font dependency).
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([6, 6, 58, 58], fill=(70, 30, 90))
    d.ellipse([6, 6, 58, 58], outline=(205, 150, 245), width=3)
    d.rectangle([25, 22, 30, 42], fill=(235, 215, 250))
    d.rectangle([34, 22, 39, 42], fill=(235, 215, 250))

    state = {"visible": True}

    def on_toggle(icon, item):
        state["visible"] = not state["visible"]
        _show_console(state["visible"])

    def on_show(icon, item):
        state["visible"] = True
        _show_console(True)

    def on_quit(icon, item):
        icon.stop()
        _show_console(True)   # reveal console so it isn't left hidden
        os._exit(0)

    # --- Player voice picker -------------------------------------------------
    # Grouped by accent/gender. Selecting one switches the voice immediately and
    # saves it, so the next line you speak uses it — no restart.
    def _voice_item(vid, name):
        # Closures (not default args) — pystray validates the callable signature
        # and rejects anything taking more than (icon, item).
        def _select(icon, item):
            set_player_voice(vid)

        def _is_current(item):
            return get_player_voice() == vid

        def _is_allowed(item):
            return vid not in banned_voices()

        return pystray.MenuItem(name, _select, checked=_is_current, radio=True,
                                enabled=_is_allowed)

    # Ban a voice you never want to hear again, from anyone. Banning recasts
    # everyone currently pinned to it straight away.
    def _ban_item(vid, name):
        def _toggle(icon, item):
            set_voice_banned(vid, vid not in banned_voices())

        def _is_banned(item):
            return vid in banned_voices()

        return pystray.MenuItem(name, _toggle, checked=_is_banned)

    _group_titles = {
        ("american_english", "male"):   "American male",
        ("american_english", "female"): "American female",
        ("british_english",  "male"):   "British male",
        ("british_english",  "female"): "British female",
    }
    voice_groups = _english_voices()
    voice_submenus = []
    for key in (("american_english", "male"), ("british_english", "male"),
                ("american_english", "female"), ("british_english", "female")):
        entries = voice_groups.get(key) or []
        if entries:
            voice_submenus.append(pystray.MenuItem(
                _group_titles[key],
                pystray.Menu(*[_voice_item(v, n) for v, n in entries])))

    def on_audition(icon, item):
        info = VOICE_DB.get(get_player_voice(), {})
        _enqueue_player_job(f"This is {info.get('name', 'your voice')}. "
                            f"Your character will speak with this voice.")

    def on_toggle_player_lines(icon, item):
        set_player_lines_enabled(not player_lines_enabled())

    player_menu = pystray.Menu(
        pystray.MenuItem("Voice my lines", on_toggle_player_lines,
                         checked=lambda item: player_lines_enabled()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            lambda item: f"Current: {VOICE_DB.get(get_player_voice(), {}).get('name', '?')}",
            None, enabled=False),
        *voice_submenus,
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Test current voice", on_audition),
    )

    # --- Character voices ---------------------------------------------------
    # Each character is pinned to the first voice they were heard with, because
    # the mod sends a different voice id for them from turn to turn. Forgetting
    # the pins re-casts everyone from whatever they next speak with.
    def on_forget_pins(icon, item):
        forget_npc_voice_pins()

    npc_voice_menu = pystray.Menu(
        pystray.MenuItem(
            lambda item: f"Pinned characters: {len(_load_npc_voice_pins())}",
            None, enabled=False),
        pystray.MenuItem("Forget pinned voices", on_forget_pins),
    )

    ban_submenus = []
    for key in (("american_english", "male"), ("british_english", "male"),
                ("american_english", "female"), ("british_english", "female")):
        entries = voice_groups.get(key) or []
        if entries:
            ban_submenus.append(pystray.MenuItem(
                _group_titles[key],
                pystray.Menu(*[_ban_item(v, n) for v, n in entries])))

    banned_menu = pystray.Menu(
        pystray.MenuItem(
            lambda item: (f"Banned: "
                          + (", ".join(sorted(VOICE_DB.get(v, {}).get("name", "?")
                                              for v in banned_voices()))
                             or "none")),
            None, enabled=False),
        pystray.Menu.SEPARATOR,
        *ban_submenus,
    )

    # --- Speech speed -------------------------------------------------------
    # Ours, not the mod's: the MCM slider's stored value never leaves normal.
    # A pick applies to the next line spoken and is remembered across restarts.
    # The characters move the full amount; the narrator follows part of the way.
    def _speed_item(name, value):
        def _select(icon, item):
            set_tts_speed(value)

        def _is_current(item):
            return abs((tts_speed() or TTS_SPEED_DEFAULT) - value) < 0.03

        return pystray.MenuItem(name, _select, checked=_is_current, radio=True)

    def on_speed_reset(icon, item):
        set_tts_speed(TTS_SPEED_DEFAULT)

    speed_menu = pystray.Menu(
        pystray.MenuItem(
            lambda item: f"Now: {speed_name(tts_speed() or TTS_SPEED_DEFAULT)}",
            None, enabled=False),
        pystray.Menu.SEPARATOR,
        *[_speed_item(n, v) for n, v in TTS_SPEED_PRESETS if v <= MAX_TTS_SPEED],
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Back to normal", on_speed_reset),
    )

    menu = pystray.Menu(
        pystray.MenuItem("TTS Narrator Proxy", None, enabled=False),
        pystray.MenuItem("Show / hide console", on_toggle, default=True),
        pystray.MenuItem("Show console", on_show),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Speech speed", speed_menu),
        pystray.MenuItem("Player voice", player_menu),
        pystray.MenuItem("Character voices", npc_voice_menu),
        pystray.MenuItem("Banned voices", banned_menu),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", on_quit),
    )
    icon = pystray.Icon("tts_narrator", img, "TTS Narrator Proxy", menu)
    threading.Thread(target=icon.run, daemon=True).start()
    print("  [tray] System-tray icon active — left-click it to show/hide, "
          "right-click for Quit.")

    # Give the startup banner a moment to print, then (optionally) detach the
    # console from the taskbar and/or tuck it away.
    def _finalize_window():
        time.sleep(1.0)
        if HIDE_FROM_TASKBAR:
            _hide_console_from_taskbar(keep_visible=not START_MINIMIZED)
            print("  [tray] Console removed from taskbar (tray icon only).")
        elif START_MINIMIZED:
            _show_console(False)
        if START_MINIMIZED:
            state["visible"] = False
    threading.Thread(target=_finalize_window, daemon=True).start()
    return True


class _Tee:
    """Write to the console AND a log file, prefixing each line with a timestamp
    in the file copy. The console copy is left untouched."""
    def __init__(self, stream, fh):
        self._stream = stream
        self._fh = fh
        self._newline = True

    def write(self, text):
        if self._stream:
            try:
                self._stream.write(text)
            except Exception:
                pass
        ts = time.strftime("%H:%M:%S")
        out = []
        for ch in text:
            if self._newline and ch not in ("\n", "\r"):
                out.append(f"[{ts}] ")
                self._newline = False
            out.append(ch)
            if ch == "\n":
                self._newline = True
        try:
            self._fh.write("".join(out))
            self._fh.flush()
        except Exception:
            pass

    def flush(self):
        for s in (self._stream, self._fh):
            try:
                if s:
                    s.flush()
            except Exception:
                pass


def _install_file_logging():
    """Mirror stdout/stderr to LOG_FILE. Safe no-op on any failure."""
    if not LOG_TO_FILE:
        return
    try:
        path = LOG_FILE.strip() or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "proxy_log.txt")
        mode = "a"
        try:
            if os.path.exists(path) and os.path.getsize(path) > LOG_MAX_BYTES:
                mode = "w"  # start fresh once it gets large
        except OSError:
            pass
        fh = open(path, mode, encoding="utf-8")
        fh.write("\n" + "=" * 60 + "\n"
                 + time.strftime("%Y-%m-%d %H:%M:%S") + "  --- proxy started ---\n")
        fh.flush()
        sys.stdout = _Tee(getattr(sys, "stdout", None), fh)
        sys.stderr = _Tee(getattr(sys, "stderr", None), fh)
        print(f"  Logging to: {path}")
    except Exception as e:
        print(f"  [log] Could not open log file: {e}")


# ============================================================
#  CALIBRATION  (TTS_NARRATOR.py --calibrate)
#  Measure how fast Player2 actually speaks, instead of guessing.
#  play_in_app:false makes Player2 return the mp3 rather than play it, so this
#  is silent and the audio can be measured exactly.
# ============================================================

def _mp3_duration(raw):
    """
    Duration of an MPEG audio stream, by summing frame durations. Player2
    returns MPEG audio, and every frame header carries the bitrate and sample
    rate needed to find the next one, so this needs no audio library.
    """
    bitrates = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
    rates = [44100, 48000, 32000, 0]
    i, total = 0, 0.0
    if raw[:3] == b"ID3":                      # skip an ID3v2 tag if present
        i = 10 + ((raw[6] & 0x7F) << 21 | (raw[7] & 0x7F) << 14 |
                  (raw[8] & 0x7F) << 7 | (raw[9] & 0x7F))
    while i + 4 <= len(raw):
        if raw[i] != 0xFF or (raw[i + 1] & 0xE0) != 0xE0:
            i += 1
            continue
        bitrate = bitrates[(raw[i + 2] >> 4) & 0xF] * 1000
        rate = rates[(raw[i + 2] >> 2) & 0x3]
        if not bitrate or not rate:
            i += 1
            continue
        total += 1152.0 / rate
        i += max(1, int(144 * bitrate / rate) + ((raw[i + 2] >> 1) & 1))
    return total


def _calibration_sample(text, voice, instructions):
    """One silent TTS call. Returns (generation seconds, audio seconds)."""
    payload = {"text": text, "play_in_app": False, "speed": 1.0,
               "voice_ids": [voice]}
    if instructions:
        payload["advanced_voice"] = {"instructions": instructions}
    for _ in range(3):
        try:
            t0 = time.time()
            resp = requests.post(f"{REAL_PLAYER2}/v1/tts/speak", json=payload,
                                 headers=_game_headers(), timeout=120)
            gen = time.time() - t0
            if resp.status_code == 200:
                b64 = "".join((resp.json().get("data") or "").split())
                b64 += "=" * (-len(b64) % 4)
                audio = base64.b64decode(b64)
                if audio:
                    return gen, _mp3_duration(audio)
        except Exception as e:
            print(f"      retrying after {type(e).__name__}: {e}")
        time.sleep(4.0)
    return None, None


_CAL_TEXTS = [
    "Steps forward, eyes sweeping over the knights.",
    "Speak plainly, then. I have little patience for riddles.",
    ("Welcome to Cape Wrath, Ser Osbert, Ser Harlan. In these dark times, a "
     "loyal blade is as precious as a summer rain. My son speaks highly of "
     "your courage, and I trust his judgment."),
    ("A roof is only as good as the walls that hold it, and a lord's word is "
     "the foundation. I have seen the Rainwood's shadows; they do not frighten "
     "me, but they bear watching. My blade is sharp and my oath is set."),
]


def run_calibration(reps=2):
    """
    Measure the speech rate on this machine's own voices and save it. Also
    reports what the accent anchor costs in generation time, since every call
    yields both numbers anyway.
    """
    print("=" * 62)
    print("  Speech-rate calibration")
    print("=" * 62)
    try:
        requests.get(f"{REAL_PLAYER2}/v1/health", timeout=5).raise_for_status()
    except Exception as e:
        print(f"  Player2 is not reachable at {REAL_PLAYER2} ({e}).")
        print("  Start the Player2 app and try again.")
        return

    # One voice per accent, so the rate isn't measured on a single voice.
    voices, seen = [], set()
    for vid, info in VOICE_DB.items():
        lang = info.get("lang", "")
        if lang in ("american_english", "british_english") and lang not in seen:
            seen.add(lang)
            voices.append((info.get("name", vid), vid))
    print(f"  Voices : {', '.join(n for n, _ in voices)}")
    print(f"  Silent — play_in_app is off, so nothing is spoken aloud.")
    print(f"  About {len(voices) * len(_CAL_TEXTS) * reps * 2} calls; "
          f"this takes a few minutes.\n")

    rates, plain, anchored, failures = [], [], [], 0
    for vname, vid in voices:
        anchor = voice_accent_instructions(vid) or None
        for text in _CAL_TEXTS:
            for label, instr in (("bare", None), ("anchor", anchor)):
                gens, durs = [], []
                for _ in range(reps):
                    gen, dur = _calibration_sample(text, vid, instr)
                    if gen is None or not dur:
                        failures += 1
                        continue
                    gens.append(gen)
                    durs.append(dur)
                if not durs:
                    continue
                gen = sorted(gens)[len(gens) // 2]
                dur = sorted(durs)[len(durs) // 2]
                cps = len(text) / dur
                (plain if label == "bare" else anchored).append(gen)
                if label == "anchor":
                    rates.append(cps)       # the proxy always sends the anchor
                print(f"    {vname:<10} {label:<7} {len(text):4}ch  "
                      f"gen={gen:6.2f}s  audio={dur:6.2f}s  {cps:5.2f} ch/s")

    if not rates:
        print("\n  No usable samples — Player2 refused every request.")
        return
    rates.sort()
    slowest, median = rates[0], rates[len(rates) // 2]
    # Trim the slowest few before choosing. Player2 occasionally renders a line
    # far slower than it ever will again - in the first calibration a 46-char
    # line came back at 10.35 ch/s when the same text had measured 18.30 moments
    # earlier. Anchoring on that single sample recommended 9.8, which would have
    # been slower than the un-measured guess it replaced. Take the slowest that
    # SURVIVES trimming, then a small margin under it.
    trim = int(len(rates) * 0.15) if len(rates) >= 5 else 0
    floor_rate = rates[trim]
    recommended = round(floor_rate * 0.97, 1)
    print("\n" + "=" * 62)
    print(f"  speech rate  slowest={slowest:.2f}  median={median:.2f}  "
          f"fastest={rates[-1]:.2f} ch/s  ({len(rates)} samples)")
    if trim:
        print(f"  discarded the {trim} slowest as outliers; "
              f"using {floor_rate:.2f} ch/s as the floor")
    if plain and anchored:
        p = sorted(plain)[len(plain) // 2]
        a = sorted(anchored)[len(anchored) // 2]
        print(f"  accent anchor costs {(a - p) / p * 100:+.0f}% generation time "
              f"({p:.2f}s -> {a:.2f}s median)")
    if failures:
        print(f"  {failures} call(s) failed and were skipped.")
    if recommended < SPEECH_CHARS_PER_SECOND * 0.75:
        print(f"  Measured {recommended:.1f} ch/s, well below the built-in "
              f"{SPEECH_CHARS_PER_SECOND:.1f} — that usually means Player2 was "
              f"struggling, not that speech is slow.")
        print(f"  Not saving. Re-run when Player2 is healthy.")
        print("=" * 62)
        return
    print(f"  Recommended SPEECH_CHARS_PER_SECOND: {recommended:.1f} "
          f"(currently using {speech_rate():.1f})")
    try:
        with open(SPEECH_RATE_FILE, "w", encoding="utf-8") as f:
            f.write("# Measured speech rate, characters per second.\n")
            f.write("# Written by TTS_NARRATOR.py --calibrate; overrides\n")
            f.write("# SPEECH_CHARS_PER_SECOND with no restart needed.\n")
            f.write(f"# measured {time.strftime('%Y-%m-%d %H:%M')}  "
                    f"slowest={slowest:.2f} floor={floor_rate:.2f} "
                    f"median={median:.2f} n={len(rates)}\n")
            f.write(f"{recommended:.1f}\n")
        print(f"  Saved to {os.path.basename(SPEECH_RATE_FILE)} — "
              f"the running proxy picks it up on its next line.")
    except Exception as e:
        print(f"  Could not write {SPEECH_RATE_FILE}: {e}")
    print("=" * 62)


if __name__ == '__main__':
    if "--calibrate" in sys.argv:
        run_calibration()
        raise SystemExit(0)

    _install_file_logging()
    print("=" * 60)
    print("  Player2 TTS Narrator Proxy  —  v3.9")
    print("  Created by REGGIE")
    print("=" * 60)
    print(f"  Narrator : Ethan ({NARRATOR_VOICE})")
    if player_lines_enabled():
        _pv = VOICE_DB.get(get_player_voice(), {})
        print(f"  Your lines: ON — {_pv.get('name')} ({_pv.get('gender')}, "
              f"{_pv.get('lang')})  — change from the tray icon")
    else:
        print("  Your lines: OFF (saves TTS) — enable from the tray icon")
    print(f"  Proxy URL: http://127.0.0.1:{PROXY_PORT}")
    print(f"  NPC Folder: {get_npc_folder()}")
    print(f"  Segment pause: {PAUSE}s")
    print(f"  Speech rate: {speech_rate():.1f} ch/s"
          + ("" if _speech_rate else "  (default — run --calibrate to measure)"))
    _dial = tts_speed()
    if _dial is not None:
        print(f"  Speech speed: {speed_name(_dial)} — change from the tray icon "
              f"(\"Speech speed\"); the narrator follows part of the way")
    else:
        print("  Speech speed: normal (not set) — change from the tray icon "
              "(\"Speech speed\")")
    if GAME_CLIENT_ID:
        print(f"  Game Client ID: {GAME_CLIENT_ID[:8]}... (your own key)")
        threading.Thread(target=_health_ping_loop, daemon=True).start()
        print("  Health ping: every 60s (active)")
    else:
        print("  Auth: using local Player2 app session (no game key)")
    print()
    if TAKEOVER_MODE:
        # With the takeover on, Player2 is NOT where we are listening — say so
        # plainly if it cannot be reached, because every line depends on it and
        # the symptom in game (silent characters) looks like the mod's fault.
        try:
            _p2 = requests.get(f"{TAKEOVER_UPSTREAM}/v1/health", timeout=5)
            _p2_ok = _p2.status_code == 200
        except Exception:
            _p2_ok = False
        if not _p2_ok:
            print("  *** Player2 is not answering at " + TAKEOVER_UPSTREAM + " ***")
            print("  Start the Player2 app, then restart this proxy. Until then")
            print("  characters will be silent, and it will look like the mod.")
        print("  TAKEOVER MODE — for AI Influence 7.0 and later.")
        print(f"  Holding {TAKEOVER_LISTEN}:{TAKEOVER_PORT} (the address the mod "
              f"uses), forwarding to Player2 at {TAKEOVER_UPSTREAM}.")
        print(f"  The mod's own URL setting is ignored by 7.0 and does not matter.")
        print(f"  Spoken lines: {AUDIO_REPLY_MODE}"
              + ("  (we play them, so you can read ahead)"
                 if AUDIO_REPLY_MODE == "background"
                 else "  (one clip handed to the mod to play)"))
    elif WATCH_MODE:
        print("  WATCH MODE — the mod is left completely alone.")
        print("  Lines are read from the save folder as they are written and")
        print("  spoken here, so nothing we do can stop characters talking.")
        print("  *** Turn the mod's own TTS OFF, or every line is spoken twice. ***")
    else:
        print("  Set this URL in AI Influence MCM settings:")
        print(f"  >>> http://127.0.0.1:{PROXY_PORT} <<<")
    print("=" * 60)
    if USE_TRAY:
        _start_tray()
    # Single playback worker — voices all lines in strict arrival order.
    threading.Thread(target=_playback_worker, daemon=True).start()
    _start_world_event_hotkey()
    if WATCH_MODE:
        threading.Thread(target=_watch_loop, daemon=True).start()
    # In takeover mode we must bind the ONE address the mod talks to, not every
    # address: binding the wildcard would collide with Player2 instead of
    # slipping in front of it for that address only.
    if TAKEOVER_MODE:
        app.run(host=TAKEOVER_LISTEN, port=TAKEOVER_PORT, debug=False)
    else:
        app.run(port=PROXY_PORT, debug=False)