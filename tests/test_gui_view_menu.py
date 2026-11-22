"""GUI tests for the View tab's right-click menu and Copy image.

Gmail in Firefox drops any picture that comes inside HTML, so a copied
picture must reach the clipboard as a file and a bitmap only.
"""

from pathlib import Path

import pytest
from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, QPoint, Qt, QUrl
from PyQt6.QtGui import QColor, QContextMenuEvent, QImage
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QMenu
from pytestqt.qtbot import QtBot

from plainpad.config import RICH_COPY_MARKER_FORMAT
from plainpad.gui.main_window import MainWindow
from plainpad.library import Library
from tests.gui_support import new_note, status
from tests.image_samples import GIF


@pytest.fixture
def library(window: MainWindow) -> Library:
    """The Library behind the window."""
    return window._library


def big_png() -> bytes:
    """A 200 by 100 PNG, large enough to right-click on."""
    image = QImage(200, 100, QImage.Format.Format_RGB32)
    image.fill(QColor("#2a7ae2"))
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data)


def stored_path(library: Library, link: str) -> Path:
    """Return the file a markdown image link points at."""
    return library.images_folder() / link.removeprefix("![](../images/")[:-1]


def test_copy_image_puts_file_and_bitmap_but_no_html(
    window: MainWindow, library: Library
) -> None:
    path = stored_path(library, library.add_image(big_png()))
    window._clipboard.copy_image(path.as_uri())
    mime = QApplication.clipboard().mimeData()
    assert [url.toLocalFile() for url in mime.urls()] == [
        QUrl.fromLocalFile(str(path)).toLocalFile()
    ]
    assert mime.hasImage()
    assert not mime.hasHtml()
    assert mime.hasFormat(RICH_COPY_MARKER_FORMAT)
    assert status(window) == "Copied image"


def test_copy_image_of_undecodable_file_still_copies_the_file(
    window: MainWindow, library: Library
) -> None:
    # The sample GIF is only a header, so no bitmap can be made of it.
    path = stored_path(library, library.add_image(GIF))
    window._clipboard.copy_image(path.as_uri())
    mime = QApplication.clipboard().mimeData()
    assert len(mime.urls()) == 1 and not mime.hasImage()


def test_copy_image_of_unknown_address_says_so(window: MainWindow) -> None:
    window._clipboard.copy_image("https://example.com/a.png")
    assert status(window) == "Could not find that image"


def test_view_tab_leaves_a_copied_picture_alone(
    window: MainWindow, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    preview = window._tabs.preview
    announced: list[str] = []
    preview.selection_copied.connect(
        lambda html, _text: announced.append(html)
    )
    monkeypatch.setattr(QApplication, "focusWidget", lambda: preview)
    mime = QApplication.clipboard().mimeData().__class__()
    mime.setHtml('<img src="https://example.com/a.png">')
    mime.setImageData(QImage(2, 2, QImage.Format.Format_RGB32))
    QApplication.clipboard().setMimeData(mime)
    assert announced == []


def right_click_view(
    window: MainWindow,
    qtbot: QtBot,
    monkeypatch: pytest.MonkeyPatch,
    markdown: str,
) -> QMenu:
    """Show ``markdown`` in the View tab, right-click near its top left.

    Returns the menu that opened. It is caught as it opens instead of
    waiting for a click. Only exec keeps a parentless menu alive while
    it is open; a popup was freed unseen, so a patched popup would
    never be reached here.
    """
    shown: list[QMenu] = []
    monkeypatch.setattr(QMenu, "exec", lambda menu, *_: shown.append(menu))
    new_note(window, qtbot)
    window._tabs.editor.insert_markdown(markdown)
    preview = window._tabs.preview
    with qtbot.waitSignal(preview.loadFinished, timeout=10000):
        window._tabs.show_view_tab()
    target = preview.focusProxy() or preview
    # Past the page and paragraph margins, so on the first word, link,
    # or picture.
    at = QPoint(24, 32)
    QTest.mouseClick(target, Qt.MouseButton.RightButton, pos=at)
    # A real right-click also sends this; the engine opens its menu on it.
    QApplication.sendEvent(
        target,
        QContextMenuEvent(
            QContextMenuEvent.Reason.Mouse, at, target.mapToGlobal(at)
        ),
    )
    qtbot.waitUntil(lambda: bool(shown), timeout=10000)
    return shown[0]


def labels_of(menu: QMenu) -> list[str]:
    """Return a menu's item labels, with "|" for a separator."""
    return [
        "|" if action.isSeparator() else action.text().replace("&", "")
        for action in menu.actions()
    ]


def test_right_click_on_text_offers_only_copy_and_select_all(
    window: MainWindow, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    menu = right_click_view(window, qtbot, monkeypatch, "Words here")
    assert labels_of(menu) == ["Copy", "Select all"]


def test_right_click_on_link_adds_copy_link_address(
    window: MainWindow, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    menu = right_click_view(
        window, qtbot, monkeypatch, "[example link](https://example.com/page)"
    )
    assert labels_of(menu) == [
        "Copy", "Select all", "|", "Copy link address"
    ]
    menu.actions()[-1].trigger()
    mime = QApplication.clipboard().mimeData()
    assert mime.text() == "https://example.com/page"
    assert not mime.hasHtml()
    assert status(window) == "Copied link address"


def test_right_click_copy_image_copies_the_stored_file(
    window: MainWindow,
    library: Library,
    qtbot: QtBot,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    link = library.add_image(big_png())
    menu = right_click_view(window, qtbot, monkeypatch, link)
    assert labels_of(menu) == ["Copy", "Select all", "|", "Copy image"]
    menu.actions()[-1].trigger()
    mime = QApplication.clipboard().mimeData()
    assert not mime.hasHtml()
    assert mime.urls()[0].toLocalFile() == QUrl.fromLocalFile(
        str(stored_path(library, link))
    ).toLocalFile()
