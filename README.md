# Plainpad

A small markdown notepad with a green CRT look. Notes save themselves four
seconds after you stop typing.

> Status: MVP. Everything in [SPEC.md](SPEC.md) is implemented.

## Features

- Notes are plain `.md` files you can open in any other editor
- Categories you define, collapsed by default, with drag and drop
- Keyword search over note names and text that filters the tree
- Edit tab for markdown, View tab for the rendered page
- Right-click the sidebar to open the notes folder in Explorer (Finder,
  or your Linux file manager), or a terminal there. On Windows you can
  pick Windows Terminal, Command Prompt, or PowerShell
- A copy button on every code block in the View tab
- Arrow keys in the sidebar browse notes after a short pause
- Autosave, per-note undo and redo
- Themes under Settings > Theme: CRT green, Dark (Darkly), Light, and a
  frozen Default you can always fall back to. Add your own by dropping a
  folder into `plainpad/themes/`. Edit a theme's `preview.css` by hand to
  restyle the View tab

## Setup

Requires Python 3.13 on Windows.

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
python -m plainpad
```

Or double-click `plainpad.pyw` in the project folder. It opens no console
window and switches to the project's `.venv` by itself, so the venv does
not need to be activated. If the app fails to start, the error is shown in
a message box.

## Keys

| Key | Action |
| --- | --- |
| Ctrl+N | New note, named with the current date and time |
| Ctrl+Shift+N | New category |
| F2 | Rename the selected note or category |
| Del | Delete the selected note or category |
| Ctrl+F | Jump to search |
| Ctrl+E | Switch between Edit and View |
| Ctrl+1 / 2 | Edit / View tab |
| Ctrl+S | Save now |
| Ctrl+Z / Ctrl+Y | Undo / redo |
| Ctrl+Q | Exit |

## Where your notes live

```
data/
  notes/        your notes, one .md file each
  trash/        notes you deleted
  index.json    categories
```

Deleting a note moves it to `data/trash/`. Deleting a category moves its
notes to Uncategorized.

## Development

```powershell
pip install -r requirements-dev.txt
pytest
flake8 plainpad tests
```

The code is in three layers: storage (`crud.py`, `categories.py`,
`search.py`), one facade (`library.py`), and the widgets in `plainpad/gui/`.
The file-by-file table is in [SPEC.md](SPEC.md#10-code-layout).
