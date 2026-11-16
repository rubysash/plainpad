"""Double-click launcher for Plainpad on Windows.

A .pyw file runs under pythonw, which opens no console window. Windows
starts it with whichever Python owns the .pyw file type, usually the global
one, which does not have PyQt6. So the launcher first hands itself over to
the project's .venv, then starts the app there.

pythonw has nowhere to print errors, so a failure at startup is shown in a
message box instead of disappearing silently.
"""

import ctypes
import subprocess
import sys
import traceback
from pathlib import Path

# The script's folder is first on sys.path, so this works under any Python.
# config has no third-party imports.
from plainpad.config import APP_NAME, VENV_DIR, VENV_PYTHONW

# MessageBoxW style: an OK button with the error icon.
MB_ICONERROR = 0x10


def show_error(message: str) -> None:
    """Show a Windows error box, since pythonw has no console."""
    ctypes.windll.user32.MessageBoxW(None, message, APP_NAME, MB_ICONERROR)


def running_in_project_venv() -> bool:
    """Return True if this interpreter belongs to the project's .venv."""
    return Path(sys.prefix).resolve() == VENV_DIR.resolve()


def main() -> int:
    """Relaunch under the .venv if needed, otherwise run Plainpad."""
    if not running_in_project_venv():
        if not VENV_PYTHONW.exists():
            show_error(
                f"Cannot find {VENV_PYTHONW}.\n\n"
                "Create the virtual environment first; see README.md."
            )
            return 1
        subprocess.Popen([str(VENV_PYTHONW), str(Path(__file__).resolve())])
        return 0
    try:
        from plainpad.app import main as run_app
        return run_app()
    except Exception:
        show_error(f"{APP_NAME} could not start.\n\n{traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
