"""The View tab: the open note rendered as a styled HTML page."""

from pathlib import Path

from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QContextMenuEvent, QDesktopServices
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication, QWidget

from plainpad.config import (
    COPY_LINK_SCHEME,
    EXTERNAL_LINK_SCHEMES,
    PREVIEW_BACKGROUND_COLOR,
    RICH_COPY_MARKER_FORMAT,
)
from plainpad.gui.view_menu import build_view_menu
from plainpad.render import MarkdownRenderer


class ExternalLinkPage(QWebEnginePage):
    """A web page that sends clicked links to the system browser.

    Without this, clicking a link in a note would navigate the View tab
    away from the note with no way back. Clicks on code block copy links
    are reported instead of followed.
    """

    # A code block's copy link was clicked: the block's index on the page.
    copy_requested = pyqtSignal(int)

    def acceptNavigationRequest(
        self,
        url: QUrl,
        navigation_type: QWebEnginePage.NavigationType,
        is_main_frame: bool,
    ) -> bool:
        """Open link clicks externally; allow the page's own load.

        Links to an anchor on the same page still scroll the page. Only
        web and mail links are handed to the system; others do nothing.
        """
        link_clicked = QWebEnginePage.NavigationType.NavigationTypeLinkClicked
        if navigation_type != link_clicked:
            return True
        without_fragment = QUrl.UrlFormattingOption.RemoveFragment
        if url.hasFragment() and url.matches(self.url(), without_fragment):
            return True
        if url.scheme() == COPY_LINK_SCHEME and url.path().isdigit():
            self.copy_requested.emit(int(url.path()))
        elif url.scheme() in EXTERNAL_LINK_SCHEMES:
            QDesktopServices.openUrl(url)
        return False


class PreviewTab(QWebEngineView):
    """Read-only rendered view of a note."""

    # A code block's text was put on the clipboard.
    code_copied = pyqtSignal()
    # A link's address was put on the clipboard.
    link_copied = pyqtSignal()
    # The page's selection was copied: the raw HTML and the plain text
    # the browser engine put on the clipboard.
    selection_copied = pyqtSignal(str, str)
    # Copy Image was chosen on a local picture: its file: address.
    image_copy_requested = pyqtSignal(str)

    def __init__(
        self,
        renderer: MarkdownRenderer,
        notes_folder: Path,
        parent: QWidget | None = None,
    ) -> None:
        """Install an ExternalLinkPage with JavaScript turned off.

        Notes may contain raw HTML, so scripts must never run. The page
        background is set to black so there is no white flash on load.
        ``notes_folder`` is what relative links in a note, such as its
        images, are resolved against.
        """
        super().__init__(parent)
        self._renderer = renderer
        # The trailing slash makes it a folder, not a file, to the page.
        self._base_url = QUrl.fromLocalFile(f"{notes_folder}/")
        self._code_blocks: list[str] = []
        page = ExternalLinkPage(self)
        page.settings().setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled, False
        )
        page.setBackgroundColor(QColor(PREVIEW_BACKGROUND_COLOR))
        page.copy_requested.connect(self.copy_code_block)
        self.setPage(page)
        QApplication.clipboard().dataChanged.connect(
            self.on_clipboard_changed
        )

    def show_markdown(self, markdown_text: str, css: str) -> None:
        """Render markdown with the given CSS and display the page."""
        rendered = self._renderer.render_page(markdown_text, css)
        self._code_blocks = rendered.code_blocks
        self.setHtml(rendered.html, self._base_url)

    def show_nothing(self) -> None:
        """Display an empty page, for when no note is open."""
        self._code_blocks = []
        self.setHtml("")

    def copy(self) -> None:
        """Copy the selection, as Edit > Copy does for a text box."""
        self.triggerPageAction(QWebEnginePage.WebAction.Copy)

    def selectAll(self) -> None:
        """Select the whole page, as Edit > Select All does."""
        self.triggerPageAction(QWebEnginePage.WebAction.SelectAll)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Show the short menu from ``build_view_menu`` at the pointer."""
        menu = build_view_menu(
            self.pageAction,
            self.lastContextMenuRequest(),
            self.copy_link,
            self.image_copy_requested.emit,
        )
        # exec, not popup: the menu has no parent, so Python frees it as
        # soon as this method returns, and a popup would vanish unseen.
        menu.exec(event.globalPos())

    def copy_link(self, address: str) -> None:
        """Put a link's address on the clipboard as plain text."""
        QApplication.clipboard().setText(address)
        self.link_copied.emit()

    def on_clipboard_changed(self) -> None:
        """Report a copy made from this page so it can be made portable.

        With JavaScript off, the selection's HTML can only be had from
        the clipboard after the browser engine's own copy. That copy
        carries the theme's colors and names images by local file, so
        it is announced for replacement. A copy the app already built
        carries the marker format and is left alone, and so is one with
        a bitmap, which is a copied picture rather than a selection.
        """
        focus = QApplication.focusWidget()
        if focus is None or not (focus is self or self.isAncestorOf(focus)):
            return
        mime = QApplication.clipboard().mimeData()
        if mime.hasImage() or mime.hasFormat(RICH_COPY_MARKER_FORMAT):
            return
        if mime.hasHtml():
            self.selection_copied.emit(mime.html(), mime.text())

    def copy_code_block(self, index: int) -> None:
        """Put the text of the page's Nth code block on the clipboard."""
        if 0 <= index < len(self._code_blocks):
            QApplication.clipboard().setText(self._code_blocks[index])
            self.code_copied.emit()
