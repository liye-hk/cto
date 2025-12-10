import io
import pytest

from ebooklib import epub

from app.services.converter import EPUBToPDFConverter, ConversionError


@pytest.fixture
def converter():
    return EPUBToPDFConverter()


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
        book.toc = [epub.EpubNcx()]
        
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
        """Test text escaping for reportlab."""
        text = "Text with <special> & characters"
        escaped = converter._escape_text(text)

        # Should escape the special characters
        assert "&" in escaped
        assert "<" in escaped
        assert ">" in escaped
        # Check that the text content is preserved (escaped)
        assert "Text with" in escaped
        assert "special" in escaped
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
        book.toc = [epub.EpubNcx()]
        
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
            chapter = epub.EpubHtml(title=f"Chapter {i}", file_name=f"chapter{i}.xhtml", lang="en")
            chapter.content = f"<h1>Chapter {i}</h1><p>This is the content of chapter {i}.</p>"
            book.add_item(chapter)
        
        # Set spine with proper tuples
        spine_items = [f"chapter{i}.xhtml" for i in range(1, 4)]
        book.spine = [(item, True) for item in spine_items]
        
        # Create NCX navigation
        book.toc = [epub.EpubNcx()]
        
        epub_buffer = io.BytesIO()
        epub.write_epub(epub_buffer, book, {})
        epub_content = epub_buffer.getvalue()
        
        pdf_content = converter.convert(epub_content)
        assert pdf_content is not None
        assert len(pdf_content) > 0
        assert pdf_content.startswith(b"%PDF")