"""The View tab: the open note rendered as a styled HTML page."""

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QColor, QDesktopServices
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QWidget

from plainpad.config import EXTERNAL_LINK_SCHEMES, PREVIEW_BACKGROUND_COLOR
from plainpad.render import MarkdownRenderer


class ExternalLinkPage(QWebEnginePage):
    """A web page that sends clicked links to the system browser.

    Without this, clicking a link in a note would navigate the View tab
    away from the note with no way back.
    """

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
        if url.scheme() in EXTERNAL_LINK_SCHEMES:
            QDesktopServices.openUrl(url)
        return False


class PreviewTab(QWebEngineView):
    """Read-only rendered view of a note."""

    def __init__(
        self, renderer: MarkdownRenderer, parent: QWidget | None = None
    ) -> None:
        """Install an ExternalLinkPage with JavaScript turned off.

        Notes may contain raw HTML, so scripts must never run. The page
        background is set to black so there is no white flash on load.
        """
        super().__init__(parent)
        self._renderer = renderer
        page = ExternalLinkPage(self)
        page.settings().setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled, False
        )
        page.setBackgroundColor(QColor(PREVIEW_BACKGROUND_COLOR))
        self.setPage(page)

    def show_markdown(self, markdown_text: str, css: str) -> None:
        """Render markdown with the given CSS and display the page."""
        self.setHtml(self._renderer.page_html(markdown_text, css))

    def show_nothing(self) -> None:
        """Display an empty page, for when no note is open."""
        self.setHtml("")
