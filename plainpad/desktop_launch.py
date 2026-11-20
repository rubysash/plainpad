"""Opening the system file browser or a terminal at a location.

DesktopLauncher builds the right command for the running OS and starts it
without waiting for it. Windows, macOS, and Linux are supported. Windows
also offers Command Prompt and PowerShell directly.
"""

import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from plainpad.config import (
    FILE_BROWSER_LABELS,
    LINUX_TERMINAL_PROGRAMS,
    MACOS_PLATFORM,
    MACOS_TERMINAL_APP,
    OTHER_FILE_BROWSER_LABEL,
    WINDOWS_COMMAND_PROMPT,
    WINDOWS_PLATFORM,
    WINDOWS_POWERSHELL_PROGRAMS,
    WINDOWS_TERMINAL_PROGRAM,
)

# Console programs such as PowerShell need their own window, or they would
# share Plainpad's console or get none. GUI programs ignore the flag. It
# only exists on Windows, and must be 0 elsewhere.
NEW_CONSOLE_FLAG = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)


class LaunchError(OSError):
    """No program could be found to carry out a launch."""


def folder_of(location: Path) -> Path:
    """Return a folder itself, or the folder that holds a file."""
    return location.parent if location.is_file() else location


class DesktopLauncher:
    """Shows files in the file browser and opens terminals.

    ``platform`` and ``find_program`` default to the real OS and
    ``shutil.which``; tests pass their own.
    """

    def __init__(
        self,
        platform: str = sys.platform,
        find_program: Callable[[str], str | None] = shutil.which,
    ) -> None:
        """Remember which OS to build commands for."""
        self._platform = platform
        self._find_program = find_program

    def file_browser_label(self) -> str:
        """Return the menu text naming this OS's file browser."""
        return FILE_BROWSER_LABELS.get(
            self._platform, OTHER_FILE_BROWSER_LABEL
        )

    def offers_windows_shells(self) -> bool:
        """Return True if Command Prompt and PowerShell can be offered."""
        return self._platform == WINDOWS_PLATFORM

    def has_terminal(self) -> bool:
        """Return True if terminal_command can find a terminal."""
        try:
            self.terminal_command(Path())
        except LaunchError:
            return False
        return True

    def file_browser_command(self, target: Path) -> list[str]:
        """Return the command that shows ``target`` in the file browser.

        A file is shown selected in its folder on Windows and macOS. Linux
        has no standard way to select a file, so its folder is opened.
        """
        is_file = target.is_file()
        if self._platform == WINDOWS_PLATFORM:
            if is_file:
                # As separate arguments, so a path with spaces still works.
                return ["explorer", "/select,", str(target)]
            return ["explorer", str(target)]
        if self._platform == MACOS_PLATFORM:
            return ["open", "-R", str(target)] if is_file else (
                ["open", str(target)]
            )
        return ["xdg-open", str(folder_of(target))]

    def terminal_command(self, folder: Path) -> list[str]:
        """Return the command that opens a terminal in ``folder``.

        The command is run from ``folder`` (see start), which is enough
        for most terminals. On Windows this is Windows Terminal. Raises
        LaunchError if no terminal is installed.
        """
        if self._platform == WINDOWS_PLATFORM:
            if self._find_program(WINDOWS_TERMINAL_PROGRAM):
                return [WINDOWS_TERMINAL_PROGRAM, "-d", str(folder)]
            raise LaunchError("Windows Terminal is not installed.")
        if self._platform == MACOS_PLATFORM:
            return ["open", "-a", MACOS_TERMINAL_APP, str(folder)]
        for program in LINUX_TERMINAL_PROGRAMS:
            if self._find_program(program):
                return [program]
        raise LaunchError("No terminal program was found.")

    def powershell_command(self) -> list[str]:
        """Return the command for the newest PowerShell installed."""
        for program in WINDOWS_POWERSHELL_PROGRAMS:
            if self._find_program(program):
                return [program]
        return [WINDOWS_POWERSHELL_PROGRAMS[-1]]

    def show_in_file_browser(self, target: Path) -> None:
        """Open the file browser at a file or folder."""
        self.start(self.file_browser_command(target), folder_of(target))

    def open_terminal(self, location: Path) -> None:
        """Open a terminal in a folder, or in the folder holding a file."""
        folder = folder_of(location)
        self.start(self.terminal_command(folder), folder)

    def open_command_prompt(self, location: Path) -> None:
        """Open Command Prompt in a folder, or the folder holding a file.

        Run from the folder in a new console, so it starts there whether
        Windows shows it in Windows Terminal or the classic console.
        """
        self.start([WINDOWS_COMMAND_PROMPT], folder_of(location))

    def open_powershell(self, location: Path) -> None:
        """Open PowerShell in a folder, or the folder holding a file."""
        self.start(self.powershell_command(), folder_of(location))

    def start(self, command: list[str], folder: Path) -> None:
        """Run a command from ``folder`` without waiting for it to end.

        Raises OSError if the program cannot be started.
        """
        subprocess.Popen(
            command,
            cwd=folder,
            creationflags=NEW_CONSOLE_FLAG,
            # On POSIX, closing Plainpad must not close the terminal.
            start_new_session=True,
        )
