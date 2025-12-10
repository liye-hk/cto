import io
import logging
import os
import re
from typing import Optional

from ebooklib import epub
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from html import unescape

logger = logging.getLogger(__name__)


class ConversionError(Exception):
    """Exception raised when conversion fails."""

    pass


class EPUBToPDFConverter:
    """Service to convert EPUB files to PDF."""

    def __init__(self):
        self.logger = logger
        self._register_cjk_font()

    def _register_cjk_font(self):
        """Register CJK font if available"""
        font_path = '/usr/share/fonts/truetype/wqy/wqy-microhei.ttf'
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('CJK', font_path))
                self.logger.info("Successfully registered CJK font")
                return True
            except Exception as e:
                self.logger.warning(f"Failed to register CJK font: {str(e)}")
        return False

    def convert(self, epub_content: bytes) -> bytes:
        """
        Convert EPUB content to PDF bytes.

        Args:
            epub_content: Raw bytes of the EPUB file

        Returns:
            PDF content as bytes

        Raises:
            ConversionError: If conversion fails
        """
        try:
            # Parse EPUB
            epub_book = self._parse_epub(epub_content)
            self.logger.info(f"Successfully parsed EPUB with {len(epub_book.spine)} chapters")

            # Create PDF in memory
            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)

            # Build story with EPUB content using simplified approach
            story = []
            styles = getSampleStyleSheet()

            # Don't override fontName - let reportlab handle it
            # Just extract text and let the simple style handle it

            # Add book title if available
            if epub_book.title:
                try:
                    title_text = self._extract_text_from_html(epub_book.title)
                    if title_text.strip():
                        story.append(Paragraph(self._escape_text(title_text[:500]), styles['Heading1']))
                        story.append(Spacer(1, 0.3 * inch))
                except Exception as e:
                    self.logger.warning(f"Skipped title: {str(e)}")

            # Process chapters with error handling
            for item in epub_book.spine:
                # Spine items are typically tuples like ('chapter_id', 'yes'/'no')
                if isinstance(item, tuple):
                    item_id = item[0]
                else:
                    item_id = item

                chapter = epub_book.get_item_with_id(item_id)
                if chapter is None:
                    continue

                # Only process HTML/document items
                if isinstance(chapter, epub.EpubHtml):
                    try:
                        content = chapter.get_content().decode('utf-8', errors='ignore')
                        
                        # Extract plain text from HTML
                        text = self._extract_text_from_html(content)
                        
                        if text.strip():
                            p = Paragraph(self._escape_text(text[:500]), styles['Normal'])
                            story.append(p)
                            story.append(Spacer(1, 0.2 * inch))
                    except Exception as e:
                        self.logger.warning(f"Skipped chapter: {str(e)}")
                        continue

            # Build the PDF
            doc.build(story)
            self.logger.info("PDF generated successfully")
            pdf_buffer.seek(0)
            return pdf_buffer.getvalue()

        except ConversionError:
            raise
        except Exception as e:
            self.logger.error(f"Conversion error: {str(e)}")
            raise ConversionError(f"Failed to convert EPUB to PDF: {str(e)}")

    def _parse_epub(self, epub_content: bytes) -> epub.EpubBook:
        """
        Parse EPUB content.

        Args:
            epub_content: Raw bytes of the EPUB file

        Returns:
            Parsed EpubBook object

        Raises:
            ConversionError: If EPUB parsing fails
        """
        try:
            epub_buffer = io.BytesIO(epub_content)
            book = epub.read_epub(epub_buffer)
            return book
        except Exception as e:
            self.logger.error(f"Failed to parse EPUB: {str(e)}")
            raise ConversionError(f"Invalid EPUB file: {str(e)}")

    def _extract_text_from_html(self, html_content: str) -> str:
        """
        Extract plain text from HTML content.

        Args:
            html_content: HTML string

        Returns:
            Plain text string
        """
        # Remove script and style tags
        text = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)

        # Add newlines before block elements
        text = re.sub(r"<p[^>]*>", "", text)
        text = re.sub(r"</p>", "\n\n", text)
        text = re.sub(r"<div[^>]*>", "", text)
        text = re.sub(r"</div>", "\n\n", text)
        text = re.sub(r"<h[1-6][^>]*>", "", text)
        text = re.sub(r"</h[1-6]>", "\n\n", text)
        text = re.sub(r"<br\s*/?>\s*", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<li[^>]*>", "- ", text)
        text = re.sub(r"</li>", "\n", text)

        # Remove other HTML tags
        text = re.sub(r"<[^>]+>", "", text)

        # Decode HTML entities
        text = unescape(text)

        # Clean up whitespace
        lines = text.split("\n")
        lines = [line.strip() for line in lines if line.strip()]
        return "\n".join(lines)

    def _escape_text(self, text: str) -> str:
        """
        Escape special characters for reportlab.

        Args:
            text: Text to escape

        Returns:
            Escaped text safe for reportlab
        """
        # Replace problematic characters
        text = text.replace("&", "&")
        text = text.replace("<", "<")
        text = text.replace(">", ">")
        return text