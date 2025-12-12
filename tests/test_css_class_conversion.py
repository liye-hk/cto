"""
Tests for CSS class to HTML tag conversion feature.

This test suite verifies that CSS classes like "bold", "center", etc.
are properly converted to corresponding HTML tags and attributes
for WeasyPrint rendering.
"""

import io
import pytest
from ebooklib import epub
from app.services.converter import (
    EPUBToPDFConverter,
    convert_css_classes_to_html,
    _is_bold_class,
    _is_center_class,
)


class TestCSSClassDetection:
    """Test detection of bold and center CSS classes."""

    def test_is_bold_class_with_exact_names(self):
        """Test detection of bold class with exact class names."""
        assert _is_bold_class('bold')
        assert _is_bold_class('strong')
        assert _is_bold_class('fw-bold')
        assert _is_bold_class('font-bold')
        assert _is_bold_class('font-weight-bold')

    def test_is_bold_class_with_substring(self):
        """Test detection of bold class with substring matching."""
        assert _is_bold_class('mybold')
        assert _is_bold_class('strongtext')
        assert _is_bold_class('text-bold-important')

    def test_is_bold_class_with_multiple_classes(self):
        """Test detection in multiple class attribute."""
        assert _is_bold_class('bold large')
        assert _is_bold_class('important strong')
        assert _is_bold_class('fw-bold mx-2')

    def test_is_bold_class_returns_false_for_non_bold(self):
        """Test that non-bold classes are correctly rejected."""
        assert not _is_bold_class('normal')
        assert not _is_bold_class('text-large')
        assert not _is_bold_class('x1')
        assert not _is_bold_class('')

    def test_is_center_class_with_exact_names(self):
        """Test detection of center class with exact class names."""
        assert _is_center_class('center')
        assert _is_center_class('centered')
        assert _is_center_class('text-center')
        assert _is_center_class('align-center')

    def test_is_center_class_with_substring(self):
        """Test detection of center class with substring matching."""
        assert _is_center_class('mycenter')
        assert _is_center_class('textcenter')
        assert _is_center_class('center-aligned')

    def test_is_center_class_with_multiple_classes(self):
        """Test detection in multiple class attribute."""
        assert _is_center_class('center large')
        assert _is_center_class('text-center mx-2')

    def test_is_center_class_returns_false_for_non_center(self):
        """Test that non-center classes are correctly rejected."""
        assert not _is_center_class('left')
        assert not _is_center_class('right')
        assert not _is_center_class('normal')
        assert not _is_center_class('')


class TestCSSClassConversion:
    """Test conversion of CSS classes to HTML tags."""

    def test_convert_span_with_bold_class(self):
        """Test conversion of span with bold class."""
        html = '<span class="bold">Bold text</span>'
        result = convert_css_classes_to_html(html)
        assert '<b>' in result
        assert '</b>' in result
        assert 'Bold text' in result

    def test_convert_div_with_bold_class(self):
        """Test conversion of div with bold class."""
        html = '<div class="bold">Bold content</div>'
        result = convert_css_classes_to_html(html)
        assert '<b>' in result
        assert '</b>' in result
        assert 'Bold content' in result

    def test_convert_p_with_center_class(self):
        """Test conversion of p with center class."""
        html = '<p class="center">Centered text</p>'
        result = convert_css_classes_to_html(html)
        assert 'align="center"' in result
        assert 'Centered text' in result

    def test_convert_p_with_centered_class(self):
        """Test conversion of p with 'centered' class."""
        html = '<p class="centered">Centered text</p>'
        result = convert_css_classes_to_html(html)
        assert 'align="center"' in result

    def test_convert_multiple_classes_with_bold(self):
        """Test conversion with multiple classes where one is bold."""
        html = '<span class="bold important">Bold text</span>'
        result = convert_css_classes_to_html(html)
        assert '<b>' in result
        assert '</b>' in result
        # Class should be removed since it's bold
        assert 'class="bold important"' not in result

    def test_convert_multiple_classes_with_center(self):
        """Test conversion with multiple classes where one is center."""
        html = '<p class="center text-lg">Centered text</p>'
        result = convert_css_classes_to_html(html)
        assert 'align="center"' in result
        # Class should still be preserved since it's not bold
        assert 'class="center text-lg"' in result

    def test_preserve_non_bold_center_classes(self):
        """Test that non-bold, non-center classes are preserved."""
        html = '<span class="x1">Text</span>'
        result = convert_css_classes_to_html(html)
        assert 'class="x1"' in result
        assert '<b>' not in result

    def test_mixed_content_with_bold_and_center(self):
        """Test mixed content with both bold and center formatting."""
        html = '<div><span class="bold">Bold</span> and <p class="center">Centered</p></div>'
        result = convert_css_classes_to_html(html)
        assert '<b>Bold</b>' in result
        assert 'align="center"' in result

    def test_nested_tags_with_bold_class(self):
        """Test nested tags with bold class."""
        html = '<p><span class="bold">Bold <i>italic</i> text</span></p>'
        result = convert_css_classes_to_html(html)
        assert '<b>' in result
        assert '<i>' in result
        assert '</b>' in result

    def test_empty_class_attribute(self):
        """Test handling of empty class attribute."""
        html = '<span class="">Text</span>'
        result = convert_css_classes_to_html(html)
        assert 'Text' in result

    def test_case_insensitivity(self):
        """Test case insensitivity of class detection."""
        html = '<span class="Bold">Bold text</span>'
        result = convert_css_classes_to_html(html)
        assert '<b>' in result

    def test_preserves_other_attributes(self):
        """Test that other attributes are preserved."""
        html = '<span class="bold" id="myspan" data-attr="value">Text</span>'
        result = convert_css_classes_to_html(html)
        assert '<b>' in result
        assert 'id="myspan"' in result or 'data-attr' in result


class TestCSSClassConversionIntegration:
    """Integration tests for CSS class conversion with EPUB to PDF conversion."""

    @staticmethod
    def _build_epub_with_css_classes(html: str) -> bytes:
        """Build a test EPUB with CSS classes."""
        book = epub.EpubBook()
        book.set_identifier("css_class_test")
        book.set_title("CSS Class Test")

        chapter = epub.EpubHtml(title="Chapter", file_name="chapter.xhtml", lang="en")
        chapter.content = html
        book.add_item(chapter)

        book.spine = [("chapter.xhtml", True)]
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        epub_buffer = io.BytesIO()
        epub.write_epub(epub_buffer, book, {})
        return epub_buffer.getvalue()

    def test_bold_class_span_in_epub(self):
        """Test EPUB conversion with bold class span."""
        html = '<p><span class="bold">Bold text</span> normal text</p>'
        epub_content = self._build_epub_with_css_classes(html)

        converter = EPUBToPDFConverter()
        pdf_content = converter.convert(epub_content)

        assert pdf_content is not None
        assert len(pdf_content) > 0
        assert pdf_content.startswith(b"%PDF")

    def test_center_class_p_in_epub(self):
        """Test EPUB conversion with center class paragraph."""
        html = '<p class="center">Centered paragraph</p>'
        epub_content = self._build_epub_with_css_classes(html)

        converter = EPUBToPDFConverter()
        pdf_content = converter.convert(epub_content)

        assert pdf_content is not None
        assert len(pdf_content) > 0
        assert pdf_content.startswith(b"%PDF")

    def test_mixed_bold_and_center_in_epub(self):
        """Test EPUB conversion with mixed bold and center formatting."""
        html = '''
        <h1 class="center">Title</h1>
        <p><span class="bold">Bold intro</span> with <span class="mybold">more bold</span></p>
        <p class="center">This is <span class="bold">bold and centered</span></p>
        '''
        epub_content = self._build_epub_with_css_classes(html)

        converter = EPUBToPDFConverter()
        pdf_content = converter.convert(epub_content)

        assert pdf_content is not None
        assert len(pdf_content) > 0
        assert pdf_content.startswith(b"%PDF")

    def test_preserves_unknown_classes_for_css_processing(self):
        """Test that unknown classes are preserved for later CSS processing."""
        html = '<p><span class="x1">Text with x1 class</span></p>'
        epub_content = self._build_epub_with_css_classes(html)

        converter = EPUBToPDFConverter()
        pdf_content = converter.convert(epub_content)

        # Should still produce valid PDF even if x1 class isn't recognized
        assert pdf_content is not None
        assert len(pdf_content) > 0
        assert pdf_content.startswith(b"%PDF")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
