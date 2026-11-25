NARRATOR for AI Influence 7.0 (Mount & Blade II: Bannerlord)
=============================================================
Version 1.0.0

Reads AI Influence conversations aloud while you play: *actions* in a
narrator's voice, and every character's words in their own voice, performed
with the delivery note the mod writes for each line. Group scenes are voiced
as the characters start talking, not after the text has finished.


WHAT YOU NEED
-------------
  1. Windows 10 or 11.
  2. Mount & Blade II: Bannerlord with AI Influence 7.0.x
     (Steam, Steam Workshop, GOG and Xbox installs are all found on their own).
  3. The Player2 app, running and signed in (https://player2.game).
     The voices come from Player2, so it must be open whenever you play.
  4. Python 3.10 or newer (https://www.python.org/downloads/).
     During setup, tick "Add python.exe to PATH".


INSTALL
-------
  1. Unzip this folder anywhere you like, for example your Documents folder.
     It does NOT go into the game's Modules folder.
  2. In the game, open the AI Influence settings (MCM) and turn the mod's
     own TTS / voice playback OFF, and "Enable Ambient NPC TTS" OFF too.
     If you leave them on, lines are spoken twice.
  3. Double-click START_NARRATOR.bat.
     The first start installs the few Python parts the narrator needs
     (requests, flask, pystray, pillow). That takes a minute, once.


FIRST START
-----------
  - The narrator looks for your AI Influence campaigns by itself and follows
    the one you are playing. If it finds several and cannot tell, it shows a
    numbered list: type the number and press Enter.
  - If it finds none (an unusual install folder), it asks you to paste the
    path of your campaign folder. It looks like:
      ...\Mount & Blade II Bannerlord\Modules\AIInfluence\save_data\<letters>
  - The console then hides itself in the system tray (bottom right, near
    the clock). Left-click the icon to show or hide it.
  - Start or load a campaign and talk to someone. That's all.

  Load a different campaign later and the narrator moves to it on its own
  within a few seconds.


IN GAME
-------
  NUMPAD +   read the latest day's events (press again to step back a day)
  NUMPAD -   read your newest letter (again for the one before)
  NUMPAD *   read the open page of the Memory Book (again to step down it)

  Tray menu (right-click the icon):
    Speech speed     slower or faster narration
    Volume           louder or quieter than the mod's own volume slider
    Banned voices    voices you never want to hear; they are replaced
    Quit


NAMES SAID WRONG?
-----------------
  The narrator already knows how to say most Westeros names and places
  (Daenerys, Braavos, Cersei, Targaryen and many more). For anything else,
  open pronunciations.txt and add a line:

      Word = how it sounds

  for example   Lys = Lease   or   Qyburn = Kwyburn
  Spell the right-hand side the way it sounds. It applies from the next line
  spoken, no restart needed. Only the voice hears it; subtitles keep the real
  spelling. Your lines win over the built-in ones.


THE VOICE NOTES
---------------
  Each line is performed from a short note on how to say it, written by the
  same AI that wrote the line. AI Influence 7.1 only asks for that note while
  its own TTS is on, and here its TTS has to be off. So the narrator adds the
  one request back to your campaign's prompts:
      save_data\<campaign>\prompts\json_output\JsonOutputExpressionField.txt
  gets one line naming the field "tts_instructions". It checks this every few
  seconds, so a new campaign or an AI Influence update that resets the file
  gets it back by itself. To undo it, delete that one line (and set
  ASK_MOD_FOR_NOTES = False near the top of NARRATOR.py, or it comes back).


THE MEMORY BOOK
---------------
  So that NUMPAD * knows which page you have open, the narrator adds a small
  script to AI Influence's Memory Book page
  (Modules\AIInfluence\MemoryBook\wwwroot\index.html). The original is kept
  next to it as index.html.before-narrator. The narrator puts the script back
  by itself after an AI Influence update.


TROUBLESHOOTING
---------------
  Nothing is spoken
    - Is the Player2 app open and signed in? The console says
      "Player2 : answering" at start-up when it is.
    - Is the narrator following the right campaign? The console shows the
      campaign folder at start-up. To choose again, quit, delete
      proxy_config.txt and start it again.
    - People talking near you are read quietly, and only while you are not
      in a conversation of your own; your own scene always comes first.

  Every line is spoken twice
    - AI Influence's own TTS is still on. Turn it off in its MCM settings.

  "Python was not found"
    - Install Python (see WHAT YOU NEED) and tick "Add python.exe to PATH".
      Already installed? Reinstall it with that box ticked.

  The first start says the install failed
    - Check your internet connection and start it again. Or open a command
      prompt in this folder and run:   py -m pip install -r requirements.txt

  A line was skipped or cut short
    - Open narrator_log.txt in this folder: every line, and why it was or was
      not spoken, is written there. Please include it with a bug report.


FILES
-----
  START_NARRATOR.bat     start here
  NARRATOR.py            the narrator
  TTS_NARRATOR.py        shared parts (finding your campaign, voices, names)
  MEMORY_BOOK_HOOK.py    the Memory Book page script (see above)
  requirements.txt       the Python parts installed on first start
  pronunciations.txt     your own pronunciations

  Made on first use, and yours alone: proxy_config.txt (your campaign
  folder), npc_voices.json (the voice each character was given),
  narrator_log.txt, and the tray settings (tts_speed.txt, tts_volume.txt,
  banned_voices.txt).
