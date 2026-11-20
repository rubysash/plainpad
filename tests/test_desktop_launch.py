"""Tests for plainpad.desktop_launch.

Only the commands are checked; nothing is started. Each OS is simulated
by passing its sys.platform value and a stand-in for shutil.which.
"""

from pathlib import Path

import pytest

from plainpad.desktop_launch import DesktopLauncher, LaunchError


def installed(*programs: str):
    """Return a shutil.which stand-in that finds only ``programs``."""
    return lambda program: program if program in programs else None


@pytest.fixture
def note(tmp_path: Path) -> Path:
    """A note file inside a folder whose name has a space."""
    folder = tmp_path / "my notes"
    folder.mkdir()
    path = folder / "Chili.md"
    path.write_text("", encoding="utf-8")
    return path


def test_windows_selects_a_file_in_explorer(note: Path) -> None:
    launcher = DesktopLauncher("win32")
    assert launcher.file_browser_command(note) == [
        "explorer", "/select,", str(note)
    ]
    assert launcher.file_browser_command(note.parent) == [
        "explorer", str(note.parent)
    ]
    assert launcher.file_browser_label() == "Show in &Explorer"


def test_windows_terminal_only_when_installed(note: Path) -> None:
    folder = note.parent
    with_wt = DesktopLauncher("win32", installed("wt"))
    assert with_wt.has_terminal()
    assert with_wt.terminal_command(folder) == ["wt", "-d", str(folder)]
    without = DesktopLauncher("win32", installed())
    assert not without.has_terminal()
    with pytest.raises(LaunchError):
        without.terminal_command(folder)


def test_windows_prefers_powershell_7(note: Path) -> None:
    both = DesktopLauncher("win32", installed("pwsh", "powershell.exe"))
    assert both.powershell_command() == ["pwsh"]
    builtin = DesktopLauncher("win32", installed())
    assert builtin.powershell_command() == ["powershell.exe"]


def test_only_windows_offers_cmd_and_powershell() -> None:
    assert DesktopLauncher("win32").offers_windows_shells()
    assert not DesktopLauncher("darwin").offers_windows_shells()
    assert not DesktopLauncher("linux").offers_windows_shells()


def test_command_prompt_starts_in_the_folder_holding_a_file(
    note: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = DesktopLauncher("win32", installed())
    started: list[tuple[list[str], Path]] = []
    monkeypatch.setattr(
        launcher, "start", lambda command, folder: started.append(
            (command, folder)
        )
    )
    launcher.open_command_prompt(note)
    launcher.open_powershell(note.parent)
    assert started == [
        (["cmd.exe"], note.parent),
        (["powershell.exe"], note.parent),
    ]


def test_macos_reveals_in_finder_and_opens_terminal(note: Path) -> None:
    launcher = DesktopLauncher("darwin")
    assert launcher.file_browser_command(note) == ["open", "-R", str(note)]
    assert launcher.terminal_command(note.parent) == [
        "open", "-a", "Terminal", str(note.parent)
    ]
    assert launcher.file_browser_label() == "Show in &Finder"


def test_linux_opens_the_folder_and_first_terminal_found(note: Path) -> None:
    launcher = DesktopLauncher("linux", installed("konsole", "xterm"))
    assert launcher.file_browser_command(note) == [
        "xdg-open", str(note.parent)
    ]
    assert launcher.terminal_command(note.parent) == ["konsole"]
    assert launcher.file_browser_label() == "Open in File &Manager"


def test_linux_without_a_terminal_raises(note: Path) -> None:
    launcher = DesktopLauncher("linux", installed())
    assert not launcher.has_terminal()
    with pytest.raises(LaunchError):
        launcher.terminal_command(note.parent)


def test_terminal_starts_in_the_folder_holding_a_file(
    note: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = DesktopLauncher("linux", installed("xterm"))
    started: list[tuple[list[str], Path]] = []
    monkeypatch.setattr(
        launcher, "start", lambda command, folder: started.append(
            (command, folder)
        )
    )
    launcher.open_terminal(note)
    assert started == [(["xterm"], note.parent)]
