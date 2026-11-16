"""Shared test setup.

GUI tests run without a screen. WebEngine must be imported before
pytest-qt creates the QApplication, so it is imported here, at collection
time.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6 import QtWebEngineWidgets  # noqa: E402, F401
