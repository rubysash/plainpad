"""The green CRT look for the application chrome.

The colors and fonts themselves are in resources/crt.qss. This module only
loads that file onto the application. The rendered markdown view is styled
separately by the user's CSS; see style_store.py.
"""

from PyQt6.QtWidgets import QApplication

from plainpad.config import QSS_FILE, QT_STYLE_NAME, TEXT_ENCODING


def apply_crt_theme(application: QApplication) -> None:
    """Read config.QSS_FILE and set it as the application stylesheet.

    The Fusion style is used underneath because the native Windows style
    ignores parts of a stylesheet and draws tree arrows that vanish on a
    black background.
    """
    application.setStyle(QT_STYLE_NAME)
    application.setStyleSheet(QSS_FILE.read_text(encoding=TEXT_ENCODING))
