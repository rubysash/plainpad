"""Tests for plainpad.image_sources. The network is always a stand-in."""

from pathlib import Path

import pytest

from plainpad.image_sources import ImageSourceError, ImageSourceReader
from tests.image_samples import GIF, PNG, PNG_DATA_ADDRESS, FakeWeb

WEB_ADDRESS = "https://example.com/cat.gif"


def test_reads_base64_data_address() -> None:
    assert ImageSourceReader().read(PNG_DATA_ADDRESS) == PNG


def test_reads_percent_encoded_data_address() -> None:
    assert ImageSourceReader().read("data:text/plain,GIF89a%01") == (
        b"GIF89a\x01"
    )


def test_reads_file_address(tmp_path: Path) -> None:
    path = tmp_path / "clip image.png"
    path.write_bytes(PNG)
    assert ImageSourceReader().read(path.as_uri()) == PNG


def test_missing_file_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ImageSourceError):
        ImageSourceReader().read((tmp_path / "gone.png").as_uri())


def test_reads_web_address_through_opener() -> None:
    web = FakeWeb({WEB_ADDRESS: GIF})
    assert ImageSourceReader(web).read(WEB_ADDRESS) == GIF
    assert web.requested == [WEB_ADDRESS]


def test_unreachable_web_address_is_an_error() -> None:
    with pytest.raises(ImageSourceError):
        ImageSourceReader(FakeWeb({})).read(WEB_ADDRESS)


def test_oversized_download_is_an_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("plainpad.image_sources.IMAGE_MAX_BYTES", 4)
    with pytest.raises(ImageSourceError):
        ImageSourceReader(FakeWeb({WEB_ADDRESS: GIF})).read(WEB_ADDRESS)


@pytest.mark.parametrize(
    "address", ["cid:image001@01D0", "mailbox:///inbox?part=1.2", "x.png"]
)
def test_unreadable_kinds_of_address_are_errors(address: str) -> None:
    web = FakeWeb({})
    with pytest.raises(ImageSourceError):
        ImageSourceReader(web).read(address)
    assert web.requested == []
