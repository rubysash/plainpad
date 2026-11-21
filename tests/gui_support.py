"""Stand-ins and shortcuts shared by the GUI tests."""

from pathlib import Path

from pytestqt.qtbot import QtBot

from plainpad.desktop_launch import DesktopLauncher
from plainpad.gui.main_window import MainWindow

FAST_AUTOSAVE_MS = 50


def answer_yes(*_args: object) -> bool:
    """Stand-in for dialogs.confirm that always answers Yes."""
    return True


class RecordingLauncher(DesktopLauncher):
    """A Windows DesktopLauncher that records commands instead of running
    them, so tests open no windows."""

    def __init__(self) -> None:
        """Pretend Windows Terminal is installed."""
        super().__init__("win32", lambda program: program)
        self.started: list[tuple[list[str], Path]] = []

    def start(self, command: list[str], folder: Path) -> None:
        """Record the command and the folder it would run from."""
        self.started.append((command, folder))


def new_note(window: MainWindow, qtbot: QtBot, text: str = "") -> str:
    """Create a note through the window, type ``text``, return its name."""
    window._commands.create_note()
    editor = window._tabs.editor
    if text:
        qtbot.keyClicks(editor, text)
    return editor.current_note_name()


def status(window: MainWindow) -> str:
    """Return the status bar text."""
    return window.statusBar().currentMessage()
