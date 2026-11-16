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
| Categories | One level deep; each note is in exactly one category |
| Search | Case-insensitive match on note name and note body |
| Python | 3.13, in a `.venv` in the project folder |

## 2. Window layout

```
+--------------------------------------------------------------+
| File  Edit  View  Help                                       |
+--------------------+-----------------------------------------+
| [ search...      ] | [ Edit ] [ View ] [ Settings ]          |
|                    |                                         |
| > Work             |  markdown source, rendered page,        |
| v Recipes          |  or preview CSS, depending on the tab   |
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

## 4. Right side tabs

### 4.1 Edit

- Plain text markdown editor (`QPlainTextEdit`), monospace, word wrapped.
- Each opened note keeps its own `QTextDocument` for the session, so each
  note has its own undo and redo history. Switching notes does not lose it.
  Saving does not clear it. History is not kept across restarts.
- Disabled with a hint message when no note is open.

### 4.2 View

- The open note rendered from markdown to HTML with the current theme's
  View CSS (see 4.3).
- Re-rendered each time the tab is shown.
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

### 4.3 Settings

- One CSS editor showing the current theme's View CSS. This CSS styles the
  View tab only.
- Each theme keeps its own CSS. Until it is edited, a theme uses the CSS it
  ships with. Switching themes saves pending CSS under the theme it was
  typed for.
- Autosaves with the same 4 second rule as notes.
- A "Reset to default" button restores the current theme's shipped CSS,
  after a confirmation. The reset is one undoable edit.
- For the Default theme the editor is read-only, the button is disabled,
  and a hint explains why (see 9).

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
  trash/        deleted notes
  index.json    categories and which note is in which
  styles/       the Settings tab CSS, one <theme>.css per edited theme
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
| File | Exit | Ctrl+Q |
| Edit | Undo | Ctrl+Z |
| Edit | Redo | Ctrl+Y |
| Edit | Cut / Copy / Paste | Ctrl+X / Ctrl+C / Ctrl+V |
| Edit | Select All | Ctrl+A |
| Edit | Find | Ctrl+F (focuses the search box) |
| View | Edit tab | Ctrl+1 |
| View | View tab | Ctrl+2 |
| View | Settings tab | Ctrl+3 |
| View | Toggle Edit / View | Ctrl+E |
| Settings | Theme > (one item per theme, current one checked) | |
| Help | About | |

Rename and Delete act on the selected tree row, whether it is a note or a
category. Rename edits the row in place.

The Edit menu items act on whichever text box has focus: the note editor,
the CSS editor, or the search box.

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
instant and remembered across restarts. The chrome is applied on top of
Qt's Fusion style, because the native Windows style ignores parts of a
stylesheet.

| Theme | Look |
| --- | --- |
| `default` | The original CRT green. Never changes; see below. |
| `crt` | The same CRT green, editable. Used on first launch. |
| `dark` | ttkbootstrap's "darkly" palette: `#222222` background, `#ffffff` text, `#375a7f` accent, `#00bc8c` links. |
| `light` | White background, `#1f2328` text (15.8:1), `#0969da` accent and links (5.2:1), `#57606a` muted text (6.4:1). WCAG AA or better throughout. |

Default is the safe fallback:

- Its files never change. A test checks their hashes.
- Its View CSS cannot be edited, so bad CSS can never break it.
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
| `plainpad/models.py` | `Category`, `CategoryListing`, `Theme`, `RenderedPage` | Plain data classes |
| `plainpad/crud.py` | `NoteStore`, `timestamp_name()`, `NoteNameError` | Create, read, update, delete note files |
| `plainpad/atomic_file.py` | `write_text_atomically()` | The one crash-safe write, used by notes, index, and CSS |
| `plainpad/categories.py` | `CategoryIndex` | Load, change, and save `index.json` |
| `plainpad/search.py` | `find_matching_notes()` | Keyword search |
| `plainpad/library.py` | `Library` | Facade over notes, categories, search |
| `plainpad/render.py` | `MarkdownRenderer` | Markdown and CSS to an HTML page |
| `plainpad/code_blocks.py` | `add_copy_links()` | Copy links on code blocks, and each block's text |
| `plainpad/theme_store.py` | `ThemeStore` | Find themes and read their stylesheets |
| `plainpad/style_store.py` | `StyleStore` | Load and save each theme's View CSS; Default is read-only |
| `plainpad/theme.py` | `apply_theme()` | Put a theme's `app.qss` on the application |
| `plainpad/autosave.py` | `AutosaveTimer` | The 4 second idle timer |
| `plainpad/gui/main_window.py` | `MainWindow` | Layout and signal wiring |
| `plainpad/gui/tree_commands.py` | `TreeCommands` | Create, rename, move, delete notes and categories |
| `plainpad/gui/session.py` | `SessionMemory` | Window size, splitter, last note via `QSettings` |
| `plainpad/gui/actions.py` | `Actions`, `populate_menu_bar()` | Menu items and key bindings |
| `plainpad/gui/sidebar.py` | `Sidebar` | Search box above the tree |
| `plainpad/gui/note_tree.py` | `NoteTree` | Collapsible tree, drag and drop |
| `plainpad/gui/tree_filter.py` | `TreeFilter` | Search filtering and restoring expanded state |
| `plainpad/gui/tree_items.py` | `make_item()`, `identity_of()` | What a tree row is and how to read it |
| `plainpad/gui/tab_area.py` | `TabArea` | The three tabs; flush and render on tab change |
| `plainpad/gui/editor_tab.py` | `EditorTab` | Markdown editor, per-note undo |
| `plainpad/gui/preview_tab.py` | `PreviewTab`, `ExternalLinkPage` | Rendered view |
| `plainpad/gui/settings_tab.py` | `SettingsTab` | CSS editor |
| `plainpad/gui/dialogs.py` | `ask_for_name()`, `confirm()`, `show_about()` | The modal prompts |
| `plainpad/themes/<name>/` | `app.qss`, `preview.css`, `theme.json` | One theme; see 9 |
| `tests/test_*.py` | | Unit tests for layer 1 and 2 |
| `tests/test_gui.py` | | pytest-qt tests of the window: autosave, undo, search, rename, delete, failed saves, keyboard browsing, copy links, themes |

Size: about 2,500 lines of Python (half of it docstrings and comments)
across 31 source files. `main_window.py` and `note_tree.py` run a little
over the 200 line guideline.

## 11. Out of scope

- Multiple notes open at once, or multiple windows
- Nested categories, tags, or a note in more than one category
- Sync, encryption, export, printing, images pasted into notes
- Syntax highlighting in the editor or in rendered code blocks
- Find and replace inside a note
- Undo history that survives a restart
