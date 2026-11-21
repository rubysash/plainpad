"""Images and formatted text moving between notes and other programs.

ClipboardCommands is the half of the window's wiring that pastes pictures
and formatted text into the open note, copies a note out as rich text,
and copies a single stored image out as a picture.
It calls Library, tells the editor what to insert, and reports back
through a signal that MainWindow connects.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from PyQt6.QtCore import QMimeData, QObject, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication

from plainpad.config import RICH_COPY_MARKER_FORMAT
from plainpad.gui.editor_tab import EditorTab
from plainpad.gui.pasted_content import PastedContent
from plainpad.library import ImageFormatError, ImageSourceError, Library


@contextmanager
def busy_cursor() -> Iterator[None]:
    """Show the wait cursor while images are read or downloaded."""
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        yield
    finally:
        QApplication.restoreOverrideCursor()


class ClipboardCommands(QObject):
    """Pastes into and copies out of the open note through the Library."""

    # A message for the status bar.
    status_message = pyqtSignal(str)

    def __init__(
        self, library: Library, editor: EditorTab, parent: QObject
    ) -> None:
        """Remember the collaborators."""
        super().__init__(parent)
        self._library = library
        self._editor = editor

    # --- Into a note -----------------------------------------------------

    def insert_images(self, content: PastedContent) -> None:
        """Store the images of a paste or drop and link them in the note.

        Files are copied as they are. Otherwise the address the picture
        came from is tried first, then the bitmap itself.
        """
        library = self._library
        address, bitmap = content.image_address(), content.bitmap()
        with busy_cursor():
            links = self.stored_links([
                lambda path=path: library.add_image(path.read_bytes())
                for path in content.image_files()
            ])
            if not links and address is not None:
                links = self.stored_links(
                    [lambda: library.add_image_from(address)]
                )
            if not links and bitmap is not None:
                links = self.stored_links([lambda: library.add_image(bitmap)])
        if not links:
            self.status_message.emit("That image could not be added.")
            return
        self._editor.insert_markdown("\n".join(links))
        self.status_message.emit(f"Added {len(links)} image(s)")

    def stored_links(self, attempts: list[Callable[[], str]]) -> list[str]:
        """Run each attempt to store an image; return the links made.

        An attempt that is refused, because the file is unreadable, not
        an image, or out of reach, is skipped.
        """
        links = []
        for store in attempts:
            try:
                links.append(store())
            except (ImageFormatError, ImageSourceError, OSError):
                continue
        return links

    def paste_formatted(self) -> None:
        """Paste the clipboard into the note as markdown, with images.

        Formatted text from a document or an email is converted. A lone
        picture is pasted as an image, and plain text as plain text.
        """
        if not (self._editor.isEnabled() and self._editor.isVisible()):
            self.status_message.emit("Open a note's Edit tab to paste.")
            return
        mime = QApplication.clipboard().mimeData()
        content = PastedContent(mime)
        if content.offers_images():
            self.insert_images(content)
            return
        if not mime.hasHtml():
            self._editor.paste()
            return
        with busy_cursor():
            imported = self._library.import_rich_text(mime.html())
        self._editor.insert_markdown(imported.markdown)
        if imported.images_missed:
            self.status_message.emit(
                f"Pasted; {imported.images_missed} image(s) could not be"
                " copied and still point at their source"
            )
        else:
            self.status_message.emit("Pasted formatted text")

    # --- Out of a note ---------------------------------------------------

    def copy_note_as_rich_text(self) -> None:
        """Put the whole open note on the clipboard as formatted text."""
        if self._editor.current_note_name() is None:
            return
        text = self._editor.current_text()
        try:
            html = self._library.rich_html_of_note(text)
        except OSError as error:
            self.status_message.emit(f"Could not copy: {error}")
            return
        self.put_rich_text(html, text)
        self.status_message.emit("Copied note as rich text")

    def replace_selection_copy(self, copied_html: str, text: str) -> None:
        """Swap the View tab's raw copy for one other programs can use."""
        try:
            html = self._library.rich_html_of_selection(copied_html)
        except OSError as error:
            self.status_message.emit(f"Could not copy images: {error}")
            return
        self.put_rich_text(html, text)
        self.status_message.emit("Copied selection as rich text")

    def copy_image(self, address: str) -> None:
        """Put one stored image on the clipboard as a picture, no HTML.

        Gmail in Firefox drops every picture that arrives inside HTML
        but takes a lone file or bitmap, so both go and nothing else.
        The file keeps every byte, which keeps a GIF animated; the
        bitmap is for programs that take no files.
        """
        path = self._library.stored_image_file(address)
        if path is None:
            self.status_message.emit("Could not find that image")
            return
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(path))])
        bitmap = QImage(str(path))
        if not bitmap.isNull():
            mime.setImageData(bitmap)
        mime.setData(RICH_COPY_MARKER_FORMAT, b"1")
        QApplication.clipboard().setMimeData(mime)
        self.status_message.emit("Copied image")

    def put_rich_text(self, html: str, text: str) -> None:
        """Set the clipboard to formatted text with a plain twin.

        The marker format tells the View tab this copy is already done.
        """
        mime = QMimeData()
        mime.setHtml(html)
        mime.setText(text)
        mime.setData(RICH_COPY_MARKER_FORMAT, b"1")
        QApplication.clipboard().setMimeData(mime)
