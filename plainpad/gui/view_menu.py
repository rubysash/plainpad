"""The View tab's right-click menu.

The browser engine's own menu is a browser's (Back, Reload, View page
source), which does not belong in a notepad. This one offers Copy and
Select all, plus the link or picture under the pointer.
"""

from collections.abc import Callable

from PyQt6.QtGui import QAction
from PyQt6.QtWebEngineCore import QWebEngineContextMenuRequest, QWebEnginePage
from PyQt6.QtWidgets import QMenu

WebAction = QWebEnginePage.WebAction
IMAGE = QWebEngineContextMenuRequest.MediaType.MediaTypeImage


def build_view_menu(
    page_action: Callable[[WebAction], QAction],
    request: QWebEngineContextMenuRequest | None,
    copy_link: Callable[[str], None],
    copy_image: Callable[[str], None],
) -> QMenu:
    """Return the menu for a right-click described by ``request``.

    ``page_action`` is the view's own, for the engine's Copy and Select
    all. A link's address is copied as plain text by ``copy_link``,
    because the engine's copy adds HTML. A local picture is copied by
    ``copy_image``, because the engine's copy puts HTML beside the
    bitmap and Gmail in Firefox then drops the picture; a picture on the
    web keeps the engine's copy. The menu has no parent, so the caller
    must keep it alive while it is shown.
    """
    menu = QMenu()
    menu.addActions(
        [page_action(WebAction.Copy), page_action(WebAction.SelectAll)]
    )
    if request is not None and request.linkUrl().isValid():
        address = request.linkUrl().toString()
        label = page_action(WebAction.CopyLinkToClipboard).text()
        menu.addSeparator()
        menu.addAction(label).triggered.connect(lambda: copy_link(address))
    if request is not None and request.mediaType() == IMAGE:
        engine_copy = page_action(WebAction.CopyImageToClipboard)
        menu.addSeparator()
        if request.mediaUrl().isLocalFile():
            address = request.mediaUrl().toString()
            menu.addAction(engine_copy.text()).triggered.connect(
                lambda: copy_image(address)
            )
        else:
            menu.addAction(engine_copy)
    return menu
