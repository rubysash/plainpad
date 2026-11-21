# Plainpad specification

Plainpad is a single-user desktop notepad written in Python and PyQt6. Notes
are markdown files that save themselves. The window looks like an old green
CRT monitor.

Status: MVP implemented. Everything in this document works; layers 1 and 2
are covered by unit tests.

## 1. Decisions already made

| Topic | Decision |
| --- | --- |
| GUI toolkit | PyQt6 |
| Rendered view | `QWebEngineView` (full CSS support) |
| Storage | One flat folder of `.md` files plus a JSON index for categories |
| Images | One shared folder; files named by content hash, kept in their original format |
| Categories | One level deep; each note is in exactly one category |
| Search | Case-insensitive match on note name and note body |
| Python | 3.13, in a `.venv` in the project folder |

## 2. Window layout

```
+--------------------------------------------------------------+
| File  Edit  View  Help                                       |
+--------------------+-----------------------------------------+
| [ search...      ] | [ Edit ] [ View ]                       |
|                    |                                         |
| > Work             |  markdown source or rendered page,      |
| v Recipes          |  depending on the tab                   |
|     2026-11-16...  |                                         |
|     Chili          |                                         |
| > Uncategorized    |                                         |
+--------------------+-----------------------------------------+
| Saved 14:30:05                                               |
+--------------------------------------------------------------+
```

The two sides are separated by a draggable splitter.

## 3. Sidebar

### 3.1 Category tree

- Top-level rows are categories. Child rows are notes.
- Categories are created, renamed, and deleted by the user only.
- `Uncategorized` is built in. It cannot be renamed or deleted, and it is
  always listed last. New notes start there unless a category is selected,
  in which case the new note goes into the selected category.
- Categories are listed alphabetically. Notes inside a category are listed
  alphabetically, which is chronological for timestamp names.
- Every category starts collapsed on launch. Clicking a category expands or
  collapses it.
- Clicking a note, or pressing Enter on it, opens it in the Edit tab.
- Moving through the tree with Up, Down, Page Up, Page Down, Home, or End
  loads the note the selection rests on after a 300 ms pause, without
  changing tabs. If the View tab is showing, it re-renders, so rendered
  notes can be browsed from the keyboard.
- Double-clicking does not rename; rename is F2 only.

### 3.2 Drag and drop

- A note can be dragged onto a category row, or onto a note inside that
  category, to move it there.
- Categories cannot be dragged, and nothing can be dropped onto empty space.
- A move only edits the index. The `.md` file does not move.

### 3.3 Search

- Typing filters the tree after a 200 ms pause.
- A note matches when the search text appears in its name or its body,
  ignoring case.
- While a search is active: categories with a match are expanded, notes that
  do not match are hidden, and categories with no match are hidden.
- Clearing the box (or pressing Esc in it) shows everything again and
  restores the expanded/collapsed state from before the search.
- The open note's unsaved text is flushed to disk before a search runs, so
  the search always sees current text.
- Creating a note clears an active search, so the new note is visible.
- A note whose file is not valid UTF-8 matches on its name only.

### 3.4 Right-click menu

Right-clicking the tree selects the row under the cursor (without opening
a note) and shows these items. Right-clicking empty space clears the
selection.

- **New Note** and **New Category**, the same as File > New Note and
  File > New Category. A new note goes into the right-clicked category,
  or the category of the right-clicked note, or `Uncategorized` when
  empty space was right-clicked.
- **Show in Explorer** (Windows), **Show in Finder** (macOS), or **Open in
  File Manager** (Linux). On a note row it opens the notes folder with
  that note's file selected. Linux has no standard way to select a file,
  so there it only opens the folder. On a category row or empty space it
  opens the notes folder, since categories exist only in `index.json`.
- **Open Terminal Here** opens a terminal whose working folder is the
  notes folder. On Windows this is Windows Terminal (`wt`) with the
  user's default profile, which may be WSL; the item is hidden if
  Windows Terminal is not installed. On macOS it is Terminal. On Linux
  it is the first of `x-terminal-emulator`, `gnome-terminal`, `konsole`,
  `xfce4-terminal`, `kitty`, `alacritty`, `xterm` that is installed, and
  the item is hidden if none is.
- Windows only: **Open Command Prompt Here** (`cmd.exe`) and **Open
  PowerShell Here** (PowerShell 7, `pwsh`, if installed, otherwise
  Windows PowerShell), both in the notes folder. They start in a new
  console, which Windows shows in Windows Terminal or the classic console
  depending on the user's default terminal setting.

If the program cannot be started, the status bar says why. Only Windows
has been tried by hand; macOS and Linux are covered by unit tests of the
commands only.

## 4. Right side tabs

### 4.1 Edit

- Plain text markdown editor (`QPlainTextEdit`), monospace, word wrapped.
- Each opened note keeps its own `QTextDocument` for the session, so each
  note has its own undo and redo history. Switching notes does not lose it.
  Saving does not clear it. History is not kept across restarts.
- Disabled with a hint message when no note is open.
- Pasting (Ctrl+V) and dropping insert plain text, except for images;
  see 4.3.

### 4.3 Images

A note shows an image with an ordinary markdown link to a file in
`data/images/`: `![](../images/3fa9c2e17b04d6a1.png)`. The link is
relative to the notes folder, so it also works in other markdown viewers.
The editor shows the link; the picture shows in the View tab.

Pasting or dropping any of these into the editor stores a copy of the
image and inserts its link at the cursor:

| Paste or drop holds | What is stored |
| --- | --- |
| Local image files, from Explorer | An exact copy of each file |
| A picture copied in a browser ("Copy image"), or dragged from a web page | The original, downloaded from its address; the bitmap as PNG if that fails |
| A bitmap only, such as a screenshot | PNG |

- PNG, JPEG, GIF, and WebP are accepted, judged by how the file starts,
  not by its extension. Anything else is refused with a status bar
  message. The limit is 20 MB per image.
- Files are never converted. An animated GIF stays animated because its
  bytes are copied as they are. "Copy image" in a browser puts only one
  still frame on the clipboard, which is why the original is downloaded
  when its address is known.
- A bitmap that comes with text, as a spreadsheet's copied cells do, is
  pasted as the text.
- The file name is the first 16 hex digits of the content's SHA-256, so
  the same image pasted twice, or into two notes, is one file.
- An image belongs to no note. Sharing one between notes is copying the
  link; moving one is moving the link; removing the link removes the
  image from that note and leaves the file alone, so undo and other notes
  keep working.
- **File > Clean Up Unused Images** saves pending edits, then moves every
  image that no note links to into `data/trash/images/` and reports the
  count. Notes in the trash count as linking. Nothing is erased.

### 4.4 Rich copy and paste

Into a note:

- **Edit > Paste Formatted** (Ctrl+Shift+V) converts the clipboard's
  formatted text to markdown: headings, bold, italic, lists, links,
  tables, code. Each picture in it is copied into `data/images/` from
  wherever the source program left it: embedded in the HTML, a temporary
  file (Word, Outlook), or a web address (Google Docs).
- A picture that cannot be fetched, such as one behind a Gmail login or
  an email's `cid:` link, stays in the note as a link to its original
  address. The status bar says how many were missed.
- Downloads are limited to 5 seconds each and 15 seconds per paste.
- Ctrl+V never converts; it pastes plain text, so pasted code is never
  reformatted.

Out of a note:

- **Edit > Copy Note as Rich Text** (Ctrl+Shift+C) puts the whole open
  note on the clipboard as formatted text, from either tab.
- **Copy** (Ctrl+C) in the View tab copies the selection the same way.
  The theme's colors and fonts are removed, as are code block copy links.
- In both, stored images are embedded in the HTML as `data:` addresses,
  because other programs cannot read Plainpad's files. The clipboard also
  carries a plain text version.
- Copy in the Edit tab is unchanged: it copies the markdown text.

Tried by hand: nothing yet. The automated tests cover the conversions and
the clipboard contents, not how each program (Google Docs, Gmail, Outlook,
Word, Thunderbird, LibreOffice) accepts them.

### 4.2 View

- The open note rendered from markdown to HTML with the current theme's
  `preview.css` (see 9).
- Relative links are resolved against the notes folder, which is how
  image links are found. Images are never drawn wider than the page; that
  one rule is part of the page itself, not of a theme, so it also holds
  in the frozen Default theme.
- Re-rendered each time the tab is shown. The theme's `preview.css` is
  read again on every render, so hand edits to it show up the next time
  View is shown.
- Every code block has a **copy** link in its top right corner. Clicking
  it puts the block's text on the clipboard, exactly as written in the
  note, and the status bar says so. The link is a plain
  `plainpad-copy:<n>` link caught by the app, since the page runs no
  JavaScript.
- JavaScript is disabled in the page. Links open in the system browser, not
  inside the app. Only `http`, `https`, and `mailto` links are opened;
  other link types do nothing. Links to an anchor in the same note scroll
  the page.
- Markdown extensions: fenced code blocks, tables, sane lists.

## 5. Autosave

- A save happens 4 seconds after the last keystroke.
- A pending save is also flushed immediately when: another note is opened,
  the tab changes, a search runs, the note is renamed, File > Save Now is
  used, or the app closes.
- Writes are atomic: text goes to a temporary file that then replaces the
  real one, so a crash cannot leave a half-written note.
- The status bar shows the time of the last save, or the error if a save
  failed. A failed save keeps the text in the editor and retries on the
  next change, and on every flush listed above, even after switching to
  another note.
- If something still cannot be saved when the app closes, it asks before
  quitting. No is the default, so the window stays open.

## 6. Notes and categories

### 6.1 Names

- A note's name is its file name without `.md`. There is no separate title.
- A new note is named with the current local time: `2026-11-16_143005`
  (`%Y-%m-%d_%H%M%S`). No colons, so it is a valid Windows file name.
- If that name is taken, `-2`, `-3`, and so on is appended.
- Rename rejects empty names, names that differ only by case from an
  existing note, the characters `\ / : * ? " < > |`, control characters,
  and Windows reserved names such as `CON` and `NUL` (also with a dot
  suffix, such as `CON.old`). Changing only the case of a note's own name
  is allowed. Leading and trailing spaces are trimmed.
- Category names follow the same case-insensitive uniqueness rule, and
  `Uncategorized` cannot be used as a category name.

### 6.2 Deleting

- Deleting a note asks for confirmation, then moves the file to
  `data/trash/`. Nothing is erased by the app. If the trash already holds
  a note with that name, the trashed file gets `_<timestamp>` appended.
- Deleting a category asks for confirmation, then moves its notes to
  `Uncategorized`. Notes are never deleted with a category.

## 7. Storage

```
data/
  notes/        one .md file per note, UTF-8
  images/       pictures linked from notes; see 4.3
  trash/        deleted notes
    images/     images moved out by Clean Up Unused Images
  index.json    categories and which note is in which
```

`data/` sits in the project folder and is git-ignored. The location is one
constant in `config.py`.

`index.json`:

```json
{
  "version": 1,
  "categories": [
    {"id": "3f9a1c2e", "name": "Recipes"}
  ],
  "assignments": {
    "2026-11-16_143005": "3f9a1c2e"
  }
}
```

- Category ids are random and never change, so renaming a category does not
  touch `assignments`.
- A note with no entry in `assignments` is in `Uncategorized`.
- On launch the index is reconciled with the folder: entries for missing
  files are dropped, and files added by hand show up in `Uncategorized`.
- If `index.json` cannot be read, it is renamed to
  `index.json.<timestamp>.corrupt` (never overwritten) and the app starts
  with no categories.

Window size, splitter position, the last open note, and the chosen theme
are remembered with `QSettings`.

## 8. Menus and keys

| Menu | Item | Key |
| --- | --- | --- |
| File | New Note | Ctrl+N |
| File | New Category | Ctrl+Shift+N |
| File | Rename | F2 |
| File | Delete | Del (when the tree has focus) |
| File | Save Now | Ctrl+S |
| File | Clean Up Unused Images | |
| File | Exit | Ctrl+Q |
| Edit | Undo | Ctrl+Z |
| Edit | Redo | Ctrl+Y |
| Edit | Cut / Copy / Paste | Ctrl+X / Ctrl+C / Ctrl+V |
| Edit | Copy Note as Rich Text | Ctrl+Shift+C |
| Edit | Paste Formatted | Ctrl+Shift+V |
| Edit | Select All | Ctrl+A |
| Edit | Find | Ctrl+F (focuses the search box) |
| View | Edit tab | Ctrl+1 |
| View | View tab | Ctrl+2 |
| View | Toggle Edit / View | Ctrl+E |
| Settings | Theme > (one item per theme, current one checked) | |
| Help | About | |

Rename and Delete act on the selected tree row, whether it is a note or a
category. Rename edits the row in place.

The Edit menu items act on whichever text box has focus: the note editor
or the search box. Copy and Select All also work in the View tab. Copy
Note as Rich Text and Paste Formatted always act on the open note.

The tree's right-click menu is described in 3.4.

## 9. Themes

Themes live in `plainpad/themes/`, one folder each:

```
plainpad/themes/<name>/
  app.qss       the window chrome (menus, tree, tabs, editors)
  preview.css   the View tab CSS the theme ships with
  theme.json    {"label": "..."} for the menu; optional
```

Any folder with both stylesheets is a theme and appears in
Settings > Theme with no code change. Without `theme.json` the menu shows
the folder name. Default is listed first, the rest by label. Switching is
instant and remembered across restarts.

There is no style editor in the app. To change a theme, edit its files by
hand. Changes to `preview.css` show the next time the View tab renders;
changes to `app.qss` show after switching themes or restarting. The chrome is applied on top of
Qt's Fusion style, because the native Windows style ignores parts of a
stylesheet.

| Theme | Look |
| --- | --- |
| `default` | The original CRT green. Never changes; see below. |
| `crt` | The same CRT green, in files meant to be edited. Used on first launch. |
| `dark` | ttkbootstrap's "darkly" palette: `#222222` background, `#ffffff` text, `#375a7f` accent, `#00bc8c` links. |
| `light` | White background, `#1f2328` text (15.8:1), `#0969da` accent and links (5.2:1), `#57606a` muted text (6.4:1). WCAG AA or better throughout. |

Default is the safe fallback:

- Its files never change. A test checks their hashes, so bad CSS can
  never break it.
- An unknown, missing, or incomplete theme falls back to it.

CRT details: black `#000000`, phosphor green `#33ff33`, dim green
`#1a8c1a`. Font stack `VT323`, `Consolas`, `Courier New`, `monospace`; no
font is bundled, `VT323` is used if installed. Its View CSS has a text
glow; Qt widgets cannot draw one, so only the View tab glows. Dark and
Light use Segoe UI for the chrome and Cascadia Mono or Consolas for the
editors.

## 10. Code layout

Three layers. Lower layers never import higher ones.

1. Storage and logic. No Qt imports. Fully unit-testable.
2. `Library`, one facade over the storage layer. The GUI's only way in.
3. GUI widgets, which talk to each other through Qt signals and are wired
   together in `MainWindow`.

| File | Contains | Purpose |
| --- | --- | --- |
| `plainpad/app.py` | `main()` | Build the application and show the window |
| `plainpad/__main__.py` | | `python -m plainpad` |
| `plainpad.pyw` | | Double-click launcher; switches to `.venv`, shows startup errors in a message box |
| `plainpad/config.py` | constants | Paths, delays, name format |
| `plainpad/models.py` | `Category`, `CategoryListing`, `Theme`, `RenderedPage`, `ImportedText` | Plain data classes |
| `plainpad/crud.py` | `NoteStore`, `timestamp_name()`, `NoteNameError` | Create, read, update, delete note files |
| `plainpad/atomic_file.py` | `write_text_atomically()`, `write_bytes_atomically()` | The one crash-safe write, used by notes, index, and images |
| `plainpad/images.py` | `ImageStore`, `ImageFormatError` | Keep image files by content hash; move unused ones to the trash |
| `plainpad/image_links.py` | `image_link_for()`, `image_names_in()` | Build and find the links notes use for images |
| `plainpad/image_sources.py` | `ImageSourceReader`, `ImageSourceError` | Image bytes from a `data:`, `file:`, or web address |
| `plainpad/rich_import.py` | `RichTextImporter`, `sole_image_address()` | Clipboard HTML to markdown, storing its images |
| `plainpad/rich_export.py` | `RichTextExporter` | A note or a copied selection as HTML with images embedded |
| `plainpad/categories.py` | `CategoryIndex` | Load, change, and save `index.json` |
| `plainpad/search.py` | `find_matching_notes()` | Keyword search |
| `plainpad/library.py` | `Library` | Facade over notes, categories, images, search |
| `plainpad/render.py` | `MarkdownRenderer` | Markdown and CSS to an HTML page |
| `plainpad/code_blocks.py` | `add_copy_links()` | Copy links on code blocks, and each block's text |
| `plainpad/theme_store.py` | `ThemeStore` | Find themes and read their stylesheets |
| `plainpad/desktop_launch.py` | `DesktopLauncher` | Open the file browser, a terminal, Command Prompt, or PowerShell, per OS |
| `plainpad/theme.py` | `apply_theme()` | Put a theme's `app.qss` on the application |
| `plainpad/autosave.py` | `AutosaveTimer` | The 4 second idle timer |
| `plainpad/gui/main_window.py` | `MainWindow` | Layout and signal wiring |
| `plainpad/gui/tree_commands.py` | `TreeCommands` | Create, rename, move, delete notes and categories |
| `plainpad/gui/location_commands.py` | `LocationCommands` | The tree's right-click menu: file browser and terminals |
| `plainpad/gui/clipboard_commands.py` | `ClipboardCommands` | Paste images and formatted text; copy a note out as rich text |
| `plainpad/gui/pasted_content.py` | `PastedContent` | Which images a paste or drop offers |
| `plainpad/gui/session.py` | `SessionMemory` | Window size, splitter, last note via `QSettings` |
| `plainpad/gui/actions.py` | `Actions`, `populate_menu_bar()`, `build_tree_menu()` | Menu items and key bindings |
| `plainpad/gui/sidebar.py` | `Sidebar` | Search box above the tree |
| `plainpad/gui/note_tree.py` | `NoteTree` | Collapsible tree, drag and drop |
| `plainpad/gui/tree_filter.py` | `TreeFilter` | Search filtering and restoring expanded state |
| `plainpad/gui/tree_items.py` | `make_item()`, `identity_of()` | What a tree row is and how to read it |
| `plainpad/gui/tab_area.py` | `TabArea` | The two tabs; flush and render on tab change |
| `plainpad/gui/editor_tab.py` | `EditorTab` | Markdown editor, per-note undo |
| `plainpad/gui/preview_tab.py` | `PreviewTab`, `ExternalLinkPage` | Rendered view |
| `plainpad/gui/dialogs.py` | `ask_for_name()`, `confirm()`, `show_about()` | The modal prompts |
| `plainpad/themes/<name>/` | `app.qss`, `preview.css`, `theme.json` | One theme; see 9 |
| `tests/test_*.py` | | Unit tests for layer 1 and 2 |
| `tests/test_gui.py` | | pytest-qt tests of the window: autosave, undo, search, rename, delete, failed saves, keyboard browsing, copy links, themes, right-click menu |
| `tests/test_gui_images.py` | | pytest-qt tests of image paste and drop, Paste Formatted, rich copy from both tabs, cleanup |
| `tests/conftest.py`, `tests/gui_support.py`, `tests/image_samples.py` | | The shared window fixture, GUI stand-ins, sample images and a network stand-in |

Size: about 3,650 lines of Python (half of it docstrings and comments)
across 37 source files. `main_window.py` and `note_tree.py` run over the
200 line guideline.

Dependencies beyond PyQt6: `Markdown` renders notes; `markdownify` (with
`beautifulsoup4`) converts pasted HTML to markdown.

## 11. Out of scope

- Multiple notes open at once, or multiple windows
- Nested categories, tags, or a note in more than one category
- Sync, encryption, export, printing
- Resizing, cropping, or converting images; images shown in the editor
- Rich copy formats other than HTML (no RTF)
- Syntax highlighting in the editor or in rendered code blocks
- Find and replace inside a note
- Undo history that survives a restart
