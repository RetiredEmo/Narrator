"""
NARRATOR — a narrator for AI Influence 7.0 and later.

Why this exists, and why it is not the old proxy
------------------------------------------------
Up to 6.x the proxy sat between the mod and Player2 and voiced everything. 7.0
closed that door: it talks to Player2 as a *verified mod* and refuses the
connection as soon as anything else is bound to that address — proven with a
relay that copied bytes and changed nothing (2026-11-11). It also got good. It
assigns each character a voice, and it writes a fresh delivery note for every
single line, which is better direction than the fixed anchors we used to send.

So this program does not stand in the way of any of that. It watches the save
folder, and when a character says something new it speaks the part the mod
throws away — the *actions* — in the narrator's voice, and the words in the
character's, directed by the mod's own note for that line.

Three things make it sound better than the old proxy did:

  * The dialogue is generated as ONE piece. Chopping a speech into chunks made
    each chunk a separate performance, with seams between them.
  * The character's line carries the mod's own per-line instruction, not our
    one-size-fits-all accent anchor.
  * The narrator's action and the character's speech are fetched AT THE SAME
    TIME. The action is short and arrives first, so it starts playing while the
    long line is still generating: one short wait instead of a long one, and no
    need to chop anything for the sake of speed.

Turn the mod's own TTS off, or every line is spoken twice.
"""

import array
import io
import collections
import json
import math
import os
import re
import sys
import threading
import time
import wave

# The voice table, the text splitting and the settings all already exist and are
# well tested; this program is a new front end on them, not a second copy.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import TTS_NARRATOR as core

# ============================================================
#  SETTINGS
# ============================================================

# How often to look for a new line.
POLL_SECONDS = 0.15
# OFF (0) since 2026-11-12, on quality grounds. It worked — splitting a line's
# opening sentence off got the voice started in about three seconds instead of
# nine — but a piece generated on its own cannot know how the piece before it
# was delivered, so the pacing and depth within a line suffered. We compared
# split and whole by ear and the whole line won; quality outranks the wait.
#
# A line that opens with an *action* still starts quickly with no split at all,
# because the action IS a short first piece and everything is fetched at once.
# Set to about 170 to trade that back for speed.
QUICK_OPENING_CHARS = 0
# --- Keeping up with a group conversation (2026-11-22) ---
# A line's audio took about 11 s to make and only began when the line before
# had finished playing, so every line cost make + play and a busy group scene
# drifted further behind with each exchange. Now the next lines are made WHILE
# the current one plays: only the first line of a scene has the wait.
# How many waiting lines to make ahead (0 = the old one-at-a-time behaviour).
PREFETCH_LINES = 3
# In GROUP scenes only, the first stretch of a character's speech (about this
# many characters, ending on a sentence) is made on its own, so the voice is
# ready in a few seconds and plays straight after the announcement and action
# while the rest is still being made (2026-11-22: speech arrived far
# faster than the voice). Both halves share one delivery note, as a long speech
# split in parts already does. One-on-one talk keeps whole lines (the quality
# we chose). 0 turns it off.
QUICK_OPENING_IN_GROUPS = 170
# Still behind? With this many lines waiting after the one starting now, the
# line is played a little faster (pitch untouched) and the "who is speaking"
# announcement is skipped, until the narrator is level again. Nothing is ever
# dropped. CATCH_UP_SPEED 1.0 turns the speed-up off.
CATCH_UP_AT = 2
CATCH_UP_SPEED = 1.15
CATCH_UP_SKIPS_ANNOUNCE = True
# --- Background characters (2026-11-22) ---
# A tavern maid, a guard, a merchant the scene makes up has no file of its own
# (its id reads "scene_agent_N"), so its lines were never heard. Every real
# character who hears one writes the line into THEIR history, so it is picked up
# from there - once, however many listeners recorded it. The game does not say
# their gender: it is judged from the title (FEMALE_TITLE_WORDS), else male.
VOICE_BACKGROUND_CHARACTERS = True
FEMALE_TITLE_WORDS = ("maid", "wife", "woman", "girl", "lady", "widow", "mother",
                      "sister", "daughter", "matron", "septa", "whore", "wench",
                      "mistress", "queen", "princess", "crone", "nun", "aunt",
                      "grandmother", "lass", "barmaid", "alewife", "milkmaid",
                      "washerwoman", "fishwife", "seamstress", "priestess")
# Speak what was already in the save files when this started. Off, so restarting
# mid-conversation does not read the backlog at you.
SPEAK_BACKLOG = False
# Use the mod's own delivery note for the character's words. This is the whole
# point: it writes a new one for every line and they are better than ours.
# False falls back to our constant per-voice anchor.
USE_MOD_DELIVERY_NOTE = True

# AI Influence 7.1.0 stopped asking its AI for the per-line voice note
# (`tts_instructions`) while the mod's own TTS is switched off - and it must
# be off, or every line is spoken twice. Without those notes every line fell
# back to notes we write from the outside, which are a guess; on 2026-11-24 a
# folksy speech description turned one into a Southern drawl. The request is
# still in the campaign's prompt files (json_output\JsonOutputTtsInstructions
# .txt); the mod only leaves it out. On: the narrator adds that one request to
# json_output\JsonOutputExpressionField.txt - the `emotion` field, sent with
# every spoken reply - so the AI that writes the line writes its note again.
# (First tried in JsonOutputVolumeField.txt: that one is NOT in every prompt -
# Harras Harlaw's, a prisoner on the map, had no volume field at all. The old
# line is taken back out of it.) The mod reads its prompt files when the
# campaign loads, so a first-time addition counts from the next load. The mod logs every reply the moment
# it arrives, and the note is picked up from there (see ModLogFollower).
# Checked every few seconds, so a new campaign or an AI Influence update that
# regenerates the file gets it back by itself. Off: nothing is touched.
ASK_MOD_FOR_NOTES = True

# When you start typing in a conversation, AI Influence stops the character's
# line on screen. On: their voice stops too. Off (chosen 2026-11-26): the voice
# finishes the line it was speaking; anything queued after it still plays.
STOP_VOICE_WHEN_YOU_TYPE = False
NOTE_PROMPT_FILE = os.path.join("prompts", "json_output", "JsonOutputExpressionField.txt")
NOTE_PROMPT_OLD_FILES = [os.path.join("prompts", "json_output", "JsonOutputVolumeField.txt")]
NOTE_PROMPT_LINE = ("- `tts_instructions`: (string) **REQUIRED** \u2014 20\u2013200 "
                    "characters, in the same language as `response`. Describe "
                    "voice mood, emotion, pace, and delivery style only. Never "
                    "name an accent, a dialect, or a region's or people's way of "
                    "speaking, and never call the speech plain, rustic or folksy.")
# Earlier wordings of our line, replaced in place when found (2026-11-26).
NOTE_PROMPT_OLD_LINES = [
    "- `tts_instructions`: (string) **REQUIRED** \u2014 20\u2013200 characters, in the same "
    "language as `response`. Describe voice mood, emotion, pace, and delivery style.",
]
# How long a line waits for its note to show up in the mod's log, once notes
# have been seen there at all. The reply is logged before the line is shown,
# so this is nearly always nothing.
MOD_NOTE_LOG_WAIT = 1.5


def _take_note_line_out(path):
    """Remove our own line (only ours, exactly) from a file we used to put it in."""
    try:
        if not os.path.isfile(path):
            return
        raw = core._read_shared_bytes(path)
        text = raw.decode("utf-8-sig")
        if NOTE_PROMPT_LINE not in text:
            return
        nl = "\r\n" if "\r\n" in text else "\n"
        kept = [l for l in text.split(nl) if l.strip() != NOTE_PROMPT_LINE]
        with open(path, "w", encoding="utf-8-sig" if raw.startswith(b"\xef\xbb\xbf")
                  else "utf-8", newline="") as f:
            f.write(nl.join(kept))
    except Exception as e:
        print(f"  [notes] Could not tidy {os.path.basename(path)}: {e}")


def ensure_note_prompt(folder):
    """Put the note request back into this campaign's prompts if it is missing."""
    if not (ASK_MOD_FOR_NOTES and folder):
        return
    for old in NOTE_PROMPT_OLD_FILES:
        _take_note_line_out(os.path.join(folder, old))
    path = os.path.join(folder, NOTE_PROMPT_FILE)
    if not os.path.isfile(path):
        return                  # the mod writes its defaults when the campaign loads
    try:
        raw = core._read_shared_bytes(path)
        bom = raw.startswith(b"\xef\xbb\xbf")
        text = raw.decode("utf-8-sig")
        if NOTE_PROMPT_LINE in text:
            return
        replaced = False
        for old in NOTE_PROMPT_OLD_LINES:
            if old in text:
                text = text.replace(old, NOTE_PROMPT_LINE)
                replaced = True
        if replaced:
            with open(path, "w", encoding="utf-8-sig" if bom else "utf-8",
                      newline="") as f:
                f.write(text)
            print("  [notes] Updated the voice-note request (no accents or dialects).")
            return
        if "tts_instructions" in text:
            return
        crlf = "\r\n" in text
        nl = "\r\n" if crlf else "\n"
        text = text.rstrip("\r\n") + nl + NOTE_PROMPT_LINE + nl
        with open(path, "w", encoding="utf-8-sig" if bom else "utf-8",
                  newline="") as f:
            f.write(text)
        print("  [notes] Asked AI Influence for its voice note on every line "
              "again (added to its prompt).")
    except Exception as e:
        print(f"  [notes] Could not add the voice-note request: {e}")
# The mod's note says how to perform a line but never says to be faithful to
# the words, and this TTS is generative: left to itself it will sometimes
# reword, swap or swallow something. Our own narrator instruction has always
# demanded word-for-word reading, which is why that never used to happen. This
# clause restores it for the characters too, without touching the mod's
# direction, which is what makes them sound good. "" to send the note alone.
# Kept SHORT on purpose. The long version of this ("read the text exactly as
# written, word for word: add nothing, leave nothing out...") flattened the
# delivery: this voice performs its instruction as much as it obeys it, and a
# clerical order sitting after "speak with a measured, dry tone" made the
# character read like a clerk. We compared them by ear on 2026-11-12 and this
# one held the performance while the long one did not.
# Firm and specific since 2026-11-24: the voice is generative and was swapping
# in words of its own on correctly written lines; one soft "keep every word"
# at the end of a direction about acting read as optional. Kept short - a long
# direction costs generation time - and sent with EVERY character line now,
# not only the ones that had a note.
KEEP_WORDS_EXACT = ("Say exactly the words of the text, in order: add nothing, "
                    "drop nothing, change nothing, and say unfamiliar names as "
                    "spelled.")
# Every direction we send for a character opens with the SAME sentence about
# who is speaking, byte for byte, for the whole session and the next one.
#
# This is the oldest lesson in the file and it had to be learned twice. A
# generative voice free-runs on whatever it is told, so a direction that
# describes the voice itself - "a high-pitched sneer", "silky", "cold and
# melodic", and the log of 2026-11-16 is full of those - recasts the speaker
# on every line. The per-voice anchor existed to stop exactly that, and the
# note work of 2026-11-16 quietly dropped it: the written note became the
# ENTIRE direction, so nothing said who the person was any more.
#
# Now the anchor is first and the per-line note second, so the note colours a
# fixed person instead of inventing one. Everything else we send - the
# fidelity clause, the continuation clause for a speech read in parts - hangs
# off the same assembler, in the same order, every time.
VOICE_ANCHOR = True
# Speed for the character's words. None follows your own dial, the same one in
# the tray menu that the narrator uses.
#
# This was pinned at normal on 2026-11-12, on the grounds that speed changes
# cost quality — but that left the dial doing nothing at all for characters,
# so the fastest setting sounded like normal, which is exactly what was
# reported on 2026-11-16. Two things had stacked up by then: the pinning, and
# the new part-by-part reading, which is measurably FULLER than one long
# generation (the same words took noticeably longer to say). Together they made
# characters crawl.
#
# So the dial governs everyone again. If a character ever sounds rushed at the
# top of the dial, the fix is a number here, not a pinning: put a figure in and
# characters hold that pace whatever the dial says.
CHARACTER_SPEED = None
# Announce who is speaking in group scenes (narrator, before their first line).
ANNOUNCE_IN_GROUPS = True
# Only read conversations YOU are part of.
#
# 7.0 has lords hold their own conversations near you — with each other and
# with townsfolk — and those land in the save files exactly like a conversation
# with you. Reading them meant hearing both sides of other people's chatter,
# out of step with the scene, on top of the mod's own ambient voices. The mod
# speaks ambient talk perfectly well itself, so we leave it to the mod.
#
# --- Overhearing other people ---
# 7.0 tags every scene in the save file: "dialog:" and "dialog/initiative:" are
# conversations with you, "group:" is a group scene, "ambient:" is two other
# people talking near you. That tag is used rather than guessed at.
#
# Ambient talk is narrated like anything else, but quieter — the feeling of
# overhearing rather than being spoken to. Turn the mod's "Enable Ambient NPC
# TTS" OFF when this is on, or every line is said twice.
NARRATE_AMBIENT = True
# How loud overheard talk is against your own conversations. We cannot know how
# far away the speakers are — nothing in the save says where anyone is standing,
# and the mod only tells us who spoke — so this is one fixed "across the room"
# level rather than true distance.
AMBIENT_VOLUME = 0.40
# Never overhear while you are in a conversation of your own: it is your scene
# that matters. A conversation counts as yours for this long after its last
# line, so a pause while you type does not let the room start talking over you.
IN_CONVERSATION_SECONDS = 40
# A line from someone YOU are talking to cuts off whatever is being overheard.
AMBIENT_YIELDS_TO_YOU = True
# A banned voice is never used, even when the mod picks it — this is what keeps
# the British voices out after they came through as cockney.
HONOUR_BANNED_VOICES = True
# A character is never given a voice of the wrong gender, whoever chose it.
MATCH_VOICE_TO_GENDER = True
# Keep the narrator's voice for the narrator. If a character is given it too,
# the asides and the speech become indistinguishable — you cannot tell who is
# talking. The old proxy reserved it; this one must as well.
RESERVE_NARRATOR_VOICE = True

PLAYER2 = "http://127.0.0.1:4315"
# A port of our own, used only as a "one narrator at a time" claim. Nothing
# listens on it in any useful sense, and it is nowhere near Player2's.
SINGLE_INSTANCE_PORT = 4399

# --- Reading the world events aloud ---
# Press the key for the newest day's events; press again while it is reading to
# cut it off and move to the day before. Events from one day are read oldest
# first, so a cause is heard before its consequence.
READ_EVENTS = True
EVENT_HOTKEY = "numpad+"
# Long readings are broken up the same way a long speech is: a short opening
# piece so the voice starts quickly, then larger pieces, all fetched at once.
EVENT_OPENING_CHARS = 170
EVENT_CHUNK_CHARS = 450
# A long reading (a day of events, a letter, a Memory Book page) is made only
# this many pieces ahead of the one playing - not all at once. Each piece takes
# far less time to make than to hear, so it still flows without a gap, but a
# reading you cut off stops being paid for there, and one piece that gets stuck
# no longer costs the whole passage. Until 2026-11-24 every piece was asked for
# the moment the key was pressed: a long 7.1 book page was paid for in full,
# then went silent after its opening when one request hung.
READING_AHEAD = 2
# A piece this late is asked for again; whichever copy comes first is played.
READING_STUCK_SECONDS = 25.0

# --- Letters ---
# 7.0 writes a letter into the sender's history exactly like something they
# said, which means it gets read out the moment it lands. That is not wanted:
# a letter should be read when YOU ask for it. Each letter also leaves a
# delivery record carrying the very line it wrote, so letters can be told from
# speech exactly rather than guessed at.
READ_LETTERS = True
LETTER_HOTKEY = "numpad-"
# Letters are never spoken as they arrive; press the key for the newest, again
# for the one before. True puts them back in the flow of the conversation.
SPEAK_LETTERS_ON_ARRIVAL = False
# Say who wrote it before reading it.
ANNOUNCE_SENDER = True

# --- How a line is to be performed ---
# This is the whole difference between our speech and the mod's own, found
# 2026-11-16 by reading the save files: the mod asks the AI for a performance
# note with EVERY line it generates ("Deep, gravelly, thunderous. Deliver with
# sadistic triumph...") and sends it with the words. We were sending, as the
# entire direction, "Neutral American English accent." Same engine, same voice,
# same words — and night and day to listen to.
#
# The note the mod asks for is only WRITTEN DOWN when the mod itself speaks the
# line, so with its TTS off (which watch mode requires) it is almost never
# there: 3 characters out of 97 had one. So we ask for our own, the same way the
# mod does. Nothing is intercepted and the mod is not touched.
#
# A note is built in three tiers, best first:
#   1. the mod's own note, when it happens to have written one for THIS line
#   2. a note written for this line by the same AI the mod uses (2-3 seconds)
#   3. a note composed here from what the save already knows — the character's
#      speech quirks, the AI's own one-word emotion for the line, their mood and
#      what caused it. Costs nothing and is ready at once.
# Tier 3 is always ready, so a slow or missing AI never leaves a line unspoken:
# it is spoken with the composed note instead.
WRITE_OWN_NOTES = True
# How long a character's words wait for tier 2 before going with tier 3.
# Measured on eight real lines from the live save: fastest under three seconds,
# usually four or five, worst case eight. So this is set past the worst case,
# because the wait is nearly always hidden and a flat line is not worth saving
# a second or two.
#
# It is hidden twice over. A note is asked for the MOMENT the line appears in
# the save file, not when its turn comes, so it is written while the line
# before it is still being spoken; and within a line, while the narrator's
# action is generated and played first.
NOTE_WAIT_SECONDS = 9.0
# Remember notes already written, so a line heard twice is not paid for twice.
NOTE_MEMORY = 400
# How long one character keeps the same note, in seconds. 0 writes a new one
# for every line.
#
# A note written per line means the DIRECTION changes every line - weary
# patience, then cold precision, then silky grace - and a generative voice
# performs its direction as much as it obeys it, so the speaker keeps being
# recast however firmly the anchor holds the pitch and accent. Within one
# conversation the performance should hold and move with the scene, not with
# the sentence. So a character's note is reused while their MOOD is the mood
# it was written under: a real turn in the conversation moves the mood, and
# that writes a new note.
NOTE_HOLD_SECONDS = 240.0
# What the note is allowed to know about the moment the line is spoken in.
#
# This is the last real difference from the mod (2026-11-16): the mod's note is
# written by the same AI call that WRITES the line, so it has the whole scene in
# front of it — above all the character's own reasoning, which the mod stores as
# `internal_thoughts` ("the player's request to 'Repeat' is interpreted as a
# dismissive demand... Melisandre responds with a mixture of..."). A note
# written from the words alone cannot know that the line is meant as an insult
# answered with contempt. Both of these are already in the save file, so this
# costs nothing but the sending.
NOTE_SEES_THOUGHTS = True       # the character's own reasoning for the line
NOTE_SEES_SCENE = 2             # how many lines of what was just said to them

# --- Speech speed, done here ---
# Player2 REQUIRES a "speed" with every request and then ignores it: measured
# 2026-11-16, asking for twice normal gave audio the same length to within a
# tenth of a second. So the speech-speed dial has done nothing at all since we
# started fetching the audio instead of asking Player2 to play it — not for
# characters, not for the narrator. That is the whole of "the fastest setting
# sounds like normal".
#
# There is no ffmpeg on this machine, so the speeding up is done here, on the
# samples: short overlapping pieces laid down closer together, each join nudged
# to where the two pieces agree best. Pitch is untouched; lengths land within a
# hundredth of a second of what is asked.
STRETCH_SPEECH = True
# How far it stays clean. We compared 1.35, 1.5 and 1.75 by ear on
# 2026-11-16 and called 1.75 too much, so the stretching stops at 1.5 and
# anything beyond it is asked of the voice instead, as pace in the direction —
# which is worth about a third and does not damage anything.
STRETCH_CEILING = 1.5
# What to add to a note when the dial is set past the ceiling.
PACE_WORDS = ((1.25, "Use a brisk, quick pace; do not linger."),
              (1.6, "Speak fast, at an urgent clip, words close together."))

# --- Loudness ---
# The mod applies the MCM "TTS Volume" slider as a gain while it encodes the
# audio (its own hint says so), and ours sits above 1. We were playing the
# bytes untouched, so our speech sat quieter than the mod's with no way to tell
# why. Matching the slider is not a quality change in itself, but a quieter
# voice is heard as a thinner one.
#
# Never clipped: the gain is capped at whatever headroom the clip actually has,
# so a loud render is left alone rather than squared off into distortion.
MATCH_MOD_LOUDNESS = True
MAX_LOUDNESS_GAIN = 4.0
# How far a later part of the same line is pulled towards the loudness its
# first part was played at. 1.0 makes every part exactly as loud as the first;
# 0 leaves each part as it came.
#
# Needed because the generation's own loudness wanders: measured on 2026-11-16,
# six parts of one speech with identical voice and direction came back with
# their average level varying by a factor of 1.62. That is heard as the voice
# changing, not as the character speaking up. 0.7 takes most of it out while
# leaving a line that genuinely drops away at the end quieter than its opening.
STEADY_PULL = 0.7
# A long speech is read in parts rather than generated whole, which is what
# the mod does. Chosen by ear on 2026-11-16: in one generation this voice
# drifts and starts to rush a thirty-second speech, while the same words in
# three parts — each told it is a continuation — were read fully and held the
# performance. It starts sooner too: the parts are generated side by side and
# played in order as they arrive, so the first words do not wait for the whole
# speech to be made.
#
# This reverses the 2026-11-12 comparison, and deliberately: that one was made
# without the continuation clause below, so each part really was starting
# afresh. 0 goes back to one generation per piece.
# Raised from 220 on 2026-11-16, same evening, against the switching we
# could still hear: every part is an independent roll of the voice (there is
# no seed - see the memory file), so the fewer parts a speech is read in, the
# less it can wander. 340 reads a long speech in four rather than six, so the
# first words arrive a few seconds later than they did at 220 and the voice
# has two fewer places to wander.
#
# The quick opening piece above was tried as a way to buy that start back
# and turned off again: it is a seam of its own in the first words, where
# the ear is listening hardest, and it cut across the memory book's titles.
#
# This is the number to turn if the balance is wrong: lower for a quicker
# start, higher for fewer seams.
LINE_PART_CHARS = 340
# Told to the voice when a piece is one of several in the same voice, so each
# piece is not performed as a complete line. This is the mod's own wording,
# taken from a note it left in the save file.
PART_OF_A_LINE = (
    "The text you are given is one part of a longer line: the parts are voiced "
    "separately and played back to back as a single continuous speech. Keep "
    "exactly the same voice, tempo, loudness and mood in every part. Do not "
    "treat the part as a complete line: no fresh start, no summing-up and no "
    "closing flourish unless the text itself ends the line.")

# --- Scenes with no tag on them at all ---
# 7.0.3 tags its scenes, and every tag we know means something: a conversation
# with you, a group scene, talk overheard nearby, a letter, a duel. But some
# exchanges are written into a character's file with NO tag and NO observations
# whatsoever — found 2026-11-16 with Lysa Arryn, who was being read aloud while
# answering a MESSENGER carrying a summons, with the player nowhere in it.
# Those lines look exactly like a conversation with you on the page, so the old
# fallback ("no tag, treat it as a conversation") read other people's business
# at you out of nowhere.
#
# An untagged scene is now only read when YOU are in it, judged by the player's
# own id appearing among the recent lines. Nothing is guessed from names, and a
# tagged scene is unaffected — including an NPC-initiated conversation, which
# carries "dialog/initiative" and so never reaches this test even though you
# have not spoken yet.
ONLY_UNTAGGED_SCENES_WITH_YOU = True
# How far back to look for your own voice in an untagged scene.
UNTAGGED_LOOKBACK = 10

# --- Duels ---
# A duel is its own kind of scene in 7.0.3, and the taunts are written into
# the history differently from speech. They also come in faster than they can
# be read: four of Gregor Clegane's arrived from one fight. Only the newest
# waiting taunt is kept, so the shouting keeps pace with the swords instead of
# trailing a minute behind them. False reads every one, in order.
NARRATE_DUELS = True
DUEL_ONLY_LATEST = True

# --- The memory book ---
# 7.0 writes a memory as a story in the character who remembers it, and the
# book shows every one of them newest first. Nothing in the save says which
# page you have open, so the key follows the book's own order: the first press
# reads the top entry, each further press steps down the list, exactly as the
# other two keys work.
READ_MEMORIES = True
MEMORY_HOTKEY = "numpad*"
# Read the title before the story, the way the page shows it.
ANNOUNCE_MEMORY_TITLE = True
# Name the one who remembers it, as the foot of the page does.
ANNOUNCE_MEMORY_OWNER = True
# The book is a web page in an embedded browser, and which page is open lives
# only inside it. MEMORY_BOOK_HOOK.py adds a few lines to that page which ping
# us here whenever the page turns, so the key can read what you are looking at
# instead of counting from the top. Without the hook nothing listens and the
# key simply falls back to the top of the book.
FOLLOW_OPEN_PAGE = True
# Put the hook into the book ourselves each time we start, and repair it after
# an AI Influence update has overwritten the page. Off: run MEMORY_BOOK_HOOK.py
# by hand, or do without and have the key start at the top of the book.
INSTALL_BOOK_HOOK = True
# Ports we may listen on, tried in turn until one is free. The page tries the
# same list and only talks to whichever answers as us, so a machine where
# something else holds the first port still works. Keep this the same as
# BOOK_REPORT_PORTS in MEMORY_BOOK_HOOK.py.
BOOK_REPORT_PORTS = [4401, 4402, 4403, 4404, 4405]
# A report older than this means the book was closed or the game has gone.
BOOK_REPORT_SECONDS = 4.0

# --- System tray ---
# Live in the tray next to the clock rather than the taskbar: left-click the
# icon to show or hide the console, right-click for the menu. Needs pystray and
# Pillow; without them the console simply stays as it is.
USE_TRAY = True
HIDE_FROM_TASKBAR = True      # no taskbar button and no alt-tab entry
START_MINIMIZED = False       # True to tuck the console away at startup


# ============================================================
#  SOUND
# ============================================================

# --- Saying the names right (2026-11-23) ---
# The old proxy's respelling list (TTS_NARRATOR._WORD_REPLACEMENTS: about 70
# Westeros names, houses, places and words) was never applied by this file, so
# every name was the voice's guess - Lys above all. It is applied again here,
# to the text sent to the voice only: subtitles, the chat log and the delivery
# notes are untouched, and no prompt grows, so it costs no tokens. Order: your
# own file first, then the additions below, then the old list (an earlier match
# wins, because the respelled word no longer matches a later rule).
PRONUNCIATION_FILE = "pronunciations.txt"
EXTRA_PRONUNCIATIONS = [
    # fixes to the old list
    ("Lys", "Liss"), ("Lyseni", "Lisseenee"),
    # places
    ("Pentos", "Pentoss"), ("Pentoshi", "Pentoshee"),
    ("Volantis", "Volahntis"), ("Volantene", "Volahnteen"),
    ("Tyrosh", "Tyerosh"), ("Tyroshi", "Tyeroshee"),
    ("Ghis", "Giss"), ("Ghiscari", "Gisskahree"),
    ("Rhoyne", "Royn"), ("Rhoynar", "Roynar"),
    ("Sothoryos", "Sothoreeos"), ("Yi Ti", "Yee Tee"),
    ("Valyria", "Vuhleeria"), ("Lhazar", "Luhzar"), ("Lhazareen", "Luhzareen"),
    ("Mantarys", "Mantariss"), ("Harrenhal", "Harren hall"),
    ("Pyke", "Pike"), ("Yronwood", "Iron wood"), ("Lorath", "Lorrath"),
    # people
    ("Aemon", "Aymon"), ("Aemond", "Aymond"), ("Daemon", "Daymon"),
    ("Daeron", "Dayron"), ("Baelor", "Baylor"), ("Maekar", "Maykar"),
    ("Rhaenyra", "Rayneera"), ("Rhaella", "Rayella"), ("Rhaenys", "Rayniss"),
    ("Jaehaerys", "Jayhairiss"), ("Visenya", "Visenya"), ("Euron", "Yooron"),
    ("Balon", "Baylon"), ("Victarion", "Viktairion"), ("Quentyn", "Kwentin"),
    ("Olenna", "Olenna"), ("Leyton", "Layton"), ("Alerie", "Alleree"),
    ("Brynden", "Brinden"), ("Jorah", "Jora"), ("Jhiqui", "Jeekee"),
    ("Xaro", "Zaro"), ("Pycelle", "Pyesell"), ("Tyene", "Teeyen"),
    # words
    ("R'hllor", "Ruhlor"), ("Rhllor", "Ruhlor"), ("weirwood", "weerwood"),
    ("Valar Morghulis", "Vahlar Morgoolis"), ("Valar Dohaeris", "Vahlar Dohairis"),
    ("Dracarys", "Druhcariss"),
]
_pron = {"mtime": None, "rules": []}


def _pron_rule(word, said):
    return (re.compile(r"(?<![\w'])" + re.escape(word) + r"(?![\w'])", re.IGNORECASE), said)


def _pron_rules():
    """Your file (re-read whenever it changes) + the additions + the old list."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), PRONUNCIATION_FILE)
    try:
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write("# How the narrator should SAY a word. One per line:  Word = sounds like\n"
                        "# Spell the right side the way it sounds, e.g.  Lys = Liss\n"
                        "# Changes apply to the next line spoken. Lines starting with # are ignored.\n"
                        "# Only the voice hears these; subtitles keep the real spelling.\n\n")
        mtime = os.path.getmtime(path)
    except OSError:
        mtime = None
    if _pron["mtime"] == mtime and _pron["rules"]:
        return _pron["rules"]
    rules = []
    try:
        with open(path, encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    word, said = (s.strip() for s in line.split("=", 1))
                    if word and said:
                        rules.append(_pron_rule(word, said))
        if rules:
            print(f"  [names] {len(rules)} pronunciation(s) of your own in use.")
    except OSError:
        pass
    rules += [_pron_rule(w, s) for w, s in EXTRA_PRONUNCIATIONS if w.lower() != s.lower()]
    # Only the names part of the old list: after it comes a filter dodge that
    # respells ordinary words ("came", "bastard", "hell") and was never used
    # by this narrator; the voice says those fine as they are.
    for p, s in getattr(core, "_WORD_REPLACEMENTS", []):
        if "fuck" in p:
            break
        rules.append((re.compile(p, re.IGNORECASE), s))
    _pron["mtime"], _pron["rules"] = mtime, rules
    return rules


def pronounce(text):
    """The text as the voice should say it (see the notes above)."""
    try:
        for rx, said in _pron_rules():
            text = rx.sub(said, text)
    except Exception as e:
        print(f"  [names] Pronunciation step skipped: {e}")
    return text


def fetch(text, voice, instructions, speed):
    """
    Ask Player2 for audio instead of asking it to play — WAV bytes back.

    The pace is ours to apply: 1.0 is sent to Player2 (the field is required
    and ignored, and sending the real figure would double up if it ever
    started working), the audio is sped up here, and anything past the clean
    ceiling is asked of the voice as words about pace.
    """
    rate, pace_words = pace_split(speed)
    if pace_words:
        instructions = ((instructions + " ") if instructions else "") + pace_words
    text = pronounce(text)
    body = {"text": text, "voice_ids": [voice], "play_in_app": False,
            "audio_format": "wav", "speed": 1.0}
    if instructions:
        body["advanced_voice"] = {"instructions": instructions}
    r = core.requests.post(PLAYER2 + "/v1/tts/speak", json=body,
                           headers=core._game_headers(), timeout=300)
    r.raise_for_status()
    payload = (r.json() or {}).get("data") or ""
    if payload.startswith("data:"):
        payload = payload.split(",", 1)[1]
    import base64
    raw = base64.b64decode(payload + "=" * (-len(payload) % 4))
    if raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        # Player2 now and then hands back another format (MP3) or nothing at
        # all; Windows cannot play that and the line was lost without a word.
        # Raising lets fetch_with_recovery ask again.
        raise ValueError(f"Player2 sent no WAV audio ({len(raw)} bytes, "
                         f"starts {raw[:4]!r})")
    clip = _tidy_wav(raw)
    return stretch_speech(clip, rate)


def fetch_with_recovery(text, voice, instructions, speed, tag=""):
    """
    Get the audio for one piece, and do not let a long line vanish.

    Player2 fails now and then on a long generation — not a hard limit (a
    759-character speech came back fine on retry) but often enough that a whole
    speech can disappear while the short action after it plays, which is
    exactly what happened to a Stannis line on 2026-11-12. A whole line is
    still ASKED FOR whole, because that is what keeps the delivery natural;
    only when that fails is it tried again, and then broken into sentences so
    the words are heard at all. Returns a list of clips to play in order.
    """
    try:
        return [fetch(text, voice, instructions, speed)]
    except Exception as e:
        print(f"      {tag} failed ({str(e)[:70]}) — trying again")
    try:
        return [fetch(text, voice, instructions, speed)]
    except Exception as e:
        print(f"      {tag} failed twice ({str(e)[:70]}) — "
              f"speaking it in sentences so it is not lost")
    # Broken into SINGLE sentences as a last resort: they are played back to
    # back, so they are told so, or the line is read as a string of separate
    # remarks.
    #
    # One sentence at a time, not 300-character chunks. Since a long speech is
    # now read in parts of its own, a failing part is only a couple of hundred
    # characters, and chunking it at 300 handed back the very text that had
    # just failed — so it failed again and the words were lost, silently.
    # Found by the recovery suite on 2026-11-16, the day the splitting went in.
    parts = core._split_sentences(text, 1) or [text]
    if len(parts) == 1 and parts[0].strip() == (text or "").strip():
        print(f"      {tag} is a single sentence and cannot be broken down "
              f"further — it is lost")
        return []
    joined = instructions
    if len(parts) > 1:
        joined = (instructions or "") + "\n\n" + PART_OF_A_LINE
    clips = []
    for part in parts:
        try:
            clips.append(fetch(part, voice, joined, speed))
        except Exception as e:
            print(f"      a sentence was lost: {str(e)[:70]}")
    return clips


# ============================================================
#  SPEEDING SPEECH UP WITHOUT CHANGING ITS PITCH
# ============================================================
# Player2 takes a speed and ignores it (see the settings), and there is no
# ffmpeg here to hand the audio to, so this is overlap-add done ourselves:
# short segments of the original laid back down closer together, each join
# moved to where the two segments best agree. Pitch is untouched because every
# segment is played at its own rate; only the spacing between them changes.
#
# We heard the first version tearing at 1.5 and this is the rebuild that
# passed. Four things had been wrong with it, and the first is the tearing:
#
#   1. The search for where to join was 3 ms wide. A man's voice sits around
#      100 Hz, so one pitch period lasts about 10 ms: a 3 ms search cannot line
#      the periods up at all, and joining mid-period IS the tear. The search is
#      now a full period wide and looks both earlier and later than the
#      arithmetic position.
#   2. The score was raw correlation, which prefers whatever is LOUDEST over
#      whatever matches. It is divided by the segment's own energy now, so
#      quiet speech is matched on its shape.
#   3. The crossfade was a straight line, which leaves a kink at each end. It
#      is a raised cosine now.
#   4. The step was 20 ms — five hundred joins in a ten-second line. It is
#      40 ms: half as many places to go wrong, still short enough to follow
#      ordinary speech.
#
# The wider search is paid for by matching every fourth sample only: a quarter
# of the work, still accurate to a fifth of a millisecond. About two seconds of
# processing for a twelve-second clip, inside the fetching threads, so it
# overlaps the generation of everything else and is never waited on.

STRETCH_DECIMATE = 4            # match on every Nth sample
STRETCH_HOP_MS = 40.0           # how much is written per step
STRETCH_WINDOW_MS = 16.0        # how long each join is crossfaded over
STRETCH_PERIOD_MS = 12.0        # how far to look for the best join


def pace_split(wanted):
    """
    How to get `wanted` times normal: how much to stretch, and what to say.

    Stretching is exact but only stays clean so far (STRETCH_CEILING), so a
    dial set past that takes the rest from the direction, as words about pace.
    Returns (stretch factor, words to add to the note or "").
    """
    if not STRETCH_SPEECH or not wanted or abs(wanted - 1.0) < 0.02:
        return 1.0, ""
    if wanted <= STRETCH_CEILING:
        return wanted, ""
    words = ""
    for over, phrase in PACE_WORDS:
        if wanted / STRETCH_CEILING >= over:
            words = phrase
    return STRETCH_CEILING, words


def _cos_ramp(n):
    """A raised cosine, for a join without a kink at either end."""
    return [0.5 - 0.5 * math.cos(math.pi * i / float(n)) for i in range(n)]


def _best_offset(out, tail_at, seg, span, window):
    """
    Where in `seg` to start so it agrees best with what is already written.

    Correlation over the segment's own energy — matching on shape rather than
    on loudness — measured on every STRETCH_DECIMATE'th sample.
    """
    step = STRETCH_DECIMATE
    want = out[tail_at:tail_at + window:step]
    best, best_score = 0, None
    for off in range(0, span):
        have = seg[off:off + window:step]
        if len(have) < len(want):
            break
        dot, energy = 0, 1
        for a, b in zip(want, have):
            dot += a * b
            energy += b * b
        score = dot / math.sqrt(energy)
        if best_score is None or score > best_score:
            best, best_score = off, score
    return best


def stretch_speech(wav_bytes, factor):
    """The same words, spoken `factor` times faster. Pitch untouched."""
    if not STRETCH_SPEECH or not wav_bytes or abs(factor - 1.0) < 0.02:
        return wav_bytes
    factor = max(0.5, min(2.5, float(factor)))
    try:
        with wave.open(io.BytesIO(wav_bytes)) as w:
            params, frames = w.getparams(), w.readframes(w.getnframes())
        if params.sampwidth != 2 or params.nchannels != 1 or not frames:
            return wav_bytes
        src = array.array("h")
        src.frombytes(frames)
        rate, n = params.framerate, len(src)

        hop = int(rate * STRETCH_HOP_MS / 1000.0) or 1
        window = int(rate * STRETCH_WINDOW_MS / 1000.0) or 1
        search = int(rate * STRETCH_PERIOD_MS / 1000.0) or 1
        step = int(round(hop * factor)) or 1
        seg_len = hop + window
        ramp = _cos_ramp(window)

        out = array.array("h",
                          bytes(2 * (int(n / factor) + seg_len + 2 * search + 8)))
        out[0:seg_len] = src[0:seg_len]     # the first segment, as it came
        written = seg_len
        out_tail = written - window         # where the next join begins
        in_pos = step

        while in_pos + seg_len + search < n:
            here = max(0, in_pos - search)
            seg = src[here:here + seg_len + 2 * search]
            span = min(2 * search, max(1, len(seg) - seg_len))
            off = _best_offset(out, out_tail, seg, span, window)
            for i in range(window):
                g = ramp[i]
                out[out_tail + i] = int(out[out_tail + i] * (1.0 - g)
                                        + seg[off + i] * g)
            rest = seg[off + window:off + seg_len]
            start = out_tail + window
            out[start:start + len(rest)] = rest
            written = start + len(rest)
            out_tail = written - window
            in_pos += step

        if in_pos < n:                      # whatever is left, laid down plain
            rest = src[in_pos:]
            out[out_tail + window:out_tail + window + len(rest)] = rest
            written = out_tail + window + len(rest)

        done = io.BytesIO()
        with wave.open(done, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(out[:written].tobytes())
        return done.getvalue()
    except Exception as e:
        print(f"      [speed] could not speed this clip up "
              f"({type(e).__name__}: {e}) "
              f"- playing it at its own pace.")
        return wav_bytes


def _stretch_seconds(wav_bytes):
    with wave.open(io.BytesIO(wav_bytes)) as w:
        return len(w.readframes(w.getnframes() or 10 ** 9)) / float(
            w.getframerate() * w.getnchannels() * w.getsampwidth())


def _tidy_wav(raw):
    """
    Rewrite the header honestly before anything tries to play it.

    Player2 streams its WAVs, so the length written in the header is a
    placeholder, not the truth. Windows' own player believes headers: left as
    they are, a clip can be cut short or run on into noise. Reading the frames
    and writing a fresh header costs nothing and removes the whole class of
    problem — it is also what makes the clip's real duration knowable.
    """
    try:
        with wave.open(io.BytesIO(raw)) as w:
            params, frames = w.getparams(), w.readframes(w.getnframes())
        out = io.BytesIO()
        with wave.open(out, "wb") as w:
            w.setnchannels(params.nchannels)
            w.setsampwidth(params.sampwidth)
            w.setframerate(params.framerate)
            w.writeframes(frames)
        return out.getvalue()
    except Exception:
        return raw                      # not a WAV we understand; hand it on


def at_dial_volume(wav_bytes):
    """
    Your own volume, from the tray menu. 1.0, or unset, changes nothing.

    Through _at_gain, so a setting above normal is rounded off at the ceiling
    rather than squared off into distortion - which is also why the dial is
    worth much more downwards than up: a clip has already been lifted to the
    mod's own slider and has little room left above it.
    """
    dial = core.tts_volume()
    if not dial or abs(dial - 1.0) <= 0.01:
        return wav_bytes
    return _at_gain(wav_bytes, dial)


def play(wav_bytes):
    """
    Play one clip and return when it has finished.

    Playing it ourselves is what lets the next clip be fetched while this one
    sounds, and it means we KNOW when a clip ends instead of estimating from
    its character count the way the old proxy had to.

    Every clip the narrator makes a sound with comes through here, which is
    why the volume dial is applied here and nowhere else.
    """
    if not wav_bytes or _state["skip"].is_set():
        return
    wav_bytes = at_dial_volume(wav_bytes)
    try:
        import winsound
        winsound.PlaySound(wav_bytes, winsound.SND_MEMORY)
    except Exception as e:
        # Not fatal: without sound the line is still logged and the next one
        # still plays.
        print(f"  [sound] Could not play: {e}")


def stop_sound():
    """Cut off whatever is sounding right now (used to interrupt a reading)."""
    try:
        import winsound
        winsound.PlaySound(None, winsound.SND_PURGE)
    except Exception:
        pass


def seconds_of(wav_bytes):
    try:
        with wave.open(io.BytesIO(wav_bytes)) as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        return 0.0


# ============================================================
#  WHO SPEAKS, AND HOW
# ============================================================

def scene_kind(npc):
    """
    What kind of scene this character is in RIGHT NOW, from the mod's own tag.

    7.0 stamps each dialogue observation with a scene id whose prefix says what
    the scene is: "dialog" and "dialog/initiative" are with you, "group" is a
    group scene, "ambient" is other people talking near you, "duel" is single
    combat with you, "letter" is written. Returns that word, or "" when there
    is nothing to go on.

    This replaced guessing. The old test called a scene a group whenever the
    character had heard another NPC speak — which is true of ambient chatter
    too, so overheard conversations were being announced like a court.
    """
    for o in reversed(npc.get("DialogueObservations") or []):
        if isinstance(o, dict) and (o.get("scene_id") or o.get("source_tag")):
            tag = str(o.get("source_tag") or o.get("scene_id"))
            # The tag is like "dialog/npc", "letter/player", "ambient-npc" or
            # "group" — and it may be followed by ":place:day:id". Both the
            # slash AND the hyphen appear as separators, which is how
            # "ambient-npc" was being read as an unknown scene and treated as a
            # conversation with the player (found 2026-11-14).
            head = re.split(r"[/\-]", tag.split(":", 1)[0])[0]
            return head if head in ("dialog", "group", "ambient", "letter",
                                    "duel") else ""
    return ""


def you_are_in_this(npc, lookback=None):
    """
    Are YOU part of this scene? Judged by your own id among the recent lines.

    Used only for a scene the mod left untagged, where there is nothing else to
    go on: your lines are kept in the same history as theirs, so your id being
    absent from the whole recent exchange means the conversation is not with
    you — a messenger, a servant, another lord's business.
    """
    pid = core._player_id(npc)
    back = lookback or UNTAGGED_LOOKBACK
    for entry in (npc.get("ConversationHistory") or [])[-back:]:
        speaker, _body = core._entry_speaker_id(entry)
        if speaker == pid:
            return True
    return False


def spoken_by(npc):
    """
    Who said each line, for lines that do not say so themselves.

    Most history lines carry the speaker's id in backticks, but a duel taunt
    is written plainly — "Lord Gregor Clegane: HA! ..." — with no id at all,
    so the usual reading of a line found no speaker and every taunt was
    skipped in silence (found 2026-11-16, mid-duel).

    The observations beside the history hold the answer exactly: each one
    carries the line as it was heard, word for word, together with the id of
    whoever said it. No guessing from names.
    """
    out = {}
    for o in (npc.get("DialogueObservations") or []):
        if not isinstance(o, dict):
            continue
        heard = (o.get("heard_line") or "").strip()
        who = o.get("speaker_hero_id")
        if heard and who:
            out[heard] = who
    return out


def drop_stale_duel_lines():
    """Keep only the newest taunt waiting to be read."""
    with _queue_cv:
        duels = [q for q in _queue if q[0] == "line" and q[1][3] == "duel"]
        if len(duels) <= 1:
            return 0
        keep_one = duels[-1]
        rest = [q for q in _queue
                if not (q[0] == "line" and q[1][3] == "duel") or q is keep_one]
        dropped = len(_queue) - len(rest)
        _queue[:] = rest
        _queue_cv.notify()
    if dropped:
        print(f"  [duel] Skipped {dropped} taunt(s) to keep up with the fight.")
    return dropped


def quieten(wav_bytes, factor):
    """
    Make a clip quieter, for talk you are only overhearing.

    Done to the samples themselves because the player we use has no volume of
    its own, and because it keeps the clip exactly as long as it was.
    """
    if not wav_bytes or factor >= 0.999:
        return wav_bytes
    try:
        import array
        with wave.open(io.BytesIO(wav_bytes)) as w:
            params, frames = w.getparams(), w.readframes(w.getnframes())
        if params.sampwidth != 2:
            return wav_bytes
        samples = array.array("h")
        samples.frombytes(frames)
        for i, v in enumerate(samples):
            samples[i] = int(v * factor)
        out = io.BytesIO()
        with wave.open(out, "wb") as w:
            w.setnchannels(params.nchannels)
            w.setsampwidth(params.sampwidth)
            w.setframerate(params.framerate)
            w.writeframes(samples.tobytes())
        return out.getvalue()
    except Exception:
        return wav_bytes


def mod_tts_volume():
    """The MCM "TTS Volume" slider, or None when it cannot be read."""
    try:
        with core.open_shared(core.MOD_SETTINGS_FILE, "utf-8") as f:
            return float(json.load(f).get("TTSVolume"))
    except Exception:
        return None


class LineLoudness:
    """
    One gain for a whole line, settled on its first part and held.

    at_mod_loudness on its own chooses the gain from the clip in front of it,
    and the parts of one speech come back at different levels - this voice
    renders the same words anywhere between a half and full scale. Each part
    was therefore lifted by a different amount: as far as its OWN headroom
    allowed. A hot part got less, a quiet part got more, and a loudness that
    steps up and down between the parts of one sentence is heard as the voice
    changing rather than as a level change.

    The gain is settled on the first part of the line and then applied to
    every part as it stands - no second headroom reduction, because that is
    the step itself. Peaks that would pass full scale are rounded off by
    _at_gain instead, which is what a limiter does and what the mod's own
    encoder does with its gain.
    """

    def __init__(self):
        self.gain = None        # what the first part was lifted by
        self.level = None       # and the level it ended up at

    def apply(self, clip):
        if not MATCH_MOD_LOUDNESS or not clip:
            return clip
        here = _level(clip)
        if self.gain is None:
            # The first part sets the line's loudness: the slider, reduced to
            # what this clip can take.
            self.gain = _loudness_gain(clip)
            self.level = here * self.gain
            return _at_gain(clip, self.gain)
        if not here or not self.level or not STEADY_PULL:
            return _at_gain(clip, self.gain)
        # Partly towards the first part's level, never more than the slider
        # would have allowed in either direction.
        gain = (self.level / here) ** STEADY_PULL
        gain = min(max(gain, 1.0 / MAX_LOUDNESS_GAIN), MAX_LOUDNESS_GAIN)
        return _at_gain(clip, gain)


def _samples_of(wav_bytes):
    """(params, samples) or (None, None) for anything we will not touch."""
    try:
        with wave.open(io.BytesIO(wav_bytes)) as w:
            params, frames = w.getparams(), w.readframes(w.getnframes())
        if params.sampwidth != 2 or not frames:
            return None, None
        samples = array.array("h")
        samples.frombytes(frames)
        return params, samples
    except Exception:
        return None, None


def _level(wav_bytes):
    """
    A clip's average level - loudness as the ear hears it.

    The peak says almost nothing here: the six measured parts above sat within
    a third of each other on peak while their level varied by two thirds.
    """
    _, samples = _samples_of(wav_bytes)
    if not samples:
        return 0.0
    total = 0.0
    step = max(1, len(samples) // 24000)      # a sample every so often is plenty
    n = 0
    for i in range(0, len(samples), step):
        v = float(samples[i])
        total += v * v
        n += 1
    return math.sqrt(total / n) if n else 0.0


def _headroom(wav_bytes):
    """How much this clip can be lifted before anything clips."""
    _, samples = _samples_of(wav_bytes)
    if not samples:
        return 1.0
    peak = max(abs(min(samples)), abs(max(samples))) or 1
    return 32500.0 / peak


def _loudness_gain(wav_bytes):
    """The gain the slider asks for, reduced to what this clip can take."""
    want = mod_tts_volume()
    if not want or want <= 1.001:
        return 1.0
    return min(want, _headroom(wav_bytes), MAX_LOUDNESS_GAIN)


# Where the knee starts, and where the scale ends. Below the knee the gain is
# exact; between the two the curve bends over so that nothing reaches full
# scale and nothing is squared off.
_KNEE = 28000.0
_CEILING = 32500.0


def _at_gain(wav_bytes, gain):
    """
    Change a clip's loudness by `gain`, rounding off anything that would clip.

    Below 1 as well as above it: a later part of a line is sometimes pulled
    down towards the level the line started at.
    """
    if not gain or abs(gain - 1.0) <= 0.01:
        return wav_bytes
    params, samples = _samples_of(wav_bytes)
    if not samples:
        return wav_bytes
    try:
        span = _CEILING - _KNEE
        for i, v in enumerate(samples):
            x = v * gain
            a = abs(x)
            if a > _KNEE:
                a = _KNEE + span * math.tanh((a - _KNEE) / span)
                x = a if x > 0 else -a
            samples[i] = int(x)
        out = io.BytesIO()
        with wave.open(out, "wb") as w:
            w.setnchannels(params.nchannels)
            w.setsampwidth(params.sampwidth)
            w.setframerate(params.framerate)
            w.writeframes(samples.tobytes())
        return out.getvalue()
    except Exception:
        return wav_bytes


def at_mod_loudness(wav_bytes):
    """
    One clip at the loudness the mod would have played it at.

    The mod's gain is applied while encoding; ours has to be applied to the
    samples, because the player we use has no volume of its own. For anything
    with PARTS - a speech read in several pieces - use LineLoudness instead, so
    the whole line is lifted by the one amount. This is the single-clip case
    and goes through the same arithmetic.
    """
    return LineLoudness().apply(wav_bytes)


def in_your_conversation():
    """True while a conversation of your own is still going on."""
    return (time.time() - _state["your_scene_at"]) < IN_CONVERSATION_SECONDS


def hush_ambient(why):
    """Cut off anything being overheard, and forget what is queued of it."""
    dropped = 0
    with _queue_cv:
        keep = [q for q in _queue if not (q[0] == "line" and q[1][3] == "ambient")]
        dropped = len(_queue) - len(keep)
        _queue[:] = keep
        _queue_cv.notify()
    if _state["speaking_ambient"]:
        _state["skip"].set()
        stop_sound()
        print(f"  [ambient] Hushed — {why}.")
    elif dropped:
        print(f"  [ambient] Dropped {dropped} overheard line(s) — {why}.")


_background_voices = {}
_background_heard = []          # (id, words) already spoken, newest last


def background_character(entry):
    """For a line said by a scene's made-up character: (id, name, gender)."""
    label = entry.split(": ", 1)[0]
    m = re.search(r"`([^`]+)`", label)
    if not m or not m.group(1).startswith("scene_agent"):
        return None
    name = label[:label.find("(")].strip() if "(" in label else label.strip()
    name = name or "A stranger"
    words = re.findall(r"[a-z]+", name.lower())
    gender = "female" if any(w in FEMALE_TITLE_WORDS for w in words) else "male"
    return m.group(1), name, gender


def background_npc(agent_id, name, gender):
    """A stand-in character record, so the line is spoken like anyone else's."""
    key = agent_id + "|" + name
    npc = {"Name": name, "StringId": "bg:" + key, "Gender": gender,
           "AssignedTTSVoice": _background_voices.get(key, "")}
    if not npc["AssignedTTSVoice"]:
        npc["AssignedTTSVoice"] = voice_for(npc)     # chosen once, kept for them
        _background_voices[key] = npc["AssignedTTSVoice"]
    return npc


def voice_for(npc):
    """
    The voice for this character: the mod's choice, unless it is one you banned.

    The mod now keeps a character on the same voice by itself, so its pick is
    taken as given; the ban list is the one place we still overrule it.
    """
    gender = (npc.get("Gender", "male") or "male").lower()
    sid = npc.get("StringId", "")

    def usable(v):
        if v not in core.VOICE_DB:
            return False
        if HONOUR_BANNED_VOICES and v in core.banned_voices():
            return False
        if RESERVE_NARRATOR_VOICE and v == core.NARRATOR_VOICE:
            return False
        # Player2's list includes Hindi, Mandarin, Italian and Spanish
        # speakers, and the mod hands them out; they read Westeros in those
        # accents. English only, American or British.
        if (core.VOICE_DB[v].get("lang") or "") not in (
                "american_english", "british_english"):
            return False
        # A man must not be given a woman's voice. The old replacement for a
        # banned voice matched the BANNED voice's gender rather than the
        # character's, so banning a British woman could hand a lord her
        # stand-in — found 2026-11-12 while chasing Ser Harlan.
        if MATCH_VOICE_TO_GENDER and gender in ("male", "female"):
            if (core.VOICE_DB[v].get("gender") or "").lower() != gender:
                return False
        return True

    # ONLY AssignedTTSVoice is a voice. CharacterVoice is a speaking HABIT —
    # "soft_menace", "rhymes", "aches" — and using it as a voice sent that word
    # to Player2 as an id, which fell back to a default voice: that is how Ser
    # Harlan Blackhare, a man, came out female on 2026-11-12.
    chosen = npc.get("AssignedTTSVoice") or ""
    if usable(chosen):
        return chosen

    def own_pick():
        """A voice of our own choosing for THIS character.

        Keyed on the character, not on the voice we are moving away from, so
        two lords handed the same unusable voice do not end up sounding alike —
        AI Influence had given the narrator's own voice to nine men at once,
        and the old stand-in turned all nine into the same Noah (2026-11-15).

        md5, not hash(): Python randomises string hashing per process, so the
        old pool pick could hand a character a different voice every restart.
        """
        # English only: the full voice list carries Mandarin, Spanish and
        # Portuguese speakers, and they read Westeros with those accents.
        english = sorted(v for v, info in core.VOICE_DB.items()
                         if (info.get("lang") or "") in
                         ("american_english", "british_english"))
        pool = [v for v in english
                if (core.VOICE_DB[v].get("gender") or "").lower() == gender
                and usable(v)]
        pool = pool or [v for v in english if usable(v)]
        pool = pool or sorted(v for v in core.VOICE_DB if usable(v))
        if not pool:
            return ""
        return pool[core._stable_index(sid or chosen or "", len(pool))]

    # A voice that is real but reserved or banned is not a casting hint, it is
    # a collision: cast this character ourselves rather than letting the core
    # move everyone who shares that voice to one stand-in.
    if chosen in core.VOICE_DB:
        mine = own_pick()
        if mine:
            print(f"  [voice] {npc.get('Name')} ({gender}): "
                  f"{core.VOICE_DB[chosen].get('name')} is spoken for — using "
                  f"{core.VOICE_DB[mine].get('name')}.")
            return mine

    pick = core.resolve_voice(chosen if chosen in core.VOICE_DB else "",
                              gender, sid)
    if not usable(pick):
        # Nothing upstream gave us a real voice. Choose one ourselves, of the
        # right gender, the same way every time for this character.
        pick = own_pick() or pick
    why = ("the mod chose a banned voice" if chosen in core.VOICE_DB
           else f"the mod gave no usable voice ({chosen!r})" if chosen
           else "the mod has not chosen a voice yet")
    print(f"  [voice] {npc.get('Name')} ({gender}): {why} — using "
          f"{core.VOICE_DB.get(pick, {}).get('name', pick)}.")
    return pick


_notes_written = {}
_notes_order = []
# Per character+scene+mood: the note they are currently being performed with,
# and when it was written. See NOTE_HOLD_SECONDS.
_notes_held = {}
_notes_lock = threading.Lock()


def _stored_reply(npc):
    """The AI's own last reply for this character, as it was written down."""
    try:
        raw = npc.get("LastAIResponseJson") or ""
        return json.loads(raw) if raw else {}
    except Exception:
        return {}


def line_cues(npc, text):
    """
    What the AI itself said about the line it had just written.

    Every reply the mod stores carries a one-word `emotion`, sometimes a
    `gesture` and a `volume`. They are only trustworthy for the line they were
    written for, so the reply's own words must match what we are about to
    speak — otherwise this is last line's feeling on this line's words.
    """
    reply = _stored_reply(npc)
    said = (reply.get("response") or "").strip()
    want = (text or "").strip()
    if not said or not want:
        return {}
    short = want[:60]
    if short not in said and said[:60] not in want:
        return {}
    out = {}
    for key in ("emotion", "gesture", "volume"):
        val = reply.get(key)
        if isinstance(val, str) and val.strip():
            out[key] = val.strip()
    return out


def line_subtext(npc, text):
    """
    The character's own reasoning for the line, when it was written for it.

    Guarded exactly like line_cues: the stored reply holds only the LAST reply,
    so its reasoning is used only when its words are the words being spoken.
    """
    if not NOTE_SEES_THOUGHTS:
        return ""
    reply = _stored_reply(npc)
    said = (reply.get("response") or "").strip()
    want = (text or "").strip()
    if not said or not want:
        return ""
    if want[:60] not in said and said[:60] not in want:
        return ""
    thoughts = (reply.get("internal_thoughts") or "").strip()
    return thoughts[:700]


def scene_before(npc, text):
    """What was just said to them, in the words the save keeps."""
    if not NOTE_SEES_SCENE:
        return []
    history = [e for e in (npc.get("ConversationHistory") or [])
               if isinstance(e, str) and e.strip()]
    want = (text or "").strip()[:60]
    where = None
    for i in range(len(history) - 1, -1, -1):
        if want and want in history[i]:
            where = i
            break
    if where is None:
        where = len(history)
    out = []
    for e in history[max(0, where - NOTE_SEES_SCENE):where]:
        speaker, body = core._entry_speaker_id(e)
        said = (body or e).strip()
        who = "Them" if speaker == npc.get("StringId") else "The other person"
        if ": " in said and speaker is None:
            who, said = said.split(": ", 1)
        out.append(f"{who}: {said[:220]}")
    return out


def character_manner(npc):
    """How this person speaks, in their own file's words. Short on purpose."""
    # Not the speech habits (AIGeneratedSpeechQuirks, CharacterVoice): those
    # are about WORDS, and the words are already written. Handed to the note
    # writer they came back as "tumble proverbs out quick and half-mangled",
    # which a voice performs as a regional drawl (Giselda Borrell, 2026-11-24).
    bits = []
    mood = npc.get("EmotionalState") or {}
    if isinstance(mood, dict) and (mood.get("Mood") or "").strip():
        why = (mood.get("Reason") or "").strip()
        bits.append("Mood: " + mood["Mood"]
                    + (f" ({why[:120]})" if why and why != "no specific reason"
                       else ""))
    rel = npc.get("PlayerRelation") or {}
    if isinstance(rel, dict) and (rel.get("Description") or "").strip():
        bits.append("Towards you: " + rel["Description"])
    return "\n".join(bits)


def composed_note(npc, text, kind="dialog"):
    """
    A performance note put together here, from what the save already knows.

    No network, ready at once. Not as good as a note written for the line, but
    an entire world away from naming an accent and leaving it at that.
    """
    cues = line_cues(npc, text)
    parts = []
    feeling = cues.get("emotion")
    if feeling:
        parts.append(f"Speak {feeling}.")
    mood = (npc.get("EmotionalState") or {})
    if not feeling and isinstance(mood, dict) and (mood.get("Mood") or "").strip():
        parts.append(f"Speak as someone {mood['Mood']}.")
    # The speech habits stay out here too - see character_manner().
    if kind == "duel":
        parts.append("Shouted in the middle of a sword fight, breath short.")
    elif kind == "ambient":
        parts.append("Talking to someone else, not to the listener.")
    if cues.get("volume"):
        parts.append(f"Volume: {cues['volume']}.")
    note = " ".join(parts).strip()
    if not note:
        return (core.pinned_character_instructions(npc.get("StringId", ""))
                or core.voice_accent_instructions(npc.get("AssignedTTSVoice", "")))
    return note


# Written in the mod's own register, which was picked by ear on 2026-11-16
# against a denser descriptive one. The mod's notes read like a director
# talking to an actor — "Speak with a measured, dry pace. Use a low pitch and
# a calm, unimpressed tone. Avoid any hint of anger." — and short: it asks for
# 20 to 200 characters. A generative voice performs its instruction as much as
# it obeys it, so a pile of adjectives muddies what three plain orders make
# clear.
NOTE_BRIEF = (
    "You write the voice direction for one line of speech in a medieval "
    "fantasy game, for a text-to-speech engine that performs whatever it is "
    "told. Write it the way a director speaks to an actor: two or three short "
    "imperative sentences, under 200 characters in all, in the form \"Speak "
    "with...\", \"Use...\", \"Avoid...\". Name mood, emotion, pace and "
    "delivery ONLY. Never describe the voice itself - not its pitch, age, "
    "sex, accent, nationality or timbre. Those are fixed already and are the "
    "same in every line; naming them makes the speaker sound like a different "
    "person each time. Never ask for a dialect, a regional or rural way of "
    "speaking, or anything folksy or rustic: only feeling and pace. Reply "
    "with the direction and nothing else: no "
    "quotation marks, no explanation, no repetition of the line.")


# Said anyway, now and then, however plainly it is forbidden above - so the
# obvious forms come back out. Only ever applied to the notes WE ask for: the
# mod's own note is left exactly as the mod wrote it, and a composed note is
# built from the character's own file, where a voice description is constant
# and therefore harmless.
VOICE_WORDS = re.compile(
    r"\b(?:very |slightly |somewhat |rather )?"
    r"(?:high|low|deep|higher|lower|mid)[- ]pitched\b,?\s*"
    r"|\buse (?:a|an|your) [^.;!?]*?"
    r"\b(?:pitch|register|timbre|vocal range)\b[^.;!?]*[.;!?]\s*"
    r"|\b(?:speak|talk) (?:in|with) (?:a|an) [^.;!?]*?"
    r"\baccent\b[^.;!?]*[.;!?]\s*"
    r"|\b(?:sound|speak) (?:like|as) (?:a|an) "
    r"(?:young|old|elderly|teenage|aged)[^.;!?]*[.;!?]\s*",
    re.I)


# A dialect asked for anyway: "a slight southern drawl", "a folksy lilt". Cut
# as a phrase, not a sentence, so the rest of the direction survives, and
# before the length check, because a dialect is never worth keeping.
DIALECT_WORDS = re.compile(
    r"(?:,\s*)?\b(?:with |in |using )?(?:a |an )?"
    r"(?:(?:slight|soft|gentle|light|faint|thick|heavy|warm|broad|lazy)[ ,]+)*"
    r"(?:(?:folksy|homespun|rustic|countrified|southern|backwoods|hillbilly|"
    r"rural|regional|country)[ ,-]+)*"
    r"(?:drawl\w*|twang\w*|dialect|brogue|lilt)\b"
    r"|(?:,\s*)?\b(?:(?:a|an) )?(?:folksy|homespun|rustic|countrified|backwoods|"
    r"hillbilly)\b,?"
    # "blunt Vale speech", "a Northern burr", "Dornish lilt": a region's or a
    # people's way of talking reads as an accent to the voice (Ysilla Royce).
    r"|(?:,\s*)?\b(?:(?:with|in) )?(?:(?:a|an) )?(?:(?:plain|blunt|dry|thick|broad|soft|"
    r"slow|clipped|lilting|rough)[ ,]+)*(?:Vale|Northern|northern|Northman|Dornish|"
    r"southron|Southron|Reach|Riverlands?|Westerlands?|Stormlands?|Crownlands?|ironborn|"
    r"Ironborn|Iron Islands|Essosi|Westerosi|Braavosi|Valyrian|Dothraki|wildling|"
    r"Free Folk|free folk|island|country|village|peasant|farm|provincial|regional|"
    r"backcountry)\s+(?:speech|accent|vowels|burr|lilt|cadence|twang|drawl|tongue|"
    r"manner of speaking|way of speaking)\b"
    # Any phrase that ENDS in an accent word, whatever comes before it: a list of
    # places always misses one ("unhurried hill accent", 2026-11-26).
    r"|(?:,\s*)?\b(?:(?:with|in|a|an)\s+)*(?:[A-Za-z'-]+\s+){0,2}"
    r"(?:accents?|drawl\w*|twang\w*|brogue|burr|dialect)\b",
    re.I)


def without_dialect(note):
    """
    Only the accent and dialect words, from ANY note - the mod's own as well.

    The mod's notes are otherwise left as the mod wrote them; a dialect is the
    one thing in them that is never wanted (2026-11-26, Ysilla Royce's "dry,
    blunt Vale speech" came out as a Texan drawl).
    """
    if not note:
        return note
    out = DIALECT_WORDS.sub("", note)
    out = re.sub(r"\s{2,}", " ", out)
    out = re.sub(r"\s+([,.;!?])", r"\1", out).strip(" ,;")
    out = re.sub(r"(^|[.;!?] )[,;]\s*", r"\1", out)
    out = re.sub(r"(?:(?<=^)|(?<=[.;!?] ))[A-Za-z]+[.;!?](?: |$)", "", out).strip()
    if not out or len(out) < 12:
        return note
    if out != note:
        out = out[0].upper() + out[1:]
        print(f"      [note] accent words dropped: {note[:60]!r} -> {out[:60]!r}")
    return out


def without_voice_words(note):
    """Strip what the note was told not to say about the voice."""
    if not note or not VOICE_ANCHOR:
        return note
    note0 = note
    note = DIALECT_WORDS.sub("", note)
    note = re.sub(r"\s{2,}", " ", note)
    note = re.sub(r"\s+([,.;!?])", r"\1", note).strip(" ,;")
    out = VOICE_WORDS.sub("", note)
    out = re.sub(r"\s{2,}", " ", out).strip(" ,;")
    out = re.sub(r"([.;!?])(?=[A-Za-z])", r"\1 ", out)
    # A sentence left as one bare word ("Use.") once its object was cut.
    out = re.sub(r"(?:(?<=^)|(?<=[.;!?] ))[A-Za-z]+[.;!?](?: |$)", "", out).strip()
    # A note that was nothing BUT a voice description is worse than useless
    # once emptied, so in that case the original stands and the anchor, which
    # comes first, has to outweigh it.
    if len(out) < 20:
        out = note
    if out != note0:
        out = out[0].upper() + out[1:]
        print(f"      [note] voice description dropped: "
              f"{note0[:60]!r} -> {out[:60]!r}")
    return out


def asked_note(npc, text, kind="dialog"):
    """
    A note written for THIS line by the same AI the mod uses.

    This is the mod's `tts_instructions` field, asked for separately because we
    are not in the mod's conversation with the AI and cannot be (7.0 refuses to
    share its Player2 address — see WATCH MODE in the proxy).
    """
    key = (npc.get("StringId", ""), (text or "")[:160])
    with _notes_lock:
        if key in _notes_written:
            return _notes_written[key]
    held = held_note(npc, kind)
    if held:
        return held
    cues = line_cues(npc, text)
    who = [f"Character: {npc.get('Name')}"]
    manner = character_manner(npc)
    if manner:
        who.append(manner)
    if cues.get("emotion"):
        who.append("The line was written as: " + cues["emotion"]
                   + (f", gesture {cues['gesture']}" if cues.get("gesture") else ""))
    said_before = scene_before(npc, text)
    if said_before:
        who.append("Just said in the scene:\n" + "\n".join(said_before))
    thoughts = line_subtext(npc, text)
    if thoughts:
        who.append("What they are actually thinking as they say it:\n"
                   + thoughts)
    if kind == "duel":
        who.append("They are shouting this during a duel.")
    elif kind == "ambient":
        who.append("They are talking to someone else, overheard.")
    ask = "\n".join(who) + "\nLine: " + (text or "")[:600]
    try:
        r = core.requests.post(
            PLAYER2 + "/v1/chat/completions",
            json={"messages": [{"role": "system", "content": NOTE_BRIEF},
                               {"role": "user", "content": ask}]},
            headers=core._game_headers(), timeout=NOTE_WAIT_SECONDS + 4)
        r.raise_for_status()
        note = (((r.json() or {}).get("choices") or [{}])[0]
                .get("message", {}).get("content") or "").strip()
    except Exception as e:
        print(f"      [note] no note written ({str(e)[:60]}) — "
              f"using what the save already knows")
        note = ""
    note = note.strip().strip('"').strip()
    # The mod asks for 200 characters and that brevity is part of why its
    # delivery lands. A little slack, then cut at a word.
    if len(note) > 260:
        note = note[:260].rsplit(" ", 1)[0]
    with _notes_lock:
        _notes_written[key] = note
        _notes_order.append(key)
        while len(_notes_order) > NOTE_MEMORY:
            _notes_written.pop(_notes_order.pop(0), None)
        if note:
            _notes_held[hold_key(npc, kind)] = (note, time.time())
    return note


def hold_key(npc, kind):
    """A character, a scene, and the mood they are in: see NOTE_HOLD_SECONDS."""
    mood = npc.get("EmotionalState") or {}
    mood = (mood.get("Mood") or "").strip().lower() if isinstance(mood, dict) \
        else ""
    return (npc.get("StringId", ""), kind, mood)


def held_note(npc, kind):
    """The note this character is already being performed with, if it stands."""
    if not NOTE_HOLD_SECONDS:
        return ""
    with _notes_lock:
        note, at = _notes_held.get(hold_key(npc, kind), ("", 0.0))
    if note and time.time() - at <= NOTE_HOLD_SECONDS:
        return note
    return ""


def prewarm_notes(npc, line, kind="dialog"):
    """
    Start writing the notes for a line the moment it is seen.

    Called when the line is QUEUED, so the writing happens while whatever is
    being spoken finishes. By the time the line's turn comes the note is
    usually already in hand, and the wait costs nothing at all.
    """
    if not WRITE_OWN_NOTES or mod_note(npc, line):
        return
    for narrated, text in parts_of(line):
        if narrated or not (text or "").strip():
            continue
        threading.Thread(target=asked_note, args=(dict(npc), text, kind),
                         daemon=True).start()


_anchor_cache = {}


def voice_anchor(npc, voice=""):
    """
    Who is speaking: one sentence, identical for this character every time.

    Built from the voice they are PINNED to rather than the voice the mod sent
    this turn, because the mod hands us a different voice id for the same
    person from one turn to the next (see pin_npc_voice) - and an anchor that
    moved with that would be no anchor at all. A character with a hand-written
    note in npc_voices.json uses that instead, verbatim, which is what that
    field has always been for.
    """
    if not VOICE_ANCHOR:
        return ""
    sid = npc.get("StringId", "") or ""
    pinned = core.pinned_character_instructions(sid)
    if pinned:
        return pinned
    pin = (core._load_npc_voice_pins().get(sid) or {}) if sid else {}
    voice = pin.get("voice") or voice or npc.get("AssignedTTSVoice", "") or ""
    if voice not in _anchor_cache:
        info = core.VOICE_DB.get(voice, {})
        who = {"male": "a man", "female": "a woman"}.get(
            (info.get("gender") or pin.get("gender") or "").lower(),
            "one and the same person")
        # Left with its own capitals: lowercasing the first word to splice it
        # into the sentence turned "British English accent" into "british",
        # and a direction with a typo in it is a direction being read by a
        # machine that notices.
        accent = (core.voice_accent_instructions(voice) or "").strip().rstrip(".")
        _anchor_cache[voice] = (
            f"This is always the same speaker: {who}. "
            + (f"{accent}. " if accent else "")
            + "Keep the pitch, age, accent and timbre identical in every "
              "line; let only the feeling change.")
    return _anchor_cache[voice]


def full_direction(note, npc=None, voice="", continued=False):
    """
    Everything sent with a character's words, always assembled in this order.

    Who they are, then how this line goes, then keep the words, then - if the
    speech is being read in parts - that this is a continuation. Every path
    that speaks a character comes through here, so a line can never go out
    missing a piece the one beside it had.
    """
    bits = []
    anchor = voice_anchor(npc, voice) if npc is not None else ""
    if anchor:
        bits.append(anchor if anchor[-1] in ".!?" else anchor + ".")
    if note:
        bits.append(note if note.strip()[-1] in ".!?" else note.strip() + ".")
    if KEEP_WORDS_EXACT and (note or anchor):
        bits.append(KEEP_WORDS_EXACT)
    out = " ".join(bits)
    if continued and out and PART_OF_A_LINE:
        out += "\n\n" + PART_OF_A_LINE
    return out


def _with_exact_words(note, npc=None, voice=""):
    """The old name for the assembler, kept because the suites call it."""
    return full_direction(note, npc, voice)


# Replies the mod logged with a voice note: (time, response text, note).
_log_notes = collections.deque(maxlen=60)
_log_notes_lock = threading.Lock()


def _same_line(said, want):
    said, want = (said or "").strip(), (want or "").strip()
    return bool(said and want) and (want[:60] in said or said[:60] in want)


def remember_logged_reply(obj):
    """A reply the mod logged as it arrived: keep its note, if it has one."""
    if not isinstance(obj, dict):
        return
    note = obj.get("tts_instructions")
    said = obj.get("response")
    if isinstance(note, str) and note.strip() and isinstance(said, str) and said.strip():
        with _log_notes_lock:
            _log_notes.append((time.time(), said.strip(), note.strip()))


def logged_note(text):
    with _log_notes_lock:
        for _t, said, note in reversed(_log_notes):
            if _same_line(said, text):
                return note
    return ""


def _notes_in_log_lately():
    with _log_notes_lock:
        return bool(_log_notes) and time.time() - _log_notes[-1][0] < 600


def mod_note(npc, text, wait=False):
    """
    The mod's own note, but only if it was written for THIS line.

    Three places it can be: the save's LastTTSInstructions (7.0, or 7.1 with
    the mod's TTS on), the reply as the mod logged it (7.1 with our prompt
    line - the earliest), and the reply stored in the save.
    """
    note = (npc.get("LastTTSInstructions") or "").strip()
    if note and _same_line(npc.get("LastTTSPlayedText") or text, text):
        return note
    deadline = time.time() + (MOD_NOTE_LOG_WAIT if wait and _notes_in_log_lately() else 0)
    while True:
        note = logged_note(text)
        if note:
            return note
        if time.time() >= deadline:
            break
        time.sleep(0.1)
    reply = _stored_reply(npc)
    note = reply.get("tts_instructions")
    if isinstance(note, str) and note.strip() and _same_line(reply.get("response"), text):
        return note.strip()
    return ""


def delivery_note(npc, voice, text=None, kind="dialog"):
    """
    How this line is to be performed: the best note we can get for it.

    Tier 1 is the mod's own note for this very line; tier 2 is one written for
    it on request; tier 3 is composed here from the save. See the settings.
    """
    if USE_MOD_DELIVERY_NOTE:
        note = without_dialect(mod_note(npc, text, wait=text is not None))
        if note:
            return full_direction(note, npc, voice)
    if text is not None and WRITE_OWN_NOTES:
        note = without_voice_words(asked_note(npc, text, kind))
        if note:
            return full_direction(note, npc, voice)
    if text is not None:
        return full_direction(composed_note(npc, text, kind), npc, voice)
    return (voice_anchor(npc, voice)
            or core.pinned_character_instructions(npc.get("StringId", ""))
            or core.voice_accent_instructions(voice))


def parts_of(line):
    """
    The line as (is_narrator, text) pieces, in the order they were written.

    The mod strips the *actions* and speaks only the words; this puts the
    actions back, in the narrator's voice, exactly where they belong.
    """
    out = []
    for who, text in core.split_text(line):
        out.append((who == core.NARRATOR_VOICE, text))
    # If the line opens with speech, give it a short opening piece so the voice
    # can start while the rest is still being made. Only ever the first piece,
    # and only when it is long enough to be worth it: every later seam is free
    # (that piece is already fetched), but a seam still costs a little
    # continuity, so we buy exactly one and only when it saves real waiting.
    if QUICK_OPENING_CHARS and out and not out[0][0] \
            and len(out[0][1]) > QUICK_OPENING_CHARS * 1.2:
        pieces = core._split_sentences(out[0][1], QUICK_OPENING_CHARS)
        rest = " ".join(pieces[1:]).strip() if len(pieces) > 1 else ""
        # Not worth a seam if what is left is a scrap: the saving would be
        # nothing and the line would be cut for no reason.
        if rest and len(rest) >= 60:
            out[0:1] = [(False, pieces[0]), (False, rest)]
    return out


# ============================================================
#  SPEAKING A LINE
# ============================================================

def speak_line(npc, line, group, kind="dialog"):
    """Make a line and speak it (for callers that do not make lines ahead)."""
    play_prepared(prepare_line(npc, line, group, kind))


def prepare_line(npc, line, group, kind="dialog"):
    """
    Speak one line: actions narrated, words in the character's voice.

    The pieces are fetched AHEAD of being played, so the only wait you feel is
    the first one. A long speech is never cut up: it is one piece, because a
    seam in the middle of a sentence is exactly what made the old proxy sound
    stitched together.
    """
    voice = voice_for(npc)
    speed = core._effective_speed(1.0)
    char_speed = CHARACTER_SPEED if CHARACTER_SPEED else speed
    pieces = parts_of(line)
    announced = False
    if group and ANNOUNCE_IN_GROUPS:
        label = core.speaker_label(npc.get("Name"))
        if label and label != _state.get("last_speaker"):
            _state["last_speaker"] = label
            pieces.insert(0, (True, label))
            announced = True
    elif not group:
        _state["last_speaker"] = None

    overheard = (kind == "ambient")
    print(f"\n--- {npc.get('Name')} "
          f"({core.VOICE_DB.get(voice, {}).get('name', voice)}"
          f"{', group' if group else ''}"
          f"{', overheard' if overheard else ''}) ---")
    for narrated, text in pieces:
        print(f"    {'NARR' if narrated else 'SAYS'}: {text[:78]}")

    # The character's words need a performance note, and the best note has to
    # be asked for (2-3 seconds). So every note is asked for NOW, at the same
    # moment as the narrator's action — which is generated and played first, so
    # the asking is usually over before anything is waiting on it. A note that
    # is late or never comes falls back to the composed one, which is ready at
    # once, and nothing is ever left unspoken for want of direction.
    spoken_pieces = [t for narrated, t in pieces if not narrated]
    notes = {}

    # A long speech is broken into parts HERE rather than inside the fetching,
    # so every part is an ordinary piece: generated alongside all the others
    # and played the moment it is its turn. The parts of one speech share the
    # one note written for the whole of it — the note belongs to the line, not
    # to a fragment of it — so each part is remembered with its parent's text.
    expanded = []
    opened = False
    for narrated, text in pieces:
        if (group and QUICK_OPENING_IN_GROUPS and not narrated and not opened
                and len(text) > QUICK_OPENING_IN_GROUPS * 1.2):
            opened = True
            parts = core._split_sentences(text, QUICK_OPENING_IN_GROUPS) or [text]
            rest = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
            if rest and len(rest) >= 60:
                print("    (opening made on its own, to start sooner)")
                expanded.append((False, parts[0], text))
                if LINE_PART_CHARS and len(rest) > LINE_PART_CHARS * 1.3:
                    for part in core._split_sentences(rest, LINE_PART_CHARS) or [rest]:
                        expanded.append((False, part, text))
                else:
                    expanded.append((False, rest, text))
                continue
        if not narrated:
            opened = True
        if narrated or not LINE_PART_CHARS \
                or len(text) <= LINE_PART_CHARS * 1.3:
            expanded.append((narrated, text, text))
            continue
        parts = core._split_sentences(text, LINE_PART_CHARS) or [text]
        if len(parts) < 2:
            expanded.append((narrated, text, text))
            continue
        print(f"    (read in {len(parts)} parts, as the mod does)")
        for part in parts:
            expanded.append((narrated, part, text))

    def write_note(text):
        notes[text] = delivery_note(npc, voice, text, kind)

    note_threads = [threading.Thread(target=write_note, args=(t,), daemon=True)
                    for t in spoken_pieces]
    for t in note_threads:
        t.start()
    # More than one piece in the same voice: tell it they join up, so the
    # second piece does not open like a new line. True as well when one speech
    # was broken into parts, which is the case the clause was written for.
    continued = (len(spoken_pieces) > 1
                 or len(expanded) > len(pieces))

    def note_for_piece(text):
        """Wait for this piece's note, settling for the composed one if late."""
        deadline = time.time() + NOTE_WAIT_SECONDS
        while text not in notes and time.time() < deadline:
            if _state["stop"].is_set():
                break
            time.sleep(0.05)
        note = notes.get(text)
        if note is None:
            print(f"      [note] not written in time — speaking it with "
                  f"what the save already knows")
            note = full_direction(composed_note(npc, text, kind), npc, voice)
        if continued and note:
            note = note + "\n\n" + PART_OF_A_LINE
        return note

    # (text, voice, instructions, speed) — the order fetch() takes them in.
    # A character's piece carries None and looks its note up when it is sent,
    # so the asking and the generating overlap instead of queueing.
    jobs = []
    for narrated, text, whole in expanded:
        if narrated:
            spoken = (core._normalize_narrator_text(text)
                      if core.NARRATOR_NORMALIZE_TEXT else text)
            jobs.append((spoken, core.NARRATOR_VOICE,
                         core.narrator_instructions(),
                         core._narrator_speed(speed)))
        else:
            jobs.append((text, voice, ("note", whole), char_speed))

    # Everything is asked for at once. The narrator's action is short and comes
    # back first, so it plays while the character's long line is still being
    # made — which is why this does not feel like waiting.
    results = [None] * len(jobs)

    def work(i, args):
        t = time.time()
        if isinstance(args[2], tuple) and args[2][0] == "note":
            # A character's words: the note written for the whole speech.
            args = (args[0], args[1], note_for_piece(args[2][1]), args[3])
            print(f"      piece {i+1} note: {str(args[2]).splitlines()[0][:96]}")
        clips = fetch_with_recovery(*args, tag=f"piece {i+1}")
        results[i] = clips
        if clips:
            total = sum(seconds_of(c) for c in clips)
            print(f"      piece {i+1} ready in {time.time()-t:.1f}s "
                  f"({total:.1f}s of audio"
                  + (f", in {len(clips)} parts" if len(clips) > 1 else "") + ")")
        else:
            print(f"      piece {i+1} could not be spoken at all")

    threads = [threading.Thread(target=work, args=(i, a), daemon=True)
               for i, a in enumerate(jobs)]
    for t in threads:
        t.start()
    return {"threads": threads, "results": results, "overheard": overheard,
            "announced": announced, "name": npc.get("Name"), "made_at": time.time()}


def play_prepared(p):
    """Play a line made by prepare_line, in order, catching up if behind."""
    if not p:
        return
    with _queue_cv:
        waiting = sum(1 for q in _queue if q[0] == "line")
    behind = CATCH_UP_AT and waiting >= CATCH_UP_AT
    factor = CATCH_UP_SPEED if behind else 1.0
    if behind:
        print(f"      [catch-up] {waiting} line(s) waiting - "
              f"{'x' + format(factor, '.2f') if factor > 1.0 else 'normal pace'}"
              f"{', no announcement' if p['announced'] and CATCH_UP_SKIPS_ANNOUNCE else ''}")

    started = time.time()
    level = LineLoudness()
    for i, t in enumerate(p["threads"]):
        t.join()
        if _state["stop"].is_set():
            return
        if i == 0:
            waited = time.time() - started
            made = time.time() - p["made_at"]
            print(f"      speaking after {waited:.1f}s"
                  + (f" (made ahead, {made:.1f}s since it was started)" if made - waited > 1.0 else ""))
            if behind and p["announced"] and CATCH_UP_SKIPS_ANNOUNCE:
                continue
        for clip in (p["results"][i] or []):
            # One gain for the whole line: see LineLoudness.
            clip = level.apply(clip)
            if factor > 1.0:
                clip = stretch_speech(clip, factor)
            play(quieten(clip, AMBIENT_VOLUME) if p["overheard"] else clip)


# Lines being made ahead, by the identity of their queue entry. One lock for
# making and taking them: the watcher and the speaker both start lines, and a
# line made twice would also announce its speaker out of order.
_ahead = {}
_ahead_lock = threading.RLock()


def make_ahead():
    """Start making the next waiting lines, in queue order (see PREFETCH_LINES)."""
    if not PREFETCH_LINES:
        return
    with _ahead_lock:
        _make_ahead_locked()


def _make_ahead_locked():
    with _queue_cv:
        upcoming = [q for q in _queue if q[0] == "line"][:PREFETCH_LINES]
        live = {id(q[1]) for q in _queue if q[0] == "line"}
    for key in [k for k in _ahead if k not in live]:
        _ahead.pop(key, None)              # dropped from the queue (hushed)
    for q in upcoming:
        key = id(q[1])
        if key not in _ahead:
            npc, line, group, scene = q[1]
            _ahead[key] = prepare_line(npc, line, group, scene)


# ============================================================
#  WATCHING THE SAVE FOLDER
# ============================================================

_state = {"seen": {}, "last_speaker": None,
          "stop": threading.Event(),
          "skip": threading.Event(),       # cut off whatever is being read
          "reading_events": False, "reading_letter": False,
          "speaking_ambient": False, "your_scene_at": 0.0,
          "event_index": 0, "event_pressed_at": 0.0, "event_fired_at": 0.0,
          "letter_index": 0, "letter_pressed_at": 0.0,
          "reading_memory": False,
          "memory_index": 0, "memory_pressed_at": 0.0,
          "open_page": None, "open_page_at": 0.0}
# Each entry is (kind, payload): ("line", (npc, text, group)) for something a
# character said, ("event", (text, label)) for a reading of the day's events.
_queue = []
_queue_cv = threading.Condition()


def scan(prime=False):
    """New lines since the last look. The player's own turns are skipped."""
    for path, data in core.load_all_npc_data().items():
        history = data.get("ConversationHistory") or []
        known = _state["seen"].get(path)
        if known is None:
            _state["seen"][path] = len(history) if (prime or not SPEAK_BACKLOG) else 0
            known = _state["seen"][path]
        if len(history) < known:            # file reset, or a new campaign
            _state["seen"][path] = len(history)
            continue
        if len(history) == known:
            continue
        fresh = history[known:]
        _state["seen"][path] = len(history)
        if prime:
            continue
        own = data.get("StringId", "")
        kind = scene_kind(data)
        if not kind:
            # No tag at all. Only your own scenes are read; see the settings.
            if ONLY_UNTAGGED_SCENES_WITH_YOU and not you_are_in_this(data):
                print(f"  [scene] {data.get('Name')} is talking to someone "
                      f"else, in a scene with no tag on it — not read.")
                continue
            kind = "dialog"
        group = (kind == "group")
        if kind == "letter":
            # A letter is read when you ask for it, never as it lands. Under
            # 7.0.3 it arrives as a scene rather than a delivery record, so
            # this is what keeps it from being spoken like a conversation.
            if not SPEAK_LETTERS_ON_ARRIVAL:
                print(f"  [letters] {data.get('Name')} has written to you — "
                      f"press {LETTER_HOTKEY.upper()} to hear it.")
                continue
        if kind == "duel" and not NARRATE_DUELS:
            continue
        if kind == "ambient":
            if not NARRATE_AMBIENT:
                continue
            # Your own scene always wins: nothing is overheard while you are in
            # a conversation, and anything already queued from the room is
            # dropped the moment someone speaks to you (below).
            if in_your_conversation():
                print(f"  [ambient] {data.get('Name')} is talking nearby — "
                      f"not while you are in a conversation.")
                continue
        else:
            _state["your_scene_at"] = time.time()
            if AMBIENT_YIELDS_TO_YOU:
                hush_ambient(f"{data.get('Name')} is speaking to you")

        letters = set() if SPEAK_LETTERS_ON_ARRIVAL else delivered_lines(data)
        heard_by = spoken_by(data)
        for entry in fresh:
            speaker, body = core._entry_speaker_id(entry)
            if speaker is None:
                # No id in the label: a duel taunt, or anything else the mod
                # writes plainly. The observations say who spoke it.
                said = (entry or "").strip()
                speaker = heard_by.get(said)
                if speaker and ": " in said:
                    body = said.split(": ", 1)[1]
            if (VOICE_BACKGROUND_CHARACTERS and speaker and speaker != own
                    and speaker.startswith("scene_agent") and (body or "").strip()):
                who = background_character(entry)
                heard = (speaker, body.strip())
                if who and heard not in _background_heard and early_already_said(body):
                    _background_heard.append(heard)
                    continue
                if who and heard not in _background_heard:
                    _background_heard.append(heard)
                    del _background_heard[:-200]
                    bg = background_npc(*who)
                    print(f"  [background] {who[1]} speaks (heard in {data.get('Name')}'s file).")
                    with _queue_cv:
                        _queue.append(("line", (bg, body, group, kind)))
                        _queue_cv.notify()
                    if _state.get("speaking_line"):
                        make_ahead()
                continue
            if speaker != own or not (body or "").strip():
                continue
            # A letter is written into the history exactly like speech. It is
            # not read out as it lands — it waits for the letter key.
            if (entry or "").strip() in letters:
                print(f"  [letters] {data.get('Name')} sent a letter — "
                      f"press {LETTER_HOTKEY.upper()} to hear it.")
                continue
            if kind != "ambient" and early_already_said(body):
                continue                  # already spoken, from the mod's log
            prewarm_notes(data, body, kind)
            with _queue_cv:
                _queue.append(("line", (data, body, group, kind)))
                _queue_cv.notify()
            if kind == "duel" and DUEL_ONLY_LATEST:
                drop_stale_duel_lines()
            # Start making it now if it is next in line or nearly so, while
            # whatever is playing finishes.
            if _state.get("speaking_line"):
                make_ahead()


# How often to check whether another campaign is being played (see
# core.FOLLOW_ACTIVE_CAMPAIGN). Loading a different campaign is picked up
# within this many seconds of its first character file being written.
CAMPAIGN_CHECK_SECONDS = 10.0


def watcher():
    try:
        ensure_note_prompt(core.get_npc_folder())
    except Exception:
        pass
    try:
        scan(prime=True)
        print(f"  Watching {len(_state['seen'])} character file(s).")
    except Exception as e:
        print(f"  Could not read the save folder: {e}")
    checked = time.time()
    while not _state["stop"].is_set():
        time.sleep(POLL_SECONDS)
        if time.time() - checked > CAMPAIGN_CHECK_SECONDS:
            checked = time.time()
            try:
                ensure_note_prompt(core.get_npc_folder())
            except Exception:
                pass
            try:
                moved = core.switch_campaign_if_needed()
                if moved:
                    _state["seen"].clear()
                    scan(prime=True)
                    print(f"  [campaign] Now following {os.path.basename(moved)} "
                          f"({len(_state['seen'])} character files).")
            except Exception as e:
                print(f"  [campaign] Could not check for another campaign: {e}")
        try:
            scan()
        except Exception as e:
            print(f"  Scan failed: {e}")
            time.sleep(2.0)


# ============================================================
#  FOLLOWING THE MOD'S OWN LOG (2026-11-23)
# ============================================================
# In a conversation scene AI Influence 7.0 writes a line into the save file
# only when it has FINISHED showing it ("CloseSpokenLine"), so a line read from
# the save started a whole line late: Elenya's went on screen at 10:12:05 and
# reached the save at 10:12:48. The mod logs the full text the moment it has it
# ("SOCIAL_PARSED") and the moment the character starts talking ("speaks out
# loud"); with both in hand the line is queued at once. When the save file
# catches up, the same line is recognised and not spoken again. Only scenes the
# player is in ("encounter #N (player)"); overheard ones are left to the save.
# Needs the mod's log on (it is by default). False = save files only.
FOLLOW_MOD_LOG = True
MOD_LOG_POLL_SECONDS = 0.2
# A character who has started talking but whose words are not in the log after
# this long is left to the save file; words never spoken are dropped after the
# longer wait (the player cut in, or the scene ended).
MOD_LOG_WORDS_WAIT = 20.0
MOD_LOG_SPOKEN_WAIT = 180.0

_early_said = []                 # (time, normalised opening) spoken from the log
_early_payloads = set()          # id() of queue payloads that came from the log
_LOG_TS = re.compile(r"^\[\d\d:\d\d:\d\d(?:\.\d+)?\] ")
_ACTS = " | \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u044f:"     # " | действия:"
# The tail after the words: " | действия: ..." up to 7.0. 7.1.0 replaced the
# actions list with "deeds", and the label may have changed with it. Any
# one-word label after " | " ends the spoken words, so a renamed tail is
# never read aloud.
_TAIL_RE = re.compile(r" \| [A-Za-z\u0400-\u04FF_]{3,24}:")


def _tail_at(text):
    """Where the words stop and the parsed tail begins, or -1."""
    last = -1
    for m in _TAIL_RE.finditer(text):
        last = m.start()
    return last
_REPLY = "\u0440\u0435\u043f\u043b\u0438\u043a\u0430"              # "реплика"


def _said_key(text):
    """The opening of a line, letters and digits only, for matching."""
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())[:80]


def early_already_said(body):
    """True (once) when this saved line was already spoken from the log."""
    key = _said_key(body)
    if len(key) < 12:
        return False
    now = time.time()
    _early_said[:] = [e for e in _early_said if now - e[0] < 900]
    for i, (_t, k) in enumerate(_early_said):
        n = min(len(k), len(key))
        if n >= 12 and k[:n] == key[:n]:
            del _early_said[i]
            return True
    return False


class ModLogFollower:
    def __init__(self, path):
        self.path = path
        self.pos = 0
        self.tail = b""
        self.enc_kind = {}        # encounter number -> "player" / "ambient"
        self.members = {}         # encounter number -> names who joined
        self.words = {}           # name -> (time, encounter, text) parsed, not yet spoken
        self.talking = {}         # name -> (time, encounter) speaking, words not yet in
        self.open_parse = None    # [encounter, name, text] of a reply still running on
        self.open_json = None     # a logged AI reply still running on to more lines
        self.queued = []          # (name, text) handed on, for tests

    # --- reading -------------------------------------------------------
    def seed(self):
        """Learn the scenes already going on, without speaking anything."""
        size = os.path.getsize(self.path)
        with open(self.path, "rb") as f:
            f.seek(max(0, size - 8_000_000))
            chunk = f.read(size - f.tell())
        self.pos = size
        for raw in chunk.split(b"\n")[1:]:
            self.handle(raw.decode("utf-8", "replace").rstrip("\r"), live=False)
        self.words.clear()
        self.talking.clear()
        self.open_parse = None

    def poll(self):
        size = os.path.getsize(self.path)
        if size < self.pos:                  # log started afresh
            self.pos, self.tail = 0, b""
        if size > self.pos:
            with open(self.path, "rb") as f:
                f.seek(self.pos)
                data = f.read(size - self.pos)
            self.pos += len(data)
            lines = (self.tail + data).split(b"\n")
            self.tail = lines.pop()
            for raw in lines:
                self.handle(raw.decode("utf-8", "replace").rstrip("\r"), live=True)
        self.expire()

    def expire(self):
        now = time.time()
        for name, (t, _e) in list(self.talking.items()):
            if now - t > MOD_LOG_WORDS_WAIT:
                del self.talking[name]
        for name, (t, _e, _x) in list(self.words.items()):
            if now - t > MOD_LOG_SPOKEN_WAIT:
                del self.words[name]

    # --- one line of the log --------------------------------------------
    def handle(self, line, live):
        if self.open_json is not None:
            if _LOG_TS.match(line):
                self.close_json()
            else:
                self.open_json.append(line)
                if len(self.open_json) > 400:
                    self.open_json = None
                return
        if "Cleaned AI response: " in line or "[SOCIAL_RAW_RESPONSE]" in line:
            if "Cleaned AI response: " in line:
                body = line.split("Cleaned AI response: ", 1)[1]
            else:
                m = re.search(r"\[SOCIAL_RAW_RESPONSE\] #\d+ [^:]+: (.*)$", line)
                body = m.group(1) if m else ""
            if live and body.strip():
                self.open_json = [body]
                if body.strip().endswith("}"):
                    self.close_json()
            return
        if self.open_parse is not None:
            if _LOG_TS.match(line):          # the reply ended without its tail
                self.close_parse(self.open_parse[2], live)
            else:
                self.open_parse[2] += "\n" + line
                if _tail_at(line) >= 0:
                    whole = self.open_parse[2]
                    self.close_parse(whole[:_tail_at(whole)], live)
                return
        if "[SOCIAL" not in line:
            return
        m = re.search(r"\[SOCIAL\] encounter #(\d+) \((\w+)\) (started|dissolved)", line)
        if m:
            n = m.group(1)
            if m.group(3) == "started":
                self.enc_kind[n] = m.group(2)
                self.members[n] = set()
            else:
                self.enc_kind.pop(n, None)
                self.members.pop(n, None)
            return
        m = re.search(r"\[SOCIAL_PARSED\] #(\d+) (.+?) \| " + _REPLY + r": (.*)$", line)
        if m:
            n, name, rest = m.groups()
            self.open_parse = [n, name, rest]
            if _tail_at(rest) >= 0:
                self.close_parse(rest[:_tail_at(rest)], live)
            return
        m = re.search(r"\[SOCIAL\] encounter #(\d+): (.+?) (joined|speaks out loud|"
                      r"was cut off by the player|removed)", line)
        if not m:
            m = re.search(r"\[SOCIAL\] encounter #(\d+): the line of (.+?) (is stopped)", line)
        if not m:
            return
        n, name, what = m.groups()
        if what == "joined":
            self.members.setdefault(n, set()).add(name)
        elif what == "removed":
            self.members.get(n, set()).discard(name)
        elif what == "speaks out loud":
            if live:
                self.talking[name] = (time.time(), n)
                self.ready(name)
        elif live:
            self.words.pop(name, None)
            self.talking.pop(name, None)
            if STOP_VOICE_WHEN_YOU_TYPE:
                cut_off_early(name)

    def close_json(self):
        text, self.open_json = "\n".join(self.open_json or []), None
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
        a, b = text.find("{"), text.rfind("}")
        if a < 0 or b <= a:
            return
        try:
            remember_logged_reply(json.loads(text[a:b + 1]))
        except Exception:
            pass

    def close_parse(self, text, live):
        n, name, _ = self.open_parse
        self.open_parse = None
        if live and text.strip():
            self.words[name] = (time.time(), n, text.strip())
            self.ready(name)

    # --- both halves in: queue it ---------------------------------------
    def ready(self, name):
        if name not in self.talking or name not in self.words:
            return
        _t, n = self.talking.pop(name)
        _t2, _n2, text = self.words.pop(name)
        if self.enc_kind.get(n) != "player":
            return                           # overheard, or a scene begun before we looked
        group = len(self.members.get(n, ())) > 1
        self.queued.append((name, text, group))
        if self.dry_run:
            return
        kind = "group" if group else "dialog"
        npc = npc_by_name(name)
        if npc is None:
            words = re.findall(r"[a-z]+", name.lower())
            gender = "female" if any(w in FEMALE_TITLE_WORDS for w in words) else "male"
            npc = background_npc("log:" + name, name, gender)
        _early_said.append((time.time(), _said_key(text)))
        _state["your_scene_at"] = time.time()
        if AMBIENT_YIELDS_TO_YOU:
            hush_ambient(f"{name} is speaking to you")
        print(f"  [live] {name} started talking - taken from the mod's log.")
        prewarm_notes(npc, text, kind)
        payload = (npc, text, group, kind)
        _early_payloads.add(id(payload))
        with _queue_cv:
            _queue.append(("line", payload))
            _queue_cv.notify()
        if _state.get("speaking_line"):
            make_ahead()

    dry_run = False


def npc_by_name(name):
    for data in core.load_all_npc_data().values():
        if data.get("Name") == name:
            return data
    return None


def cut_off_early(name):
    """The player cut in: stop that character's line and anything queued of theirs."""
    with _queue_cv:
        keep = [q for q in _queue if not (q[0] == "line" and id(q[1]) in _early_payloads
                                          and q[1][0].get("Name") == name)]
        dropped = len(_queue) - len(keep)
        _queue[:] = keep
    if _state.get("speaking_name") == name and _state.get("speaking_early"):
        _state["skip"].set()
        stop_sound()
        print(f"  [live] You cut in - {name} stops.")
    elif dropped:
        print(f"  [live] You cut in - {name}'s waiting line dropped.")


def _mod_log_path():
    folder = core.get_npc_folder() or ""
    return os.path.normpath(os.path.join(folder, "..", "..", "logs", "mod_log.txt"))


def mod_log_follower():
    if not FOLLOW_MOD_LOG:
        return
    follower, said, last_check = None, False, 0.0
    while not _state["stop"].is_set():
        time.sleep(MOD_LOG_POLL_SECONDS)
        # Find the log again now and then: the campaign (and so the mod's
        # folder) can change while the narrator runs.
        if follower is None or time.time() - last_check > CAMPAIGN_CHECK_SECONDS:
            last_check = time.time()
            path = _mod_log_path()
            if follower is None or os.path.normcase(path) != os.path.normcase(follower.path):
                if not os.path.exists(path):
                    if not said:
                        said = True
                        print("  [live] The mod's log is not there yet - reading the save files.")
                    follower = None
                    continue
                try:
                    follower = ModLogFollower(path)
                    follower.seed()
                    print("  [live] Following the mod's log, so a speaker is heard as they start.")
                except Exception as e:
                    print(f"  [live] Could not read the mod's log ({e}) - save files only.")
                    follower = None
                    continue
        try:
            follower.poll()
        except Exception as e:
            print(f"  [live] Log read failed: {e}")
            time.sleep(2.0)


def speaker():
    """One line at a time, in the order they were written."""
    while not _state["stop"].is_set():
        with _queue_cv:
            while not _queue and not _state["stop"].is_set():
                _queue_cv.wait(0.5)
            if _state["stop"].is_set():
                return
            kind, payload = _queue.pop(0)
        _state["skip"].clear()
        try:
            if kind == "line":
                npc, line, group, scene = payload
                with _ahead_lock:
                    prepared = _ahead.pop(id(payload), None)
                    if prepared is None:
                        prepared = prepare_line(npc, line, group, scene)
                    make_ahead()              # the next lines are made while this one plays
                _state["speaking_ambient"] = (scene == "ambient")
                _state["speaking_line"] = True
                _state["speaking_name"] = npc.get("Name")
                _state["speaking_early"] = id(payload) in _early_payloads
                _early_payloads.discard(id(payload))
                try:
                    play_prepared(prepared)
                finally:
                    _state["speaking_ambient"] = False
                    _state["speaking_line"] = False
                    _state["speaking_name"] = None
                    _state["speaking_early"] = False
            else:
                text, label = payload
                flag = {"event": "reading_events",
                        "letter": "reading_letter",
                        "memory": "reading_memory"}[kind]
                _state[flag] = True
                try:
                    speak_as_narrator(text, label)
                finally:
                    _state[flag] = False
        except Exception as e:
            print(f"  Could not speak that: {e}")


# ============================================================
#  WORLD EVENTS
# ============================================================

def speak_as_narrator(text, label):
    """
    Read a passage in the narrator's voice, in pieces fetched all at once.

    Same trick as a character's line: a short opening piece so the voice starts
    quickly, the rest in larger pieces behind it. Stops at once if interrupted.

    A reading like this — a day of events, a letter, a page of someone's
    memories — is the LONGEST thing the narrator ever says, and it is always in
    pieces. Until 2026-11-16 each piece was generated knowing nothing of the
    others, so the reading restarted and signed off over and over within one
    passage. Every piece is now told it is part of a continuous reading, which
    is the same clause the characters got, and the mod's own wording.
    """
    pieces = core._split_sentences(text, EVENT_OPENING_CHARS) or [text]
    first, rest = pieces[0], " ".join(pieces[1:]).strip()
    jobs = [first] + (core._split_sentences(rest, EVENT_CHUNK_CHARS) if rest else [])
    jobs = [j for j in jobs if j and j.strip()]
    reading = core.narrator_instructions()
    if len(jobs) > 1:
        reading = (reading or "") + "\n\n" + PART_OF_A_LINE
    print(f"  {label}: {len(jobs)} piece(s)"
          + (", read as one continuous passage" if len(jobs) > 1 else ""))

    clips = [None] * len(jobs)
    ready = [threading.Event() for _ in jobs]
    asked = set()
    lock = threading.Lock()

    def work(i, retry=False):
        try:
            clip = fetch(core._normalize_narrator_text(jobs[i]),
                         core.NARRATOR_VOICE, reading,
                         core._narrator_speed(core._effective_speed(1.0)))
            with lock:
                if clips[i] is None:
                    clips[i] = clip
        except Exception as e:
            print(f"      piece {i+1}{' (asked again)' if retry else ''} failed: {e}")
        finally:
            # A first request that fails while its retry is still out must not
            # end the wait; the retry's own answer (or failure) does.
            if retry or clips[i] is not None or i not in _retried:
                ready[i].set()

    _retried = set()

    def ask(i, retry=False):
        if i >= len(jobs) or (i in asked and not retry):
            return
        if _state["skip"].is_set() or _state["stop"].is_set():
            return
        asked.add(i)
        threading.Thread(target=work, args=(i, retry), daemon=True).start()

    for i in range(min(len(jobs), READING_AHEAD + 1)):
        ask(i)
    started = time.time()
    for i in range(len(jobs)):
        waited = 0.0
        while not ready[i].wait(0.25):
            if _state["skip"].is_set() or _state["stop"].is_set():
                return
            waited += 0.25
            if waited >= READING_STUCK_SECONDS and i not in _retried:
                _retried.add(i)
                print(f"      piece {i+1} of {len(jobs)} still not back after "
                      f"{waited:.0f}s - asking for it again")
                ask(i, retry=True)
        if _state["skip"].is_set() or _state["stop"].is_set():
            return
        if i == 0:
            print(f"      reading after {time.time()-started:.1f}s")
        ask(i + READING_AHEAD + 1)       # keep the same distance ahead
        if clips[i] is None:
            print(f"      piece {i+1} of {len(jobs)} could not be made - skipped")
        play(clips[i])


def events_text(index):
    """One campaign day's events as a single passage, oldest arrival first."""
    days = core.group_world_events_by_day()
    if not days:
        print("  [events] No world events recorded yet.")
        return None, None, 0
    index = max(0, min(index, len(days) - 1))
    day, events = days[index]
    parts = [t for t in (core._event_speech(e) for e in events) if t]
    if not parts:
        return None, None, len(days)
    text = " ".join(core._ensure_sentence_punctuation(t) for t in parts)
    where = ("the latest day" if index == 0
             else "the day before" if index == 1
             else f"{index} days further back")
    return text, f"[events] campaign day {day}, {where} ({len(parts)} event(s))", len(days)


def on_event_key():
    """
    Press once to hear the newest day. Press again while it reads to cut it off
    and hear the day before, and so on back through the record.
    """
    now = time.time()
    reading = _state["reading_events"]
    if reading and now - _state["event_pressed_at"] > 0.5:
        # Interrupt what is being read and step back a day.
        _state["event_index"] += 1
        _state["skip"].set()
        stop_sound()
        with _queue_cv:
            _queue[:] = [q for q in _queue if q[0] != "event"]
            _queue_cv.notify()
        print("  [events] Cut off — moving to the day before.")
    elif not reading:
        _state["event_index"] = 0
    _state["event_pressed_at"] = now
    text, label, total = events_text(_state["event_index"])
    if not text:
        return
    with _queue_cv:
        _queue.append(("event", (text, label)))
        _queue_cv.notify()


# ============================================================
#  LETTERS
# ============================================================

def delivered_lines(npc):
    """
    The history lines of this character that are LETTERS, not speech.

    Every delivery leaves a record holding the exact line it wrote into the
    history, so this is an identity check, not a guess.
    """
    lines = set()
    for rec in (npc.get("InformationHistoryEntries") or []):
        if rec.get("Kind") != "delivery" or rec.get("Deleted"):
            continue
        line = (rec.get("Line") or "").strip()
        if line:
            lines.add(line)
    return lines


def collect_letters():
    """
    Every letter still on record, newest first, read fresh from the save.

    Two shapes, because 7.0.3 changed this. The new one is a scene tagged
    "letter/npc" in the character's dialogue observations — a letter from them
    to you; "letter/player" is your own reply and is not read back at you. The
    old one is an InformationHistoryEntries record of Kind "delivery", which
    older letters in an existing campaign still have. Both are gathered and
    the same letter is never listed twice.
    """
    out, seen = [], set()

    def add(text, sender, day, private):
        text = (text or "").strip()
        key = text[:120]
        if not text or key in seen:
            return
        seen.add(key)
        out.append({"text": text, "sender": sender or "someone",
                    "day": day or 0.0, "private": private})

    for _path, data in core.load_all_npc_data().items():
        name = data.get("Name")
        for o in (data.get("DialogueObservations") or []):
            if not isinstance(o, dict):
                continue
            tag = str(o.get("source_tag") or o.get("scene_id") or "")
            if not tag.startswith("letter"):
                continue
            if o.get("is_player") or tag.startswith("letter/player"):
                continue                       # your own letter, not theirs
            add(o.get("canonical_line"), o.get("speaker_name") or name,
                o.get("campaign_days"), True)
        for rec in (data.get("InformationHistoryEntries") or []):
            if not isinstance(rec, dict):
                continue
            if rec.get("Kind") != "delivery" or rec.get("Deleted"):
                continue
            add(rec.get("NativeText"), name, rec.get("Day"),
                rec.get("Secrecy") == "private")

    out.sort(key=lambda r: -r["day"])
    return out


def on_letter_key():
    """Newest letter on the first press; each further press steps back one."""
    now = time.time()
    if _state["reading_letter"] and now - _state["letter_pressed_at"] > 0.5:
        _state["letter_index"] += 1
        _state["skip"].set()
        stop_sound()
        with _queue_cv:
            _queue[:] = [q for q in _queue if q[0] != "letter"]
            _queue_cv.notify()
        print("  [letters] Cut off — moving to the letter before.")
    elif not _state["reading_letter"]:
        _state["letter_index"] = 0
    _state["letter_pressed_at"] = now

    letters = collect_letters()
    if not letters:
        print("  [letters] No letters have arrived yet.")
        return
    index = max(0, min(_state["letter_index"], len(letters) - 1))
    _state["letter_index"] = index
    letter = letters[index]
    text = letter["text"]
    if ANNOUNCE_SENDER:
        text = f"A letter from {letter['sender']}. " + text
    where = ("the newest" if index == 0
             else "the one before" if index == 1
             else f"{index} letters further back")
    label = f"[letters] from {letter['sender']} ({where} of {len(letters)})"
    with _queue_cv:
        _queue.append(("letter", (text, label)))
        _queue_cv.notify()


# ============================================================
#  THE MEMORY BOOK
# ============================================================

def collect_memories():
    """
    Every memory in the book, newest first — the same order the book shows.

    A memory belongs to the character who remembers it: 7.0 keeps it in that
    character's own file under "Memories", with a title, the campaign day and
    a written summary, which is the prose the page displays. The book simply
    gathers all of them and sorts by day, so we do the same and the numbering
    matches what is on screen.
    """
    out, seen = [], set()
    for _path, data in core.load_all_npc_data().items():
        owner = data.get("Name")
        for m in (data.get("Memories") or []):
            if not isinstance(m, dict):
                continue
            story = (m.get("summary") or m.get("memory_text") or "").strip()
            if not story:
                continue
            key = m.get("id") or story[:120]
            if key in seen:
                continue
            seen.add(key)
            out.append({"id": m.get("id") or "",
                        "title": (m.get("title") or "").strip(),
                        "story": story, "owner": owner,
                        "day": m.get("campaign_day") or 0.0})
    out.sort(key=lambda r: -r["day"])
    return out


def open_page():
    """
    The page of the book on screen right now, or None.

    Filled in by the hook in the book's own page; a report that has stopped
    arriving means the book was closed, so it goes stale on its own.
    """
    if not FOLLOW_OPEN_PAGE:
        return None
    page = _state["open_page"]
    if not page:
        return None
    if time.time() - _state["open_page_at"] > BOOK_REPORT_SECONDS:
        return None
    return page


def _match_open_page(book, page):
    """
    Which entry of OUR book the page on screen is, or None.

    The id first, and in practice always: the book and the save file call a
    memory by the same id, so this needs no guessing and holds in any
    language, in any campaign, however the memory is titled. The rest is
    there only for a page that somehow arrives without one.
    """
    if not page or not book:
        return None

    ident = (page.get("id") or "").strip()
    if ident:
        for i, m in enumerate(book):
            if m.get("id") == ident:
                return i
        # An id we do not have: a memory formed since we last read the save.
        # Better to say nothing than to read the wrong page.
        return None

    def plain(x):
        return re.sub(r"[^a-z0-9]+", "", (x or "").lower())

    title = plain(page.get("title"))
    if title:
        hits = [i for i, m in enumerate(book) if plain(m["title"]) == title]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            # Two memories share a title: the byline under the page carries
            # who remembers it, which settles it.
            owner = plain(page.get("meta"))
            for i in hits:
                if owner and plain(book[i]["owner"]) in owner:
                    return i
            return hits[0]

    # No title to go on — the counter at the foot reads "3 of 12", and the
    # book is in the same order we are.
    nums = re.findall(r"\d+", page.get("counter") or "")
    if len(nums) == 2 and int(nums[1]) == len(book):
        n = int(nums[0]) - 1
        if 0 <= n < len(book):
            return n
    return None


def book_listener():
    """
    Listen on the loopback address for the book saying which page is open.

    Bound to this machine only. It answers the book's "are you there" with a
    word of identification, and every report with a single transparent pixel.
    """
    if not FOLLOW_OPEN_PAGE:
        return
    import http.server
    import json as _json
    import urllib.parse

    PIXEL = (b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
             b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
             b"\x00\x00\x02\x02D\x01\x00;")

    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self):
            try:
                parsed = urllib.parse.urlparse(self.path)
                q = urllib.parse.parse_qs(parsed.query)
                one = lambda k: (q.get(k) or [""])[0]
                if parsed.path == "/narrator/hello":
                    body = _json.dumps({"narrator": "bannerlord-tts",
                                        "hook": 2}).encode()
                    self.send_response(200)
                    # The book is served from a port of the mod's choosing, so
                    # it is a different origin from ours and must be allowed
                    # to read this one answer.
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if parsed.path == "/book":
                    if one("open") == "1":
                        page = {"id": one("id"), "title": one("title"),
                                "meta": one("meta"), "counter": one("counter")}
                        was = _state["open_page"]
                        _state["open_page"] = page
                        _state["open_page_at"] = time.time()
                        if not was or was.get("id") != page["id"] \
                                or was.get("title") != page["title"]:
                            print(f"  [book] Open at: {page['title'] or '?'}"
                                  f" ({page['counter']})")
                    else:
                        if _state["open_page"]:
                            print("  [book] Closed.")
                        _state["open_page"] = None
            except Exception:
                pass
            self.send_response(200)
            self.send_header("Content-Type", "image/gif")
            self.send_header("Content-Length", str(len(PIXEL)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(PIXEL)

        def log_message(self, *a):
            pass                      # the console has better things to say

    class OnePerPort(http.server.ThreadingHTTPServer):
        # Windows lets a second program bind a port another one is already
        # listening on when SO_REUSEADDR is set, and then hands connections
        # to whichever it pleases. Python turns that option on by default, so
        # without this a second narrator would quietly steal half the book's
        # reports from the first — which is exactly what happened in testing
        # while an older narrator was still running (2026-11-16).
        allow_reuse_address = False

        def handle_error(self, request, client_address):
            # The book page closing while we answer it: harmless, and it used
            # to print a whole traceback into the log each time.
            if isinstance(sys.exc_info()[1], (ConnectionError, OSError)):
                return
            super().handle_error(request, client_address)

    srv = None
    for port in BOOK_REPORT_PORTS:
        try:
            srv = OnePerPort(("127.0.0.1", port), Handler)
            break
        except OSError:
            continue                 # that one is taken; the page tries them all
    if srv is None:
        print(f"  [book] Every port is taken, so {MEMORY_HOTKEY.upper()} will "
              f"start at the top of the book instead of your open page.")
        return
    srv.daemon_threads = True
    _state["book_port"] = srv.server_address[1]
    print(f"  [book] Following the Memory Book on port "
          f"{srv.server_address[1]}.")
    try:
        while not _state["stop"].is_set():
            srv.handle_request()
    finally:
        srv.server_close()


def on_memory_key():
    """Top of the book on the first press; each further press steps down one."""
    now = time.time()
    if _state["reading_memory"] and now - _state["memory_pressed_at"] > 0.5:
        _state["memory_index"] += 1
        _state["skip"].set()
        stop_sound()
        with _queue_cv:
            _queue[:] = [q for q in _queue if q[0] != "memory"]
            _queue_cv.notify()
        print("  [memories] Cut off — moving down the book.")
    elif not _state["reading_memory"]:
        _state["memory_index"] = 0
    _state["memory_pressed_at"] = now

    book = collect_memories()
    if not book:
        print("  [memories] The book is still empty.")
        return

    # If the book is open in front of you, read THAT page. Turning the page
    # and pressing again reads the new one; pressing again without turning it
    # steps on down the book, as it does when the book is shut.
    on_screen = _match_open_page(book, open_page())
    if on_screen is not None and not _state["reading_memory"]:
        _state["memory_index"] = on_screen
    elif on_screen is not None and on_screen != _state.get("read_page_was"):
        _state["memory_index"] = on_screen

    index = max(0, min(_state["memory_index"], len(book) - 1))
    _state["memory_index"] = index
    _state["read_page_was"] = on_screen
    page = book[index]

    opening = []
    if ANNOUNCE_MEMORY_TITLE and page["title"]:
        opening.append(core._ensure_sentence_punctuation(page["title"]))
    if ANNOUNCE_MEMORY_OWNER and page["owner"]:
        opening.append(f"Remembered by {page['owner']}.")
    text = " ".join(opening + [page["story"]]).strip()

    where = ("the page you have open" if on_screen == index
             else "the top of the book" if index == 0
             else "the one below it" if index == 1
             else f"{index} pages down")
    label = (f"[memories] {page['title'] or 'a memory'} "
             f"({where} of {len(book)})")
    with _queue_cv:
        _queue.append(("memory", (text, label)))
        _queue_cv.notify()


def start_book_listener():
    """
    Start listening, and make sure the book knows how to reach us.

    The hook is put in (or repaired) here rather than left to the player,
    because an AI Influence update silently replaces the page it lives in.
    Writing only happens when the page would really change.
    """
    if not (FOLLOW_OPEN_PAGE and READ_MEMORIES):
        return
    threading.Thread(target=book_listener, daemon=True).start()
    if not INSTALL_BOOK_HOOK:
        return
    try:
        import MEMORY_BOOK_HOOK as bookhook
        ok, what = bookhook.install(ports=BOOK_REPORT_PORTS,
                                    save_folder=core.get_npc_folder())
    except Exception as e:
        ok, what = False, f"could not be set up ({e})"
    print(f"  [book] Memory Book hook: {what}."
          + ("" if ok else f" {MEMORY_HOTKEY.upper()} will start at the top "
                           f"of the book."))


def hotkey_watchers():
    """
    Watch the key two ways, because neither alone is enough.

    Windows will not deliver a registered hotkey to us while a window running
    with higher rights has focus, which the game sometimes does; reading the
    key's own state still works there. Registering as well means the key is
    caught even when the game swallows it.
    """
    if os.name != "nt":
        return
    keys = []
    if READ_EVENTS:
        keys.append(("events", EVENT_HOTKEY, on_event_key,
                     "the latest day's events; again to step back a day"))
    if READ_LETTERS:
        keys.append(("letters", LETTER_HOTKEY, on_letter_key,
                     "the newest letter; again for the one before"))
    if READ_MEMORIES:
        keys.append(("memories", MEMORY_HOTKEY, on_memory_key,
                     "the top of the memory book; again to step down it"))
    if not keys:
        return

    fired = {}

    def fire(label, action):
        if time.time() - fired.get(label, 0.0) < 0.4:
            return                       # one press, one reading
        fired[label] = time.time()
        try:
            action()
        except Exception as e:
            print(f"  [{label}] Could not read it: {e}")

    parsed = []
    for label, spec, action, blurb in keys:
        mods, vk = core._parse_hotkey(spec)
        if not vk:
            print(f"  [{label}] Could not understand {spec!r} — no hotkey.")
            continue
        parsed.append((label, spec, action, blurb, mods, vk))

    def registered():
        # All of them on ONE thread: Windows delivers a registered hotkey to
        # whichever thread registered it, so a second thread would never hear
        # about the first thread's keys.
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        mine = {}
        for i, (label, _spec, action, _b, mods, vk) in enumerate(parsed, start=1):
            if user32.RegisterHotKey(None, i, mods | 0x4000, vk):
                mine[i] = (label, action)
        if not mine:
            return                       # taken by something else; polling covers us
        msg = wintypes.MSG()
        try:
            while not _state["stop"].is_set():
                if user32.GetMessageW(ctypes.byref(msg), None, 0, 0) in (0, -1):
                    break
                if msg.message == 0x0312 and msg.wParam in mine:
                    fire(*mine[msg.wParam])
        finally:
            for i in mine:
                user32.UnregisterHotKey(None, i)

    def polled():
        import ctypes
        user32 = ctypes.windll.user32
        watch = [{"label": l, "action": a, "vk": vk,
                  "mods": [m for m in core._MOD_VKS if mods & m], "down": False}
                 for l, _s, a, _b, mods, vk in parsed]
        while not _state["stop"].is_set():
            try:
                for w in watch:
                    down = bool(user32.GetAsyncKeyState(w["vk"]) & 0x8000)
                    if down and w["mods"]:
                        down = all(user32.GetAsyncKeyState(core._MOD_VKS[m]) & 0x8000
                                   for m in w["mods"])
                    if down and not w["down"]:
                        w["down"] = True
                        fire(w["label"], w["action"])
                    elif not down:
                        w["down"] = False
            except Exception as e:
                print(f"  [hotkeys] Key watch stopped: {e}")
                return
            time.sleep(0.05)

    threading.Thread(target=registered, daemon=True).start()
    threading.Thread(target=polled, daemon=True).start()
    for label, spec, _a, blurb, _m, _v in parsed:
        print(f"  [{label}] Press {spec.upper()} in game for {blurb}.")


def start_tray():
    """
    Put the narrator in the system tray instead of the taskbar.

    The menu carries only what still means something in this design: the speech
    speed, the volume, the banned voices (the one place we overrule the mod's
    casting), and quitting. Character voices and the player's own voice belong to the old
    proxy — the mod does its own casting now.
    """
    if not USE_TRAY:
        return False
    try:
        import pystray
        from PIL import Image, ImageDraw
    except Exception as e:
        print(f"  [tray] Tray unavailable ({e}). To enable: pip install pystray pillow")
        return False

    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([6, 6, 58, 58], fill=(70, 30, 90))
    d.ellipse([6, 6, 58, 58], outline=(205, 150, 245), width=3)
    d.rectangle([25, 22, 30, 42], fill=(235, 215, 250))
    d.rectangle([34, 22, 39, 42], fill=(235, 215, 250))

    shown = {"visible": True}

    def on_toggle(icon, item):
        shown["visible"] = not shown["visible"]
        core._show_console(shown["visible"])

    def on_show(icon, item):
        shown["visible"] = True
        core._show_console(True)

    def on_quit(icon, item):
        _state["stop"].set()
        icon.stop()
        core._show_console(True)          # never leave it hidden and running
        os._exit(0)

    def speed_item(name, value):
        def pick(icon, item):
            core.set_tts_speed(value)

        def current(item):
            return abs((core.tts_speed() or 1.0) - value) < 0.03

        return pystray.MenuItem(name, pick, checked=current, radio=True)

    speed_menu = pystray.Menu(
        pystray.MenuItem(
            lambda item: f"Now: {core.speed_name(core.tts_speed() or 1.0)}",
            None, enabled=False),
        pystray.MenuItem("(the narrator; characters keep a natural pace)",
                         None, enabled=False),
        pystray.Menu.SEPARATOR,
        *[speed_item(n, v) for n, v in core.TTS_SPEED_PRESETS
          if v <= core.MAX_TTS_SPEED],
    )

    def volume_item(name, value):
        def pick(icon, item):
            core.set_tts_volume(value)

        def current(item):
            return abs((core.tts_volume() or 1.0) - value) < 0.03

        return pystray.MenuItem(name, pick, checked=current, radio=True)

    volume_menu = pystray.Menu(
        pystray.MenuItem(
            lambda item: f"Now: {core.volume_name(core.tts_volume() or 1.0)}",
            None, enabled=False),
        pystray.MenuItem("(everything the narrator says, on top of the mod's "
                         "own slider)", None, enabled=False),
        pystray.Menu.SEPARATOR,
        *[volume_item(n, v) for n, v in core.TTS_VOLUME_PRESETS
          if v <= core.MAX_TTS_VOLUME],
    )

    def ban_item(vid, name):
        def toggle(icon, item):
            core.set_voice_banned(vid, vid not in core.banned_voices())

        def is_banned(item):
            return vid in core.banned_voices()

        return pystray.MenuItem(name, toggle, checked=is_banned)

    titles = {("american_english", "male"): "American male",
              ("american_english", "female"): "American female",
              ("british_english", "male"): "British male",
              ("british_english", "female"): "British female"}
    groups = core._english_voices()
    ban_subs = []
    for key in (("american_english", "male"), ("british_english", "male"),
                ("american_english", "female"), ("british_english", "female")):
        entries = groups.get(key) or []
        if entries:
            ban_subs.append(pystray.MenuItem(
                titles[key],
                pystray.Menu(*[ban_item(v, n) for v, n in entries])))

    banned_menu = pystray.Menu(
        pystray.MenuItem(
            lambda item: "Banned: " + (", ".join(sorted(
                core.VOICE_DB.get(v, {}).get("name", "?")
                for v in core.banned_voices())) or "none"),
            None, enabled=False),
        pystray.MenuItem("(a banned voice is replaced even if the mod picks it)",
                         None, enabled=False),
        pystray.Menu.SEPARATOR,
        *ban_subs,
    )

    menu = pystray.Menu(
        pystray.MenuItem("Narrator (AI Influence 7.0)", None, enabled=False),
        pystray.MenuItem("Show / hide console", on_toggle, default=True),
        pystray.MenuItem("Show console", on_show),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Speech speed", speed_menu),
        pystray.MenuItem("Volume", volume_menu),
        pystray.MenuItem("Banned voices", banned_menu),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", on_quit),
    )
    icon = pystray.Icon("narrator", img, "Narrator (AI Influence 7.0)", menu)
    threading.Thread(target=icon.run, daemon=True).start()
    print("  [tray] In the system tray — left-click to show or hide, "
          "right-click for the menu.")

    def settle():
        time.sleep(1.0)                   # let the banner finish printing
        if HIDE_FROM_TASKBAR:
            core._hide_console_from_taskbar(keep_visible=not START_MINIMIZED)
            print("  [tray] Console taken off the taskbar.")
        elif START_MINIMIZED:
            core._show_console(False)
            shown["visible"] = False

    threading.Thread(target=settle, daemon=True).start()
    return True


def start_log():
    """
    Keep a copy of the console in a file.

    Until now the narrator only printed, so when a line went unspoken there was
    nothing to look at afterwards and the cause had to be guessed at. Every
    line that appears on screen now also lands in narrator_log.txt, timestamped.
    """
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "narrator_log.txt")

    class Tee:
        def __init__(self, stream, handle):
            self._stream, self._handle, self._fresh = stream, handle, True

        def write(self, text):
            self._stream.write(text)
            try:
                for part in text.splitlines(True):
                    if self._fresh and part.strip():
                        self._handle.write(time.strftime("[%H:%M:%S] "))
                    self._handle.write(part)
                    self._fresh = part.endswith("\n")
                self._handle.flush()
            except Exception:
                pass

        def flush(self):
            self._stream.flush()

    try:
        handle = open(path, "a", encoding="utf-8", errors="replace")
        handle.write("\n" + "=" * 60 + "\n"
                     + time.strftime("  started %Y-%m-%d %H:%M:%S") + "\n")
        sys.stdout = Tee(sys.stdout, handle)
        sys.stderr = Tee(sys.stderr, handle)
        return path
    except Exception as e:
        print(f"  [log] Could not open the log file: {e}")
        return None


def claim_single_instance():
    """
    Only one narrator at a time.

    Two copies both watch the same save folder and both speak every line, which
    sounds exactly like the mod's own TTS being left on — so this refuses to
    start rather than leaving you to work out which of the two it is. The claim
    is a socket, so it is released the moment the program exits, however it
    exits.
    """
    import socket
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
    try:
        s.bind(("127.0.0.1", SINGLE_INSTANCE_PORT))
        s.listen(1)
    except OSError:
        print("=" * 60)
        print("  A narrator is ALREADY RUNNING.")
        print("  Two of them read every line twice, which sounds like an echo.")
        print("  Close the other window (or end the other python.exe) and")
        print("  start this one again.")
        print("=" * 60)
        return None
    return s                            # held open for the life of the program


def main():
    lock = claim_single_instance()
    if lock is None:
        return
    logged = start_log()
    print("=" * 60)
    print("  NARRATOR — for AI Influence 7.0")
    print("=" * 60)
    folder = core.get_npc_folder()
    print(f"  Save folder : {folder}")
    print(f"  Narrator    : {core.VOICE_DB.get(core.NARRATOR_VOICE, {}).get('name')}")
    print(f"  Characters  : the mod's own voice and its own note for each line")
    print(f"  Speed       : narrator on your dial "
          f"({core.speed_name(core.tts_speed() or 1.0)}), "
          f"characters at {'normal' if CHARACTER_SPEED == 1.0 else 'your dial'}")
    banned = len(core.banned_voices())
    print(f"  Banned      : {banned} voice(s) will be replaced if the mod picks one")
    try:
        core.requests.get(PLAYER2 + "/v1/health", timeout=5).raise_for_status()
        print("  Player2     : answering")
    except Exception:
        print("  Player2     : NOT ANSWERING — start the Player2 app.")
    print()
    if logged:
        print(f"  Log         : {os.path.basename(logged)} (kept, for when a "
              f"line goes unspoken)")
    print("  *** Turn AI Influence's own TTS OFF, or every line is spoken twice. ***")
    print("=" * 60)
    start_tray()
    hotkey_watchers()
    start_book_listener()
    threading.Thread(target=speaker, daemon=True).start()
    threading.Thread(target=mod_log_follower, daemon=True).start()
    try:
        watcher()
    except KeyboardInterrupt:
        _state["stop"].set()
        print("\n  Stopped.")


if __name__ == "__main__":
    main()
