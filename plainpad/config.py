"""Constants shared by the whole application.

Every path, delay, and format string lives here so that no other module
contains a magic value.
"""

from pathlib import Path

APP_NAME = "Plainpad"
ORGANIZATION_NAME = "Plainpad"

# --- Locations -----------------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent.parent

VENV_DIR = PROJECT_DIR / ".venv"
# The windowless interpreter, used by the plainpad.pyw launcher.
VENV_PYTHONW = VENV_DIR / "Scripts" / "pythonw.exe"

DATA_DIR = PROJECT_DIR / "data"
NOTES_DIR_NAME = "notes"
TRASH_DIR_NAME = "trash"
INDEX_FILE_NAME = "index.json"

# --- Themes --------------------------------------------------------------

# One folder per theme, each holding these three files.
THEMES_DIR = Path(__file__).resolve().parent / "themes"
THEME_QSS_FILE_NAME = "app.qss"
THEME_PREVIEW_CSS_FILE_NAME = "preview.css"
THEME_INFO_FILE_NAME = "theme.json"

# The original CRT look. Its files never change, so it is always there to
# fall back to.
DEFAULT_THEME = "default"
# What a first launch uses: the same look, in files that may be edited.
FIRST_RUN_THEME = "crt"

# --- File browser and terminal -------------------------------------------

# Values of sys.platform.
WINDOWS_PLATFORM = "win32"
MACOS_PLATFORM = "darwin"

FILE_BROWSER_LABELS = {
    WINDOWS_PLATFORM: "Show in &Explorer",
    MACOS_PLATFORM: "Show in &Finder",
}
OTHER_FILE_BROWSER_LABEL = "Open in File &Manager"

# Windows Terminal opens the user's default profile, which may be WSL.
WINDOWS_TERMINAL_PROGRAM = "wt"
WINDOWS_COMMAND_PROMPT = "cmd.exe"
# PowerShell 7 if installed, else the Windows PowerShell every Windows has.
WINDOWS_POWERSHELL_PROGRAMS = ("pwsh", "powershell.exe")
MACOS_TERMINAL_APP = "Terminal"
# Tried in order. Each one starts in the folder it is run from.
LINUX_TERMINAL_PROGRAMS = (
    "x-terminal-emulator",
    "gnome-terminal",
    "konsole",
    "xfce4-terminal",
    "kitty",
    "alacritty",
    "xterm",
)

# --- Files ---------------------------------------------------------------

TEXT_ENCODING = "utf-8"

# Temporary files get this suffix so they never look like notes.
ATOMIC_TEMP_SUFFIX = ".tmp"

# --- Notes ---------------------------------------------------------------

NOTE_EXTENSION = ".md"

# No colons, so the result is a valid Windows file name.
TIMESTAMP_FORMAT = "%Y-%m-%d_%H%M%S"

# The first suffix tried when a name is taken: name-2, name-3, ...
DUPLICATE_SUFFIX_START = 2

FORBIDDEN_NAME_CHARACTERS = '\\/:*?"<>|'
# Windows refuses control characters (code points below 32) in file names.
FIRST_PRINTABLE_CODE_POINT = 32
RESERVED_WINDOWS_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{number}" for number in range(1, 10)}
    | {f"LPT{number}" for number in range(1, 10)}
)

# --- Categories ----------------------------------------------------------

INDEX_VERSION = 1
INDEX_JSON_INDENT = 2
CATEGORY_ID_BYTES = 4
CORRUPT_INDEX_SUFFIX = ".corrupt"

# Fixed id of the built-in category. It is never written to index.json;
# a note with no assignment belongs to it.
UNCATEGORIZED_ID = "uncategorized"
UNCATEGORIZED_NAME = "Uncategorized"

# --- Timing --------------------------------------------------------------

AUTOSAVE_DELAY_MS = 4000
SEARCH_DELAY_MS = 200
# Pause after arrowing through the tree before the highlighted note loads.
NOTE_BROWSE_DELAY_MS = 300

# --- Markdown and preview ------------------------------------------------

MARKDOWN_EXTENSIONS = ("fenced_code", "tables", "sane_lists")

PREVIEW_BACKGROUND_COLOR = "#000000"
EXTERNAL_LINK_SCHEMES = frozenset({"http", "https", "mailto"})

# Copy links on code blocks are plain links in this scheme, because the
# View tab runs no JavaScript. The app catches the click and copies.
COPY_LINK_SCHEME = "plainpad-copy"
CODE_BLOCK_TEMPLATE = (
    '<div class="code-block">'
    '<a class="copy-code" href="{scheme}:{index}">copy</a>'
    "{block}</div>"
)

PREVIEW_PAGE_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{css}
</style>
</head>
<body>
{body}
</body>
</html>
"""

# --- Window --------------------------------------------------------------

QT_STYLE_NAME = "Fusion"
STATUS_TIME_FORMAT = "%H:%M:%S"
DEFAULT_WINDOW_SIZE = (1000, 700)
DEFAULT_SPLITTER_SIZES = (260, 740)

SETTINGS_GEOMETRY_KEY = "window/geometry"
SETTINGS_SPLITTER_KEY = "window/splitter"
SETTINGS_LAST_NOTE_KEY = "session/last_note"
SETTINGS_THEME_KEY = "appearance/theme"
