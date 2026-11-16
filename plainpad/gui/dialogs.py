"""The modal prompts the application uses."""

from PyQt6.QtWidgets import QInputDialog, QMessageBox, QWidget

from plainpad import __version__
from plainpad.config import APP_NAME


def ask_for_name(parent: QWidget, title: str, label: str) -> str | None:
    """Ask the user to type a name.

    Returns the trimmed text, or None if the user cancelled or typed
    nothing.
    """
    text, accepted = QInputDialog.getText(parent, title, label)
    text = text.strip()
    return text if accepted and text else None


def confirm(parent: QWidget, title: str, question: str) -> bool:
    """Ask a yes/no question. Returns True only if the user chose Yes.

    No is the default button, so pressing Enter by accident is safe.
    """
    buttons = QMessageBox.StandardButton
    answer = QMessageBox.question(
        parent, title, question, buttons.Yes | buttons.No, buttons.No
    )
    return answer == buttons.Yes


def show_about(parent: QWidget) -> None:
    """Show the application name and version."""
    QMessageBox.about(
        parent,
        f"About {APP_NAME}",
        f"{APP_NAME} {__version__}\n\n"
        "A markdown notepad with autosave and a green CRT theme.",
    )
