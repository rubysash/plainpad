"""Applying a theme's window stylesheet to the application.

The stylesheets live in the themes/ folder; see theme_store.py. The
rendered markdown view is styled separately by the theme's preview.css.
"""

from PyQt6.QtWidgets import QApplication

from plainpad.config import QT_STYLE_NAME


def apply_theme(application: QApplication, qss: str) -> None:
    """Set a theme's stylesheet on the whole application.

    The Fusion style is used underneath because the native Windows style
    ignores parts of a stylesheet and draws tree arrows that vanish on a
    dark background.
    """
    application.setStyle(QT_STYLE_NAME)
    application.setStyleSheet(qss)
