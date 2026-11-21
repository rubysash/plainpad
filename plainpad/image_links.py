"""The link a note uses to show a stored image, and how to find them.

A note refers to an image by a relative path from the notes folder to the
images folder. That path is the only tie between a note and a picture.
"""

import re

from plainpad.config import IMAGE_LINK_PREFIX, IMAGE_LINK_TEMPLATE

# A stored image's file name: hex digits of its hash, then an extension.
IMAGE_NAME_PATTERN = r"[0-9a-fA-F]+\.[A-Za-z]+"
_LINK = re.compile(
    re.escape(IMAGE_LINK_PREFIX) + f"({IMAGE_NAME_PATTERN})"
)
_WHOLE_LINK = re.compile(
    re.escape(IMAGE_LINK_PREFIX) + f"({IMAGE_NAME_PATTERN})$"
)


def image_link_for(name: str) -> str:
    """Return the markdown that shows the stored image ``name``."""
    return IMAGE_LINK_TEMPLATE.format(prefix=IMAGE_LINK_PREFIX, name=name)


def image_address_for(name: str) -> str:
    """Return the relative address of the stored image ``name``."""
    return f"{IMAGE_LINK_PREFIX}{name}"


def image_names_in(text: str) -> set[str]:
    """Return the name of every stored image a note's text links to.

    Any mention of the images folder counts, whether in markdown or in
    raw HTML, so an image is never judged unused by mistake.
    """
    return set(_LINK.findall(text))


def stored_image_name(address: str) -> str | None:
    """Return the image name if ``address`` is a link to a stored image.

    Only an address that is exactly the relative link counts. A web
    address that happens to end the same way does not.
    """
    match = _WHOLE_LINK.match(address)
    return match.group(1) if match else None
