import io
import pytest
from ebooklib import epub
from app.services.converter import EPUBToPDFConverter, ConversionError


@pytest.fixture
def converter():
    """Create a converter instance for testing."""
    return EPUBToPDFConverter()


def create_minimal_epub() -> bytes:
    """
    Create a minimal valid EPUB file for testing.

    Returns:
        Bytes of a valid EPUB file
    """
    book = epub.EpubBook()
    book.set_identifier("test-epub-001")
    book.set_title("Test EPUB Document")
    book.set_language("en")

    # Create a chapter
    c1 = epub.EpubHtml(
        title="Chapter 1",
        file_name="chap_01.xhtml",
        lang="en",
    )
    c1.content = "<h1>Chapter 1</h1><p>This is the first chapter with some test content.</p>"

    # Create navigation file
    nav = epub.EpubNcx()

    book.add_item(c1)
    book.add_item(nav)
    book.spine = [c1]
    book.toc = (c1,)

    # Generate EPUB bytes
    epub_buffer = io.BytesIO()
    epub.write_epub(epub_buffer, book, {})
    epub_buffer.seek(0)
    return epub_buffer.getvalue()


class TestEPUBToPDFConverter:
    """Test suite for EPUBToPDFConverter."""

    def test_convert_valid_epub(self, converter):
        """Test conversion of a valid EPUB file."""
        epub_content = create_minimal_epub()
        pdf_content = converter.convert(epub_content)

        # Verify PDF was generated
        assert isinstance(pdf_content, bytes)
        assert len(pdf_content) > 0
        # PDF files start with %PDF
        assert pdf_content.startswith(b"%PDF")

    def test_convert_invalid_epub(self, converter):
        """Test conversion with invalid EPUB content."""
        invalid_content = b"This is not a valid EPUB file"

        with pytest.raises(ConversionError):
            converter.convert(invalid_content)

    def test_convert_empty_epub(self, converter):
        """Test conversion with empty content."""
        with pytest.raises(ConversionError):
            converter.convert(b"")

    def test_parse_html_content(self, converter):
        """Test HTML content parsing."""
        html = "<h1>Heading</h1><p>Paragraph with <b>bold</b> text</p>"
        elements = converter._parse_html_content(html)

        # Should have at least some elements
        assert len(elements) > 0

    def test_html_to_text_conversion(self, converter):
        """Test HTML to text conversion."""
        html = """
        <p>First paragraph</p>
        <h2>A Heading</h2>
        <p>Second paragraph</p>
        """
        text = converter._html_to_text(html)

        # Check that content is preserved
        assert "First paragraph" in text
        assert "Second paragraph" in text
        assert "Heading" in text

    def test_html_to_text_with_special_entities(self, converter):
        """Test HTML to text with HTML entities."""
        html = "<p>Text with &lt;angle&gt; brackets and &amp; ampersand</p>"
        text = converter._html_to_text(html)

        assert "angle" in text
        assert "brackets" in text
        assert "ampersand" in text

    def test_is_heading_detection(self, converter):
        """Test heading detection."""
        assert converter._is_heading("Chapter 1")
        assert converter._is_heading("Introduction")
        assert not converter._is_heading(
            "This is a very long text that definitely does not look like a heading at all"
        )
        assert not converter._is_heading("lowercase heading")

    def test_escape_text(self, converter):
        """Test text escaping for reportlab."""
        text = "Text with <special> & characters"
        escaped = converter._escape_text(text)

        assert "&lt;" in escaped
        assert "&gt;" in escaped
        assert "&amp;" in escaped

    def test_converter_handles_unicode(self, converter):
        """Test converter handles unicode content."""
        book = epub.EpubBook()
        book.set_identifier("unicode-test")
        book.set_title("Unicode Test")
        book.set_language("en")

        c1 = epub.EpubHtml(
            title="Unicode Chapter",
            file_name="chap_01.xhtml",
            lang="en",
        )
        c1.content = "<h1>Unicode Test: café, naïve, 日本語, 🎉</h1><p>Special characters test.</p>"

        nav = epub.EpubNcx()

        book.add_item(c1)
        book.add_item(nav)
        book.spine = [c1]
        book.toc = (c1,)

        epub_buffer = io.BytesIO()
        epub.write_epub(epub_buffer, book, {})
        epub_buffer.seek(0)

        # Should not raise an exception
        pdf_content = converter.convert(epub_buffer.getvalue())
        assert isinstance(pdf_content, bytes)
        assert len(pdf_content) > 0

    def test_converter_with_multiple_chapters(self, converter):
        """Test converter with multiple chapters."""
        book = epub.EpubBook()
        book.set_identifier("multi-chapter")
        book.set_title("Multi-Chapter Book")
        book.set_language("en")

        chapters = []
        for i in range(1, 4):
            c = epub.EpubHtml(
                title=f"Chapter {i}",
                file_name=f"chap_{i:02d}.xhtml",
                lang="en",
            )
            c.content = f"<h1>Chapter {i}</h1><p>Content for chapter {i}.</p>"
            book.add_item(c)
            chapters.append(c)

        nav = epub.EpubNcx()

        book.add_item(nav)
        book.spine = chapters
        book.toc = tuple(chapters)

        epub_buffer = io.BytesIO()
        epub.write_epub(epub_buffer, book, {})
        epub_buffer.seek(0)

        pdf_content = converter.convert(epub_buffer.getvalue())
        assert isinstance(pdf_content, bytes)
        assert len(pdf_content) > 0
        assert pdf_content.startswith(b"%PDF")

    def test_converter_with_chinese_japanese_content(self, converter):
        """Test converter with Chinese and Japanese content."""
        book = epub.EpubBook()
        book.set_identifier("cjk-test")
        book.set_title("中文测试 Japanese Test")
        book.set_language("en")

        c1 = epub.EpubHtml(
            title="测试章节 Japanese Chapter",
            file_name="chap_01.xhtml",
            lang="en",
        )
        c1.content = """
        <h1>Chinese Characters - 中文字符</h1>
        <p>这是中文内容测试。这是一个测试段落，包含中文字符和English text mixed together.</p>
        
        <h2>Japanese Characters - 日本語文字</h2>
        <p>これは日本語のテストです。日本語の文字をテストしています。</p>
        
        <h2>Emoji and Symbols - 表情符号和符号</h2>
        <p>Testing emojis: 🎉🚀📚💻🌍 And special symbols: ©™®€£¥</p>
        
        <h2>Mixed Content</h2>
        <p>Mixed: Hello 你好 こんにちは 🌍 Café naïve résumé</p>
        
        <h2>Special Unicode Characters</h2>
        <p>Mathematical symbols: ∑∏∫√∞≈≠≤≥±</p>
        <p>Greek letters: αβγδεζηθικλμνξοπρστυφχψω</p>
        """

        nav = epub.EpubNcx()

        book.add_item(c1)
        book.add_item(nav)
        book.spine = [c1]
        book.toc = (c1,)

        epub_buffer = io.BytesIO()
        epub.write_epub(epub_buffer, book, {})
        epub_buffer.seek(0)

        # Should not raise an exception with Unicode content
        pdf_content = converter.convert(epub_buffer.getvalue())
        assert isinstance(pdf_content, bytes)
        assert len(pdf_content) > 0
        assert pdf_content.startswith(b"%PDF")
