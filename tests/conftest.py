"""Shared test setup, and the window fixture every GUI test uses.

GUI tests run without a screen. WebEngine must be imported before
pytest-qt creates the QApplication, so it is imported here, at collection
time.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6 import QtWebEngineWidgets  # noqa: E402, F401
from PyQt6 import sip  # noqa: E402
from PyQt6.QtCore import QSettings  # noqa: E402
from pytestqt.qtbot import QtBot  # noqa: E402

from plainpad.config import THEMES_DIR  # noqa: E402
from plainpad.gui import editor_tab, main_window, tree_commands  # noqa: E402
from plainpad.gui.main_window import MainWindow  # noqa: E402
from plainpad.image_sources import ImageSourceReader  # noqa: E402
from plainpad.library import Library  # noqa: E402
from plainpad.theme_store import ThemeStore  # noqa: E402
from tests.gui_support import (  # noqa: E402
    FAST_AUTOSAVE_MS,
    RecordingLauncher,
    answer_yes,
)
from tests.image_samples import FakeWeb  # noqa: E402


@pytest.fixture
def window(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[MainWindow]:
    """A shown MainWindow over an empty data folder.

    The window is destroyed at once after the test rather than left to
    pytest-qt, because WebEngine crashes at exit if a rendered page
    outlives the application.
    """
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(tmp_path / "settings"),
    )
    monkeypatch.setattr(editor_tab, "AUTOSAVE_DELAY_MS", FAST_AUTOSAVE_MS)
    monkeypatch.setattr(main_window, "confirm", answer_yes)
    monkeypatch.setattr(tree_commands, "confirm", answer_yes)
    # No test may reach the real network.
    offline = ImageSourceReader(FakeWeb({}))
    library = Library(tmp_path / "data", offline)
    win = MainWindow(library, ThemeStore(THEMES_DIR), RecordingLauncher())
    win.show()
    yield win
    win.close()
    sip.delete(win)
