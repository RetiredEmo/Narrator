"""
Build the release zip from this repository.

    python build.py            ->  dist/Narrator-AIInfluence-<version>.zip

Nothing is compiled: the narrator is plain Python and runs from its source.
"Building" only means copying the files a player needs into one zip, after
checking that none of them carries anything from one machine (a user folder,
a campaign id, an e-mail address). Uses only the Python standard library.
"""
import os
import re
import shutil
import sys
import zipfile

VERSION = "1.0.0"
HERE = os.path.dirname(os.path.abspath(__file__))

# Exactly what ships, and nothing else.
FILES = ["NARRATOR.py", "TTS_NARRATOR.py", "MEMORY_BOOK_HOOK.py",
         "START_NARRATOR.bat", "requirements.txt", "README.txt",
         "pronunciations.txt"]

FORBIDDEN = [r"C:\\Users\\[A-Za-z]", r"SteamLibrary[\\/]+steamapps[\\/]+common",
             r"@gmail\.com"]


def main():
    name = f"Narrator-AIInfluence-{VERSION}"
    dist = os.path.join(HERE, "dist")
    stage = os.path.join(dist, name)
    shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(stage)
    for f in FILES:
        shutil.copy2(os.path.join(HERE, f), stage)

    bad = []
    for f in FILES:
        text = open(os.path.join(stage, f), encoding="utf-8", errors="replace").read()
        for pat in FORBIDDEN:
            for m in re.finditer(pat, text):
                line = text.count("\n", 0, m.start()) + 1
                bad.append(f"{f}:{line}")
    if bad:
        print("Refusing to build - machine-specific text found:", *bad, sep="\n  ")
        sys.exit(1)

    out = os.path.join(dist, name + ".zip")
    if os.path.exists(out):
        os.remove(out)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(FILES):
            z.write(os.path.join(stage, f), os.path.join(name, f))
    print(f"Built {out} ({os.path.getsize(out) // 1024} KB, {len(FILES)} files)")


if __name__ == "__main__":
    main()
