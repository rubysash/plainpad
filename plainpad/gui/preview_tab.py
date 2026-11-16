"""The View tab: the open note rendered as a styled HTML page."""

from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication, QWidget

from plainpad.config import (
    COPY_LINK_SCHEME,
    EXTERNAL_LINK_SCHEMES,
    PREVIEW_BACKGROUND_COLOR,
)
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

    def __init__(
        self, renderer: MarkdownRenderer, parent: QWidget | None = None
    ) -> None:
        """Install an ExternalLinkPage with JavaScript turned off.

        Notes may contain raw HTML, so scripts must never run. The page
        background is set to black so there is no white flash on load.
        """
        super().__init__(parent)
        self._renderer = renderer
        self._code_blocks: list[str] = []
        page = ExternalLinkPage(self)
        page.settings().setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled, False
        )
        page.setBackgroundColor(QColor(PREVIEW_BACKGROUND_COLOR))
        page.copy_requested.connect(self.copy_code_block)
        self.setPage(page)

    def show_markdown(self, markdown_text: str, css: str) -> None:
        """Render markdown with the given CSS and display the page."""
        rendered = self._renderer.render_page(markdown_text, css)
        self._code_blocks = rendered.code_blocks
        self.setHtml(rendered.html)

    def show_nothing(self) -> None:
        """Display an empty page, for when no note is open."""
        self._code_blocks = []
        self.setHtml("")

    def copy_code_block(self, index: int) -> None:
        """Put the text of the page's Nth code block on the clipboard."""
        if 0 <= index < len(self._code_blocks):
            QApplication.clipboard().setText(self._code_blocks[index])
            self.code_copied.emit()
