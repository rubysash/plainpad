"""GUI tests for images and rich copy and paste, using pytest-qt.

The clipboard here is the offscreen platform's own, not the desktop's.
"""

from pathlib import Path

import pytest
from PyQt6.QtCore import QMimeData, QUrl
from PyQt6.QtGui import QColor, QImage
from PyQt6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from plainpad.config import RICH_COPY_MARKER_FORMAT
from plainpad.gui.main_window import MainWindow
from plainpad.library import Library
from tests.gui_support import new_note, status
from tests.image_samples import GIF, PNG, PNG_DATA_ADDRESS


@pytest.fixture
def library(window: MainWindow) -> Library:
    """The Library behind the window."""
    return window._library


def stored_images(library: Library) -> list[Path]:
    """Return every file in the image folder."""
    return sorted(library.images_folder().iterdir())


def put_on_clipboard(**flavors: object) -> None:
    """Set the clipboard from ``text``, ``html``, ``image``, ``urls``."""
    mime = QMimeData()
    if "text" in flavors:
        mime.setText(flavors["text"])
    if "html" in flavors:
        mime.setHtml(flavors["html"])
    if "image" in flavors:
        mime.setImageData(flavors["image"])
    if "urls" in flavors:
        mime.setUrls(flavors["urls"])
    QApplication.clipboard().setMimeData(mime)


def red_square() -> QImage:
    """A small bitmap, as a screenshot would put on the clipboard."""
    image = QImage(4, 4, QImage.Format.Format_RGB32)
    image.fill(QColor("red"))
    return image


def test_pasting_a_bitmap_stores_a_png_and_links_it(
    window: MainWindow, library: Library, qtbot: QtBot
) -> None:
    new_note(window, qtbot, "Shot: ")
    put_on_clipboard(image=red_square())
    window._actions.paste.trigger()
    (stored,) = stored_images(library)
    assert stored.suffix == ".png"
    assert QImage(str(stored)).pixelColor(0, 0) == QColor("red")
    editor = window._tabs.editor
    assert editor.current_text() == f"Shot: ![](../images/{stored.name})"
    assert status(window) == "Added 1 image(s)"


def test_pasting_image_files_copies_their_exact_bytes(
    window: MainWindow, library: Library, qtbot: QtBot, tmp_path: Path
) -> None:
    animated, still = tmp_path / "cat.GIF", tmp_path / "dog.png"
    animated.write_bytes(GIF)
    still.write_bytes(PNG)
    new_note(window, qtbot)
    put_on_clipboard(
        urls=[QUrl.fromLocalFile(str(path)) for path in (animated, still)]
    )
    window._actions.paste.trigger()
    assert {path.read_bytes() for path in stored_images(library)} == {
        GIF,
        PNG,
    }
    lines = window._tabs.editor.current_text().splitlines()
    assert len(lines) == 2
    assert lines[0].endswith(".gif)") and lines[1].endswith(".png)")


def test_dropping_an_image_is_undoable_and_autosaved(
    window: MainWindow, library: Library, qtbot: QtBot, tmp_path: Path
) -> None:
    picture = tmp_path / "cat.gif"
    picture.write_bytes(GIF)
    name = new_note(window, qtbot)
    editor = window._tabs.editor
    dropped = QMimeData()
    dropped.setUrls([QUrl.fromLocalFile(str(picture))])
    assert editor.canInsertFromMimeData(dropped)
    # Qt hands a drop to the same method as a paste.
    editor.insertFromMimeData(dropped)
    link = editor.current_text()
    qtbot.waitUntil(lambda: library.read_note(name) == link)
    editor.undo()
    assert editor.current_text() == ""
    # Removing the link never removes the file.
    assert len(stored_images(library)) == 1


def test_browser_copy_image_prefers_the_original_over_the_bitmap(
    window: MainWindow, library: Library, qtbot: QtBot, tmp_path: Path
) -> None:
    original = tmp_path / "anim.gif"
    original.write_bytes(GIF)
    new_note(window, qtbot)
    put_on_clipboard(
        image=red_square(), html=f'<img src="{original.as_uri()}">'
    )
    window._actions.paste.trigger()
    (stored,) = stored_images(library)
    assert stored.read_bytes() == GIF


def test_unreachable_original_falls_back_to_the_bitmap(
    window: MainWindow, library: Library, qtbot: QtBot
) -> None:
    new_note(window, qtbot)
    put_on_clipboard(
        image=red_square(), html='<img src="https://example.com/a.gif">'
    )
    window._actions.paste.trigger()
    (stored,) = stored_images(library)
    assert stored.suffix == ".png"


def test_file_that_is_not_an_image_is_refused(
    window: MainWindow, library: Library, qtbot: QtBot, tmp_path: Path
) -> None:
    fake = tmp_path / "notes.png"
    fake.write_text("not a picture", encoding="utf-8")
    new_note(window, qtbot)
    put_on_clipboard(urls=[QUrl.fromLocalFile(str(fake))])
    window._actions.paste.trigger()
    assert stored_images(library) == []
    assert window._tabs.editor.current_text() == ""
    assert status(window) == "That image could not be added."


def test_plain_paste_of_formatted_text_stays_plain(
    window: MainWindow, library: Library, qtbot: QtBot
) -> None:
    new_note(window, qtbot)
    # A spreadsheet also offers a picture of the copied cells.
    put_on_clipboard(
        text="a\tb", html="<table><tr><td>a</td><td>b</td></tr></table>",
        image=red_square(),
    )
    window._actions.paste.trigger()
    assert window._tabs.editor.current_text() == "a\tb"
    assert stored_images(library) == []


def test_paste_formatted_converts_html_and_stores_images(
    window: MainWindow, library: Library, qtbot: QtBot
) -> None:
    new_note(window, qtbot)
    put_on_clipboard(
        text="Title bold",
        html=(
            "<h2>Title</h2><p><b>bold</b></p>"
            f'<p><img src="{PNG_DATA_ADDRESS}"></p>'
            '<p><img src="cid:unreachable"></p>'
        ),
    )
    window._actions.paste_formatted.trigger()
    (stored,) = stored_images(library)
    assert window._tabs.editor.current_text() == (
        f"## Title\n\n**bold**\n\n![](../images/{stored.name})\n\n"
        "![](cid:unreachable)"
    )
    assert status(window).startswith("Pasted; 1 image(s) could not")


def test_paste_formatted_needs_the_edit_tab(
    window: MainWindow, qtbot: QtBot
) -> None:
    new_note(window, qtbot)
    window._tabs.show_view_tab()
    put_on_clipboard(text="x", html="<b>x</b>")
    window._actions.paste_formatted.trigger()
    assert window._tabs.editor.current_text() == ""
    assert status(window) == "Open a note's Edit tab to paste."


def test_copy_note_as_rich_text_embeds_images(
    window: MainWindow, library: Library, qtbot: QtBot
) -> None:
    new_note(window, qtbot)
    text = f"# Title\n\n{library.add_image(PNG)}"
    window._tabs.editor.insert_markdown(text)
    window._actions.copy_note_rich.trigger()
    mime = QApplication.clipboard().mimeData()
    assert "<h1>Title</h1>" in mime.html()
    assert PNG_DATA_ADDRESS in mime.html()
    assert mime.text() == text
    assert mime.hasFormat(RICH_COPY_MARKER_FORMAT)
    assert status(window) == "Copied note as rich text"


def test_view_selection_copy_is_replaced_with_portable_html(
    window: MainWindow, library: Library, qtbot: QtBot
) -> None:
    new_note(window, qtbot)
    image = library.images_folder() / (
        library.add_image(PNG).removeprefix("![](../images/")[:-1]
    )
    window._clipboard.replace_selection_copy(
        '<h1 style="color: rgb(51, 255, 51);">T</h1>'
        f'<img src="{image.as_uri()}">',
        "T",
    )
    mime = QApplication.clipboard().mimeData()
    assert "style" not in mime.html()
    assert PNG_DATA_ADDRESS in mime.html()
    assert mime.text() == "T"
    assert status(window) == "Copied selection as rich text"


def test_view_tab_only_announces_its_own_raw_copies(
    window: MainWindow, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    new_note(window, qtbot)
    preview = window._tabs.preview
    announced: list[str] = []
    preview.selection_copied.connect(
        lambda html, _text: announced.append(html)
    )
    # Focus is elsewhere: another program, or the editor, made the copy.
    put_on_clipboard(text="x", html="<b>x</b>")
    assert announced == []
    monkeypatch.setattr(QApplication, "focusWidget", lambda: preview)
    put_on_clipboard(text="code")
    assert announced == []
    put_on_clipboard(text="x", html="<b>x</b>")
    # The replacement carries the marker, so it is not announced again.
    assert len(announced) == 1
    assert QApplication.clipboard().mimeData().hasFormat(
        RICH_COPY_MARKER_FORMAT
    )


def test_view_tab_resolves_links_against_the_notes_folder(
    window: MainWindow, library: Library, qtbot: QtBot
) -> None:
    new_note(window, qtbot, "hello")
    preview = window._tabs.preview
    with qtbot.waitSignal(preview.loadFinished, timeout=10000):
        window._tabs.show_view_tab()
    folder = QUrl.fromLocalFile(str(library.notes_folder())).toString()
    assert preview.url().toString() == f"{folder}/"


def test_clean_up_moves_unlinked_images_to_trash(
    window: MainWindow, library: Library, qtbot: QtBot
) -> None:
    new_note(window, qtbot)
    window._tabs.editor.insert_markdown(library.add_image(PNG))
    library.add_image(GIF)
    # The link above is not saved yet; cleaning up must save it first.
    window._actions.clean_up_images.trigger()
    assert [path.read_bytes() for path in stored_images(library)] == [PNG]
    assert status(window) == "Moved 1 unused image(s) to the trash"


def test_real_view_copy_reaches_the_clipboard_portable(
    window: MainWindow, library: Library, qtbot: QtBot
) -> None:
    new_note(window, qtbot)
    window._tabs.editor.insert_markdown(
        f"# Heading\n\nwords {library.add_image(PNG)}"
    )
    preview = window._tabs.preview
    with qtbot.waitSignal(preview.loadFinished, timeout=10000):
        window._tabs.show_view_tab()
    preview.setFocus()
    preview.selectAll()
    qtbot.waitUntil(preview.hasSelection, timeout=10000)
    with qtbot.waitSignal(preview.selection_copied, timeout=10000):
        window._actions.copy.trigger()
    mime = QApplication.clipboard().mimeData()
    assert mime.hasFormat(RICH_COPY_MARKER_FORMAT)
    assert "Heading" in mime.html()
    assert "style=" not in mime.html()
    assert "<!--" not in mime.html() and "<body>" not in mime.html()
    assert PNG_DATA_ADDRESS in mime.html()
