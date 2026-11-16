"""Keyword search over note names and note text."""

from plainpad.crud import NoteStore


def find_matching_notes(store: NoteStore, query: str) -> set[str]:
    """Return the names of notes whose name or text contains ``query``.

    Matching ignores case. A blank query matches nothing; the caller
    decides what an empty search box means. A note whose file cannot be
    read as UTF-8 is matched on its name only.
    """
    wanted = query.strip().casefold()
    if not wanted:
        return set()
    matches = set()
    for name in store.names():
        if wanted in name.casefold():
            matches.add(name)
            continue
        try:
            text = store.read(name)
        except (OSError, UnicodeDecodeError):
            continue
        if wanted in text.casefold():
            matches.add(name)
    return matches
