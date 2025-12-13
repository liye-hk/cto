import io
from typing import Optional

import pytest
from ebooklib import epub

from app.services.converter import ConversionError, EPUBToPDFConverter


@pytest.fixture
def converter():
    return EPUBToPDFConverter()


_BOLD_FONT_MARKERS = (
    b"Helvetica-Bold",
    b"DejaVuSans-Bold",
    b"WenQuanYi-Bold",
)


def _assert_pdf_uses_bold_font(pdf_content: bytes) -> None:
    assert any(marker in pdf_content for marker in _BOLD_FONT_MARKERS), (
        "Expected PDF to embed a bold font (used when encountering bold text), but none of the known bold font "
        "markers were found."
    )


def _build_epub_with_html(html: str, css: Optional[str] = None) -> bytes:
    book = epub.EpubBook()
    book.set_identifier("bold_test")
    # Keep empty to avoid the converter inserting a title paragraph that could introduce bold fonts.
    book.set_title("")

    chapter = epub.EpubHtml(title="Chapter", file_name="chapter.xhtml", lang="en")
    chapter.content = html
    book.add_item(chapter)

    if css:
        style_item = epub.EpubItem(
            uid="style",
            file_name="styles.css",
            media_type="text/css",
            content=css.encode("utf-8"),
        )
        book.add_item(style_item)

    book.spine = [("chapter.xhtml", True)]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    epub_buffer = io.BytesIO()
    epub.write_epub(epub_buffer, book, {})
    return epub_buffer.getvalue()


class TestEPUBToPDFConverter:
    def test_convert_valid_epub(self, converter):
        """Test conversion of a valid EPUB file."""
        # Create a minimal EPUB
        book = epub.EpubBook()
        book.set_identifier("test_book")
        book.set_title("Test Book")

        # Create a chapter
        chapter = epub.EpubHtml(title="Chapter 1", file_name="chapter1.xhtml", lang="en")
        chapter.content = "<h1>Chapter 1</h1><p>This is the first chapter content.</p>"
        book.add_item(chapter)

        # Create spine with proper tuple format
        book.spine = [("chapter1.xhtml", True)]

        # Create NCX navigation
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # Write EPUB to bytes
        epub_buffer = io.BytesIO()
        epub.write_epub(epub_buffer, book, {})
        epub_content = epub_buffer.getvalue()

        # Convert to PDF
        pdf_content = converter.convert(epub_content)

        # Check that PDF is generated
        assert pdf_content is not None
        assert len(pdf_content) > 0
        # Basic PDF header check
        assert pdf_content.startswith(b"%PDF")

    def test_convert_invalid_epub(self, converter):
        """Test conversion of invalid EPUB content."""
        with pytest.raises(ConversionError):
            converter.convert(b"invalid epub content")

    def test_convert_empty_epub(self, converter):
        """Test conversion of empty EPUB."""
        with pytest.raises(ConversionError):
            converter.convert(b"")

    def test_escape_text(self, converter):
        """Ensure escaping preserves formatting tags while sanitizing others."""
        text = (
            "Text with <special> & characters, "
            "<b>bold</b> and <font color=\"#ff0000\">red</font> text."
        )
        escaped = converter._escape_text(text)

        # Disallowed tags should be escaped
        assert "&lt;special&gt;" in escaped
        assert "&amp;" in escaped

        # Allowed formatting tags should be preserved in the output
        assert "<b>bold</b>" in escaped
        # Font color tags should be converted to span with style for WeasyPrint compatibility
        assert '<span style="color: #ff0000;">red</span>' in escaped

        # Plain text should remain readable
        assert "Text with" in escaped
        assert "characters" in escaped

    def test_converter_handles_unicode(self, converter):
        """Test converter handles Unicode characters properly."""
        # Create EPUB with Unicode content
        book = epub.EpubBook()
        book.set_identifier("unicode_test")
        book.set_title("Unicode Test")

        chapter = epub.EpubHtml(title="Unicode Chapter", file_name="unicode.xhtml", lang="en")
        chapter.content = "<h1>测试章节</h1><p>This contains Chinese characters: 测试</p>"
        book.add_item(chapter)
        book.spine = [("unicode.xhtml", True)]
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        epub_buffer = io.BytesIO()
        epub.write_epub(epub_buffer, book, {})
        epub_content = epub_buffer.getvalue()

        # Should not raise exception
        pdf_content = converter.convert(epub_content)
        assert pdf_content is not None
        assert len(pdf_content) > 0

    def test_converter_with_multiple_chapters(self, converter):
        """Test converter with multiple chapters."""
        book = epub.EpubBook()
        book.set_identifier("multi_chapter")
        book.set_title("Multi Chapter Book")

        # Create multiple chapters
        for i in range(1, 4):
            chapter = epub.EpubHtml(
                title=f"Chapter {i}", file_name=f"chapter{i}.xhtml", lang="en"
            )
            chapter.content = f"<h1>Chapter {i}</h1><p>This is the content of chapter {i}.</p>"
            book.add_item(chapter)

        # Set spine with proper tuples
        spine_items = [f"chapter{i}.xhtml" for i in range(1, 4)]
        book.spine = [(item, True) for item in spine_items]

        # Create NCX navigation
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        epub_buffer = io.BytesIO()
        epub.write_epub(epub_buffer, book, {})
        epub_content = epub_buffer.getvalue()

        pdf_content = converter.convert(epub_content)
        assert pdf_content is not None
        assert len(pdf_content) > 0
        assert pdf_content.startswith(b"%PDF")

    def test_bold_text_from_b_tag_uses_bold_font(self, converter):
        epub_content = _build_epub_with_html('<p>Normal <b>Bold</b> text</p>')
        pdf_content = converter.convert(epub_content)
        _assert_pdf_uses_bold_font(pdf_content)

    def test_bold_text_from_inline_style_font_weight_uses_bold_font(self, converter):
        epub_content = _build_epub_with_html('<p><span style="font-weight: bold">Bold</span> text</p>')
        pdf_content = converter.convert(epub_content)
        _assert_pdf_uses_bold_font(pdf_content)

    def test_bold_text_from_css_class_uses_bold_font(self, converter):
        css = ".x1 { font-weight: 700; }"
        epub_content = _build_epub_with_html(
            '<p><span class="x1">Bold</span> text</p>',
            css=css,
        )
        pdf_content = converter.convert(epub_content)
        _assert_pdf_uses_bold_font(pdf_content)
