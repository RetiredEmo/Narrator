"""
Teach AI Influence's Memory Book to say which page is open.

The book is not a game screen. The mod runs a small web server and shows an
ordinary web page in an embedded browser over the map (logs\\MemoryBook.log
says so), and that page lives on disk inside the mod folder. Which page you
are looking at exists only inside that page — nothing is written to the save
or to any log — so the only honest way to know is to ask the page itself.

This appends a marked block to the book's index.html. The block reads the
book's own list of memories from the mod's API, works out which entry is
highlighted, and tells the narrator that memory's id. An id is exact: it does
not care what language the game is in, what a memory is called, or whether two
memories happen to share a title.

The narrator installs and repairs this by itself when it starts, so an AI
Influence update that overwrites the page is undone the next time you run it.
You only need this by hand to look in on it or to take it out:

    python MEMORY_BOOK_HOOK.py            install or repair
    python MEMORY_BOOK_HOOK.py --status   say whether it is in place
    python MEMORY_BOOK_HOOK.py --remove   put the book back as it was

Nothing here is tied to one machine: the page is found from wherever the
narrator found the save folder, and failing that from Steam's own library list.
"""
import io
import os
import re
import sys

# Ports the narrator may be listening on. The page tries them in turn and only
# talks to one that answers as the narrator, so a port taken by something else
# costs nothing. Keep this the same as BOOK_REPORT_PORTS in NARRATOR.py.
BOOK_REPORT_PORTS = [4401, 4402, 4403, 4404, 4405]

# Raised whenever the block below changes, so that an older one is replaced
# rather than left sitting there.
HOOK_VERSION = 2

START = "<!-- TTS-NARRATOR-HOOK-START v%d -->" % HOOK_VERSION
END = "<!-- TTS-NARRATOR-HOOK-END -->"
ANY_START = re.compile(r"<!-- TTS-NARRATOR-HOOK-START[^>]*-->")

# Where the page sits inside the mod, counting from the module folder.
PAGE_WITHIN_MODULE = os.path.join("MemoryBook", "wwwroot", "index.html")


# ------------------------------------------------------------------
#  Finding the book on this machine
# ------------------------------------------------------------------

def module_root_from_save(save_folder):
    r"""...\Modules\AIInfluence\save_data\<campaign>  ->  ...\AIInfluence"""
    if not save_folder:
        return None
    base = os.path.dirname(os.path.normpath(save_folder))      # save_data
    if os.path.basename(base).lower() != "save_data":
        return None
    return os.path.dirname(base)                               # AIInfluence


def find_book_page(save_folder=None):
    """
    The book's index.html on this machine, or None.

    The save folder the narrator already watches points straight at it, which
    is both exact and free; only if that fails do we go looking for installs.
    """
    tried = []

    root = module_root_from_save(save_folder)
    if root:
        page = os.path.join(root, PAGE_WITHIN_MODULE)
        tried.append(page)
        if os.path.isfile(page):
            return page

    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import TTS_NARRATOR as core
        bases = core._find_save_data_bases()
    except Exception:
        bases = []
    for base in bases:
        page = os.path.join(os.path.dirname(base), PAGE_WITHIN_MODULE)
        if page in tried:
            continue
        tried.append(page)
        if os.path.isfile(page):
            return page
    return None


# ------------------------------------------------------------------
#  The block we add
# ------------------------------------------------------------------

SCRIPT_TEMPLATE = """%s
<script>
/* Added by the Bannerlord TTS Narrator, so that its "read this page" key reads
   the page you have open. It reads this book and talks to this machine only.
   To remove it, delete from the comment above to the one below. */
(function () {
  "use strict";
  var PORTS = [%s];
  var endpoint = null, tried = 0, memories = null, last = "", beat = 0;

  function day(m) {
    if (!m || m.campaignDay == null || isNaN(m.campaignDay)) return -1;
    return Math.floor(m.campaignDay);
  }

  function sortedLikeTheBook(list) {
    /* The book orders by campaign day, newest first, and leaves equal days in
       the order the mod sent them. Array.sort is stable, so this is the very
       order the list on screen is in. */
    return list.slice().sort(function (a, b) { return day(b) - day(a); });
  }

  function items() { return document.querySelectorAll(".memory-list-item"); }

  function activeIndex() {
    var all = items();
    for (var i = 0; i < all.length; i++) {
      if (all[i].className.indexOf("active") >= 0
          || all[i].getAttribute("aria-selected") === "true") return i;
    }
    return -1;
  }

  function text(id) {
    var el = document.getElementById(id);
    return el ? (el.textContent || "").trim() : "";
  }

  function loadMemories(then) {
    try {
      var xhr = new XMLHttpRequest();
      xhr.open("GET", "/api/memory-book/memories", true);
      xhr.onload = function () {
        try {
          var data = JSON.parse(xhr.responseText);
          memories = sortedLikeTheBook((data && data.memories) || []);
        } catch (e) { memories = []; }
        if (then) then();
      };
      xhr.onerror = function () { memories = []; if (then) then(); };
      xhr.send(null);
    } catch (e) { memories = []; if (then) then(); }
  }

  function findNarrator() {
    if (endpoint !== null || tried >= PORTS.length) return;
    var port = PORTS[tried++];
    try {
      fetch("http://127.0.0.1:" + port + "/narrator/hello", {cache: "no-store"})
        .then(function (r) { return r.json(); })
        .then(function (j) {
          if (j && j.narrator === "bannerlord-tts") {
            endpoint = "http://127.0.0.1:" + port + "/book";
          }
        })
        .catch(function () { /* nothing there, or not ours */ });
    } catch (e) { /* no fetch in this engine */ }
  }

  function send(open) {
    if (endpoint === null) { findNarrator(); return; }
    var i = activeIndex();
    var id = (memories && i >= 0 && memories[i]) ? (memories[i].id || "") : "";
    var title = text("memoryTitle");
    var now = Date.now();
    var stamp = open + "|" + id + "|" + i + "|" + title;
    /* Repeat an unchanged page now and then, so the narrator can tell a book
       still open from one that was closed without a word. */
    if (stamp === last && now - beat < 2000) return;
    last = stamp;
    beat = now;
    try {
      new Image().src = endpoint
        + "?open=" + (open ? "1" : "0")
        + "&id=" + encodeURIComponent(id)
        + "&n=" + i
        + "&of=" + (memories ? memories.length : -1)
        + "&title=" + encodeURIComponent(title)
        + "&counter=" + encodeURIComponent(text("counterText"))
        + "&_=" + now;
    } catch (e) { /* the narrator is not running */ }
  }

  function watch() {
    var root = document.getElementById("app") || document.body;
    try {
      new MutationObserver(function () { send(true); })
        .observe(root, {subtree: true, childList: true, characterData: true,
                        attributes: true,
                        attributeFilter: ["class", "aria-selected"]});
    } catch (e) { /* the timer below still covers it */ }
    setInterval(function () {
      if (memories && items().length && memories.length !== items().length) {
        loadMemories();          /* a memory was formed while you were reading */
      }
      send(!document.hidden);
    }, 500);
    loadMemories(function () { send(true); });
  }

  function closed() { last = ""; send(false); }
  window.addEventListener("pagehide", closed);
  window.addEventListener("beforeunload", closed);
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) closed();
  });

  findNarrator();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", watch);
  } else {
    watch();
  }
})();
</script>
%s"""


def build_script(ports=None):
    ports = ports or BOOK_REPORT_PORTS
    return SCRIPT_TEMPLATE % (START, ",".join(str(p) for p in ports), END)


# ------------------------------------------------------------------
#  Putting it in and taking it out
# ------------------------------------------------------------------

def read(path):
    # newline="" so the file's own line endings survive: the page ships with
    # Windows ones, and rewriting it with Unix ones would touch every line of
    # a file that is not ours.
    return io.open(path, encoding="utf-8-sig", newline="").read()


def write(path, text):
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def strip_hook(html):
    """The page without our block, and without the gap it leaves behind, so
    that removing it gives the file back byte for byte. Any version of the
    block comes out, not only the current one."""
    eol = "\r\n" if "\r\n" in html else "\n"
    pattern = (r"(?:\r?\n)*<!-- TTS-NARRATOR-HOOK-START[^>]*-->.*?"
               + re.escape(END) + r"(?:\r?\n)*")
    return re.sub(pattern, eol, html, flags=re.S)


def has_hook(html, current_only=True):
    return (START in html) if current_only else bool(ANY_START.search(html))


def install(page=None, ports=None, save_folder=None):
    """
    Put the block in, or bring an older one up to date.

    Returns (ok, what happened). The file is written only when it would
    actually change, so running this at every start-up costs one read.
    """
    page = page or find_book_page(save_folder)
    if not page:
        return False, ("the Memory Book was not found — AI Influence 7 or "
                       "later must be installed")
    try:
        html = read(page)
    except Exception as e:
        return False, f"could not read the Memory Book page ({e})"

    if "</body>" not in html:
        return False, "that page is not the book we know, so it was left alone"

    clean = strip_hook(html)
    eol = "\r\n" if "\r\n" in clean else "\n"
    block = build_script(ports)
    if eol == "\r\n":
        block = block.replace("\n", "\r\n")
    wanted = clean.replace("</body>", block + eol + "</body>", 1)
    if wanted == html:
        return True, "already in place"

    had_older = has_hook(html, current_only=False)
    backup = page + ".before-narrator"
    if not os.path.exists(backup) and not had_older:
        try:
            write(backup, html)
        except Exception:
            pass                     # a backup is a courtesy, not a condition
    try:
        write(page, wanted)
    except Exception as e:
        return False, (f"could not write to the Memory Book page ({e}) — is "
                       f"the game running, or the folder read-only?")
    return True, ("repaired after an update" if had_older else "installed")


def remove(page=None, save_folder=None):
    page = page or find_book_page(save_folder)
    if not page:
        return False, "the Memory Book was not found"
    html = read(page)
    if not has_hook(html, current_only=False):
        return True, "nothing to remove"
    write(page, strip_hook(html))
    return True, "removed"


def status(page=None, save_folder=None):
    page = page or find_book_page(save_folder)
    if not page:
        return False, "the Memory Book was not found", None
    html = read(page)
    if has_hook(html):
        return True, "in place", page
    if has_hook(html, current_only=False):
        return True, ("in place, but an older version — run this to bring it "
                      "up to date"), page
    return False, "not installed", page


def main(argv):
    want = (argv[1] if len(argv) > 1 else "").lower()

    if want in ("--status", "-s", "status"):
        ok, msg, page = status()
        print("Memory Book hook: " + msg + ".")
        if page:
            print("  " + page)
        return 0

    if want in ("--remove", "-r", "remove", "uninstall"):
        ok, msg = remove()
        print("Memory Book hook: " + msg + ".")
        return 0 if ok else 1

    ok, msg = install()
    print("Memory Book hook: " + msg + ".")
    page = find_book_page()
    if page:
        print("  " + page)
    if ok:
        print("The narrator does this for itself every time it starts, so an "
              "AI Influence update cannot leave it behind.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
