# CLAUDE.md

Plainpad: a PyQt6 markdown notepad with autosave and a green CRT theme.
`SPEC.md` is the source of truth for behavior. Update it in the same change
whenever behavior changes.

## Commands

Always use the project `.venv`. Never install into the global Python.

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt   # includes requirements.txt
python -m plainpad                    # run
pytest                                # tests
flake8 plainpad tests                 # PEP 8 check, must be clean
```

## Architecture

Three layers. A lower layer never imports a higher one.

1. Storage and logic: `crud.py`, `categories.py`, `search.py`, `render.py`,
   `style_store.py`, `atomic_file.py`, `models.py`, `config.py`. No Qt
   imports here.
2. Facade: `library.py`. The GUI reads and writes notes and categories only
   through `Library`.
3. GUI: `plainpad/gui/`, plus `autosave.py` and `theme.py`.

Widgets do not call each other. A widget emits a signal, and `MainWindow`
connects it to a `Library` call or to another widget's public method.
`MainWindow` wires things together and holds no business logic.

A note's identity is its file name without `.md`. A category's identity is
its id in `index.json`, never its display name.

## Code rules

- PEP 8, 79 column lines, type hints on every signature.
- Every module, class, and public method has a docstring that says what it
  is for. Comments explain why, not what.
- Keep functions under about 30 lines and files under about 200 lines. When
  one grows past that, split it by responsibility into a named class or
  module.
- No `utils.py`, `helpers.py`, `misc.py`, or functions named `_helper`,
  `_do_x`, `_handle_stuff`. If code needs a home, it belongs to a class or
  module named after what it does.
- No function that exists only to be called once from one place to shorten
  another function. Split by responsibility, not by line count.
- Constants go in `config.py`. No magic numbers or paths in other files.
- Styling goes in `resources/crt.qss` and `resources/default_preview.css`.
  No inline `setStyleSheet` strings in widgets.
- Every file write goes through `atomic_file.write_text_atomically`.
- The app never erases user notes. Delete moves to `data/trash/`.
- Layers 1 and 2 get unit tests using pytest's `tmp_path`. Tests never touch
  the real `data/` folder.

## Gotchas

- A `QTextDocument` used by `QPlainTextEdit` must have a
  `QPlainTextDocumentLayout` set on it, or the editor shows nothing.
- `QWebEngineView` needs `PyQt6-WebEngine` imported before `QApplication`
  is created.
- Programmatic `setPlainText` fires `textChanged`. Block signals or check
  `document().isModified()` so loading a note does not trigger an autosave.
- Windows file names are case-insensitive. Compare note names with
  `casefold()`.
