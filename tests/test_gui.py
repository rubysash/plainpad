"""GUI tests for MainWindow and its widgets, using pytest-qt.

Each test gets its own data folder and its own QSettings file under
tmp_path, so the user's notes and window state are never touched. Dialogs
are replaced with stubs that answer Yes, and autosave runs fast.
"""

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from PyQt6 import sip
from PyQt6.QtCore import QPoint, QSettings, Qt, QUrl
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from plainpad.config import THEMES_DIR
from plainpad.desktop_launch import DesktopLauncher
from plainpad.gui import editor_tab, main_window, tree_commands
from plainpad.gui.main_window import MainWindow
from plainpad.library import Library
from plainpad.theme_store import ThemeStore

FAST_AUTOSAVE_MS = 50


def answer_yes(*_args: object) -> bool:
    """Stand-in for dialogs.confirm that always answers Yes."""
    return True


class RecordingLauncher(DesktopLauncher):
    """A Windows DesktopLauncher that records commands instead of running
    them, so tests open no windows."""

    def __init__(self) -> None:
        """Pretend Windows Terminal is installed."""
        super().__init__("win32", lambda program: program)
        self.started: list[tuple[list[str], Path]] = []

    def start(self, command: list[str], folder: Path) -> None:
        """Record the command and the folder it would run from."""
        self.started.append((command, folder))


@pytest.fixture
def window(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[MainWindow]:
    """A shown MainWindow over an empty data folder.

    The window is destroyed at once after the test rather than left to
    pytest-qt, because WebEngine crashes at exit if a rendered page
    outlives the application.
    """
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(tmp_path / "settings"),
    )
    monkeypatch.setattr(editor_tab, "AUTOSAVE_DELAY_MS", FAST_AUTOSAVE_MS)
    monkeypatch.setattr(main_window, "confirm", answer_yes)
    monkeypatch.setattr(tree_commands, "confirm", answer_yes)
    library = Library(tmp_path / "data")
    win = MainWindow(library, ThemeStore(THEMES_DIR), RecordingLauncher())
    win.show()
    yield win
    win.close()
    sip.delete(win)


@pytest.fixture
def library(window: MainWindow) -> Library:
    """The Library behind the window."""
    return window._library


def new_note(window: MainWindow, qtbot: QtBot, text: str = "") -> str:
    """Create a note through the window, type ``text``, return its name."""
    window._commands.create_note()
    editor = window._tabs.editor
    if text:
        qtbot.keyClicks(editor, text)
    return editor.current_note_name()


def make_save_flaky(
    library: Library, monkeypatch: pytest.MonkeyPatch
) -> dict[str, bool]:
    """Make note saves fail while the returned switch says so."""
    switch = {"fail": True}
    real_save: Callable[[str, str], None] = library.save_note

    def flaky_save(name: str, text: str) -> None:
        if switch["fail"]:
            raise OSError("disk full")
        real_save(name, text)

    monkeypatch.setattr(library, "save_note", flaky_save)
    return switch


def status(window: MainWindow) -> str:
    """Return the status bar text."""
    return window.statusBar().currentMessage()


def test_editor_is_disabled_until_a_note_is_open(
    window: MainWindow, qtbot: QtBot
) -> None:
    editor = window._tabs.editor
    assert not editor.isEnabled()
    new_note(window, qtbot)
    assert editor.isEnabled()


def test_typing_autosaves_after_idle(
    window: MainWindow, library: Library, qtbot: QtBot
) -> None:
    name = new_note(window, qtbot, "hello")
    qtbot.waitUntil(lambda: library.read_note(name) == "hello")
    assert status(window).startswith("Saved")


def test_switching_notes_saves_and_keeps_undo(
    window: MainWindow, library: Library, qtbot: QtBot
) -> None:
    first = new_note(window, qtbot, "first")
    new_note(window, qtbot, "second")
    assert library.read_note(first) == "first"
    window.open_note(first)
    editor = window._tabs.editor
    assert editor.toPlainText() == "first"
    assert editor.document().isUndoAvailable()
    editor.undo()
    assert editor.toPlainText() != "first"


def test_search_hides_non_matches_then_restores(
    window: MainWindow, library: Library
) -> None:
    library.save_note("Chili", "beans and cumin")
    library.save_note("Soup", "leeks")
    window.refresh_tree()
    tree = window._sidebar.tree
    window.run_search("CUMIN")
    assert not tree.find_item("note", "Chili").isHidden()
    assert tree.find_item("note", "Soup").isHidden()
    assert tree.topLevelItem(0).isExpanded()
    window.run_search("")
    assert not tree.find_item("note", "Soup").isHidden()
    assert not tree.topLevelItem(0).isExpanded()


def test_bad_rename_is_rejected(
    window: MainWindow, library: Library
) -> None:
    library.save_note("Chili", "")
    window.refresh_tree()
    window._commands.apply_note_rename("Chili", "CON")
    assert library.note_exists("Chili")
    assert "Rename failed" in status(window)
    assert window._sidebar.tree.find_item("note", "Chili") is not None


def test_renaming_open_note_keeps_it_open(
    window: MainWindow, library: Library, qtbot: QtBot
) -> None:
    name = new_note(window, qtbot, "beans")
    window._commands.apply_note_rename(name, "Chili")
    assert window._tabs.editor.current_note_name() == "Chili"
    assert library.read_note("Chili") == "beans"
    assert window.windowTitle().startswith("Chili")


def test_delete_moves_open_note_to_trash(
    window: MainWindow, library: Library, qtbot: QtBot, tmp_path: Path
) -> None:
    name = new_note(window, qtbot, "bye")
    window._commands.delete_selected()
    assert not library.note_exists(name)
    trashed = tmp_path / "data" / "trash" / f"{name}.md"
    assert trashed.read_text(encoding="utf-8") == "bye"
    assert not window._tabs.editor.isEnabled()


def test_failed_save_is_retried_by_save_now(
    window: MainWindow,
    library: Library,
    qtbot: QtBot,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    name = new_note(window, qtbot)
    switch = make_save_flaky(library, monkeypatch)
    qtbot.keyClicks(window._tabs.editor, "keep")
    window._tabs.flush_pending_saves()
    assert "Save failed" in status(window)
    assert window._tabs.has_unsaved_changes()
    switch["fail"] = False
    window._actions.save_now.trigger()
    assert library.read_note(name) == "keep"
    assert not window._tabs.has_unsaved_changes()


def test_failed_save_survives_switching_notes(
    window: MainWindow,
    library: Library,
    qtbot: QtBot,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = new_note(window, qtbot)
    switch = make_save_flaky(library, monkeypatch)
    qtbot.keyClicks(window._tabs.editor, "first text")
    new_note(window, qtbot)
    switch["fail"] = False
    window._actions.save_now.trigger()
    assert library.read_note(first) == "first text"


def test_close_asks_before_losing_unsaved_text(
    window: MainWindow,
    library: Library,
    qtbot: QtBot,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    new_note(window, qtbot)
    make_save_flaky(library, monkeypatch)
    qtbot.keyClicks(window._tabs.editor, "unsaved")
    monkeypatch.setattr(main_window, "confirm", lambda *_args: False)
    window.close()
    assert window.isVisible()
    monkeypatch.setattr(main_window, "confirm", answer_yes)
    window.close()
    assert not window.isVisible()


def test_arrow_keys_load_note_after_pause_and_keep_tab(
    window: MainWindow, library: Library, qtbot: QtBot
) -> None:
    library.save_note("Alpha", "# alpha")
    library.save_note("Beta", "# beta")
    window.refresh_tree()
    tree, tabs = window._sidebar.tree, window._tabs
    tree.select_note("Alpha")
    window.open_note("Alpha")
    tabs.show_view_tab()
    tree.setFocus()
    qtbot.keyClick(tree, Qt.Key.Key_Down)
    assert tabs.editor.current_note_name() == "Alpha"
    qtbot.waitUntil(lambda: tabs.editor.current_note_name() == "Beta")
    assert tabs.currentWidget() is tabs.preview


def test_copy_link_puts_code_block_on_clipboard(
    window: MainWindow, library: Library
) -> None:
    library.save_note("Commands", "```\nqm list\n```\n\n```\npct list\n```")
    window.refresh_tree()
    window.open_note("Commands")
    window._tabs.show_view_tab()
    page = window._tabs.preview.page()
    link_clicked = QWebEnginePage.NavigationType.NavigationTypeLinkClicked
    followed = page.acceptNavigationRequest(
        QUrl("plainpad-copy:1"), link_clicked, True
    )
    assert not followed
    assert QApplication.clipboard().text() == "pct list"
    assert status(window) == "Copied code block"


def test_first_run_uses_crt_theme(window: MainWindow) -> None:
    themes = ThemeStore(THEMES_DIR)
    assert window._actions.themes["crt"].isChecked()
    assert QApplication.instance().styleSheet() == themes.qss("crt")


def test_switching_theme_restyles_app_and_view(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    themes = ThemeStore(THEMES_DIR)
    rendered: list[str] = []
    monkeypatch.setattr(
        window._tabs.preview,
        "show_markdown",
        lambda _text, css: rendered.append(css),
    )
    window._commands.create_note()
    window._tabs.show_view_tab()
    window._actions.themes["dark"].trigger()
    assert QApplication.instance().styleSheet() == themes.qss("dark")
    assert rendered[-1] == themes.preview_css("dark")
    assert window._actions.themes["dark"].isChecked()
    assert not window._actions.themes["crt"].isChecked()
    assert QSettings().value("appearance/theme") == "dark"


def test_tabs_are_edit_and_view_only(window: MainWindow) -> None:
    tabs = window._tabs
    assert [tabs.tabText(i) for i in range(tabs.count())] == ["Edit", "View"]


def right_click(window: MainWindow, note_name: str | None) -> None:
    """Open the tree menu on a note's row, or on a category row."""
    tree = window._sidebar.tree
    item = tree.find_item("note", note_name) if note_name else (
        tree.topLevelItem(0)
    )
    tree.scrollToItem(item)
    window._locations.show_menu(tree.visualItemRect(item).center())
    window._locations._menu.close()


def test_right_click_note_shows_it_in_explorer(
    window: MainWindow, library: Library
) -> None:
    library.save_note("Chili", "")
    window.refresh_tree()
    window._sidebar.tree.select_note("Chili")
    right_click(window, "Chili")
    window._actions.show_in_file_browser.trigger()
    command, folder = window._locations._launcher.started[-1]
    assert command == ["explorer", "/select,", str(library.note_path("Chili"))]
    assert folder == library.notes_folder()


def test_right_click_category_opens_terminal_in_notes_folder(
    window: MainWindow, library: Library
) -> None:
    right_click(window, None)
    window._actions.open_terminal_here.trigger()
    folder = str(library.notes_folder())
    command, _ = window._locations._launcher.started[-1]
    assert command == ["wt", "-d", folder]


def test_right_click_offers_cmd_and_powershell_on_windows(
    window: MainWindow, library: Library
) -> None:
    actions = window._actions
    menu_items = window._locations._menu.actions()
    for action in (
        actions.show_in_file_browser,
        actions.open_terminal_here,
        actions.open_command_prompt_here,
        actions.open_powershell_here,
    ):
        assert action in menu_items
    right_click(window, None)
    actions.open_command_prompt_here.trigger()
    actions.open_powershell_here.trigger()
    started = window._locations._launcher.started[-2:]
    folder = library.notes_folder()
    assert started == [(["cmd.exe"], folder), (["pwsh"], folder)]


def real_right_click(window: MainWindow, qtbot: QtBot, at: QPoint) -> None:
    """Right-click the tree as a mouse would, then open its menu there."""
    viewport = window._sidebar.tree.viewport()
    qtbot.mouseClick(viewport, Qt.MouseButton.RightButton, pos=at)
    window._locations.show_menu(at)
    window._locations._menu.close()


def test_right_click_new_note_goes_into_clicked_category(
    window: MainWindow, library: Library, qtbot: QtBot
) -> None:
    menu_items = window._locations._menu.actions()
    assert window._actions.new_note in menu_items
    assert window._actions.new_category in menu_items
    recipes = library.create_category("Recipes")
    window.refresh_tree()
    tree = window._sidebar.tree
    row = tree.find_item("category", recipes.category_id)
    real_right_click(window, qtbot, tree.visualItemRect(row).center())
    window._actions.new_note.trigger()
    listing = next(
        item for item in library.listings()
        if item.category.category_id == recipes.category_id
    )
    assert listing.note_names == [window._tabs.editor.current_note_name()]


def test_right_click_empty_space_puts_new_note_in_uncategorized(
    window: MainWindow, library: Library, qtbot: QtBot
) -> None:
    recipes = library.create_category("Recipes")
    window.refresh_tree()
    tree = window._sidebar.tree
    tree.setCurrentItem(tree.find_item("category", recipes.category_id))
    empty = QPoint(5, tree.viewport().height() - 5)
    assert tree.itemAt(empty) is None
    real_right_click(window, qtbot, empty)
    window._actions.new_note.trigger()
    uncategorized = library.listings()[-1]
    assert uncategorized.note_names == [
        window._tabs.editor.current_note_name()
    ]


def test_launch_failure_is_shown_in_status_bar(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*_args: object) -> None:
        raise FileNotFoundError("wt not found")

    monkeypatch.setattr(window._locations._launcher, "start", fail)
    right_click(window, None)
    window._actions.open_terminal_here.trigger()
    assert "Could not open a terminal" in status(window)
