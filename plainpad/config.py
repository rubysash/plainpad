"""Constants shared by the whole application.

Every path, delay, and format string lives here so that no other module
contains a magic value.
"""

from pathlib import Path

APP_NAME = "Plainpad"
ORGANIZATION_NAME = "Plainpad"

# --- Locations -----------------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent.parent
RESOURCES_DIR = Path(__file__).resolve().parent / "resources"

VENV_DIR = PROJECT_DIR / ".venv"
# The windowless interpreter, used by the plainpad.pyw launcher.
VENV_PYTHONW = VENV_DIR / "Scripts" / "pythonw.exe"

DATA_DIR = PROJECT_DIR / "data"
NOTES_DIR_NAME = "notes"
TRASH_DIR_NAME = "trash"
INDEX_FILE_NAME = "index.json"
PREVIEW_CSS_FILE_NAME = "preview.css"

QSS_FILE = RESOURCES_DIR / "crt.qss"
DEFAULT_PREVIEW_CSS_FILE = RESOURCES_DIR / "default_preview.css"

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

# --- Markdown and preview ------------------------------------------------

MARKDOWN_EXTENSIONS = ("fenced_code", "tables", "sane_lists")

PREVIEW_BACKGROUND_COLOR = "#000000"
EXTERNAL_LINK_SCHEMES = frozenset({"http", "https", "mailto"})

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
