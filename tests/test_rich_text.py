"""Tests for plainpad.rich_import and plainpad.rich_export.

The HTML samples follow what Google Docs and Word put on the clipboard.
The network is always a stand-in.
"""

from pathlib import Path

import pytest

from plainpad.image_sources import ImageSourceReader
from plainpad.images import ImageStore
from plainpad.render import MarkdownRenderer
from plainpad.rich_export import RichTextExporter
from plainpad.rich_import import RichTextImporter, sole_image_address
from tests.image_samples import GIF, PNG, PNG_DATA_ADDRESS, FakeWeb

DOCS_IMAGE = "https://lh7-rt.googleusercontent.com/docsz/abc?key=k"
NORMAL = "font-size:11pt;font-weight:400;font-style:normal;"
BOLD = "font-size:11pt;font-weight:700;font-style:normal;"
ITALIC = "font-size:11pt;font-weight:400;font-style:italic;"
DOCS_HTML = (
    '<meta charset="utf-8">'
    '<b style="font-weight:normal;" id="docs-internal-guid-1">'
    f'<h1 dir="ltr"><span style="{BOLD}">My Title</span></h1>'
    f'<p dir="ltr"><span style="{NORMAL}">Plain </span>'
    f'<span style="{BOLD}">bold</span><span style="{NORMAL}"> and </span>'
    f'<span style="{ITALIC}">italic</span></p>'
    f'<p dir="ltr"><span style="{NORMAL}">'
    f'<img src="{DOCS_IMAGE}" width="624" height="351" /></span></p>'
    f'<ul><li dir="ltr"><p role="presentation"><span style="{NORMAL}">One'
    "</span></p></li></ul><br />"
    f'<table><tbody><tr><td><p><span style="{NORMAL}">A</span></p></td>'
    f'<td><p><span style="{NORMAL}">B</span></p></td></tr>'
    "<tr><td><p>1</p></td><td><p>2</p></td></tr></tbody></table></b>"
)
WORD_HTML = """<html xmlns:o="urn:schemas-microsoft-com:office:office">
<head><style><!-- p.MsoNormal {margin:0in;} --></style></head><body>
<!--StartFragment-->
<p class=MsoNormal>Some <b>bold</b> text.<o:p></o:p></p>
<p class=MsoNormal><!--[if gte vml 1]><v:shape><v:imagedata
src="file:///C:/hidden/in/comment.png"/></v:shape><![endif]--><![if !vml]>
<img width=624 height=351 src="IMAGE_ADDRESS"><![endif]><o:p></o:p></p>
<!--EndFragment-->
</body></html>"""


@pytest.fixture
def images(tmp_path: Path) -> ImageStore:
    """An empty ImageStore."""
    return ImageStore(tmp_path / "images", tmp_path / "trash" / "images")


def importer(images: ImageStore, pages: dict[str, bytes]) -> RichTextImporter:
    """A RichTextImporter whose web serves only ``pages``."""
    return RichTextImporter(images, ImageSourceReader(FakeWeb(pages)))


def test_google_docs_copy_becomes_markdown(images: ImageStore) -> None:
    imported = importer(images, {DOCS_IMAGE: GIF}).markdown_from(DOCS_HTML)
    name = images.names()[0]
    assert imported.images_missed == 0
    assert images.read(name) == GIF
    assert imported.markdown == (
        "# My Title\n\n"
        "Plain **bold** and *italic*\n\n"
        f"![](../images/{name})\n\n"
        "- One\n\n"
        "| A | B |\n| --- | --- |\n| 1 | 2 |"
    )


def test_word_copy_reads_image_from_temp_file(
    images: ImageStore, tmp_path: Path
) -> None:
    clip = tmp_path / "clip_image002.png"
    clip.write_bytes(PNG)
    html = WORD_HTML.replace("IMAGE_ADDRESS", clip.as_uri())
    imported = importer(images, {}).markdown_from(html)
    name = images.names()[0]
    assert imported.markdown == (
        f"Some **bold** text.\n\n![](../images/{name})"
    )
    assert imported.images_missed == 0


def test_unfetchable_image_keeps_its_address(images: ImageStore) -> None:
    imported = importer(images, {}).markdown_from(
        f'<p>Hi</p><img src="{DOCS_IMAGE}"><img src="cid:part1">'
    )
    assert imported.images_missed == 2
    assert f"![]({DOCS_IMAGE})" in imported.markdown
    assert images.names() == []


def test_fetched_file_that_is_no_image_counts_as_missed(
    images: ImageStore,
) -> None:
    pages = {DOCS_IMAGE: b"<html>Sign in</html>"}
    imported = importer(images, pages).markdown_from(
        f'<img src="{DOCS_IMAGE}">'
    )
    assert imported.images_missed == 1


def test_repeated_image_is_fetched_once(images: ImageStore) -> None:
    web = FakeWeb({DOCS_IMAGE: PNG})
    both = f'<img src="{DOCS_IMAGE}"><p>x</p><img src="{DOCS_IMAGE}">'
    RichTextImporter(images, ImageSourceReader(web)).markdown_from(both)
    assert web.requested == [DOCS_IMAGE]


def test_downloads_stop_when_the_time_limit_runs_out(
    images: ImageStore,
) -> None:
    # Each look at the clock is an hour later than the last.
    hours = iter(range(0, 100 * 3600, 3600))
    web = FakeWeb({DOCS_IMAGE: PNG})
    slow = RichTextImporter(
        images, ImageSourceReader(web), clock=lambda: next(hours)
    )
    imported = slow.markdown_from(f'<img src="{DOCS_IMAGE}">')
    assert imported.images_missed == 1
    assert web.requested == []


def test_sole_image_address() -> None:
    assert sole_image_address(f'<img src="{DOCS_IMAGE}">') == DOCS_IMAGE
    assert sole_image_address(f'<p>Look <img src="{DOCS_IMAGE}"></p>') is None
    assert sole_image_address("<p>No picture</p>") is None


def exporter(images: ImageStore) -> RichTextExporter:
    """A RichTextExporter over the store."""
    return RichTextExporter(MarkdownRenderer(), images)


def test_note_html_embeds_stored_images(images: ImageStore) -> None:
    name = images.add(PNG)
    html = exporter(images).note_html(f"# T\n\n**b** ![](../images/{name})")
    assert "<h1>T</h1>" in html
    assert "<strong>b</strong>" in html
    assert f'src="{PNG_DATA_ADDRESS}"' in html


def test_note_html_leaves_web_and_missing_images_alone(
    images: ImageStore,
) -> None:
    html = exporter(images).note_html(
        f"![]({DOCS_IMAGE}) ![](../images/0000000000000000.png)"
    )
    assert f'src="{DOCS_IMAGE}"' in html
    assert 'src="../images/0000000000000000.png"' in html


def test_selection_html_drops_theme_and_copy_links(
    images: ImageStore,
) -> None:
    name = images.add(PNG)
    copied = (
        '<meta charset="utf-8"><h1 style="color: rgb(51, 255, 51);">T</h1>'
        '<div class="code-block"><a class="copy-code" '
        'href="plainpad-copy:0">copy</a><pre><code>c</code></pre></div>'
        f'<img src="{images.path_of(name).as_uri()}">'
        '<a href="https://example.com/">kept</a>'
    )
    html = exporter(images).selection_html(copied)
    assert html == (
        "<h1>T</h1><div><pre><code>c</code></pre></div>"
        f'<img src="{PNG_DATA_ADDRESS}"/>'
        '<a href="https://example.com/">kept</a>'
    )


def test_selection_html_ignores_files_outside_the_image_folder(
    images: ImageStore, tmp_path: Path
) -> None:
    outside = tmp_path / "secret.png"
    outside.write_bytes(PNG)
    html = exporter(images).selection_html(f'<img src="{outside.as_uri()}">')
    assert "data:" not in html
