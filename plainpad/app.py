"""Application entry point.

Builds the storage objects, applies the theme, and shows the main window.
This is the only module that knows how all three layers are constructed.
"""

import sys

# WebEngine must be imported before the QApplication is created.
from PyQt6 import QtWebEngineWidgets  # noqa: F401
from PyQt6.QtWidgets import QApplication

from plainpad.config import (
    APP_NAME,
    DATA_DIR,
    DEFAULT_PREVIEW_CSS_FILE,
    ORGANIZATION_NAME,
    PREVIEW_CSS_FILE_NAME,
)
from plainpad.gui.main_window import MainWindow
from plainpad.library import Library
from plainpad.style_store import StyleStore
from plainpad.theme import apply_crt_theme


def main() -> int:
    """Start Plainpad and return the process exit code."""
    application = QApplication(sys.argv)
    # QSettings reads these to decide where the session is remembered.
    application.setOrganizationName(ORGANIZATION_NAME)
    application.setApplicationName(APP_NAME)
    apply_crt_theme(application)

    library = Library(DATA_DIR)
    style_store = StyleStore(
        DATA_DIR / PREVIEW_CSS_FILE_NAME, DEFAULT_PREVIEW_CSS_FILE
    )
    window = MainWindow(library, style_store)
    window.show()
    return application.exec()
