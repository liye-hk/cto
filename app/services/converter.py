import io
import logging
import os
import re
from typing import Optional

from ebooklib import epub
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
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
        self._setup_unicode_fonts()

    def _setup_unicode_fonts(self):
        """Setup Unicode-compatible fonts for PDF generation."""
        try:
            # Common font paths for Unicode support
            font_paths = [
                # Linux/Unix systems
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
                '/usr/share/fonts/TTF/DejaVuSans.ttf',
                # macOS
                '/System/Library/Fonts/Arial.ttf',
                '/Library/Fonts/Arial.ttf',
                # Windows
                'C:\\Windows\\Fonts\\arial.ttf',
                'C:\\Windows\\Fonts\\calibri.ttf',
            ]
            
            # Try to find and register a Unicode font
            font_registered = False
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('UnicodeSans', font_path))
                        self.logger.info(f"Registered Unicode font: {font_path}")
                        font_registered = True
                        break
                    except Exception as e:
                        self.logger.warning(f"Failed to register font {font_path}: {e}")
                        continue
            
            if not font_registered:
                self.logger.warning("No Unicode fonts found, using default fonts")
                
        except Exception as e:
            self.logger.warning(f"Font setup error: {e}")
            # Continue without Unicode font - reportlab will handle as best as possible

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
            doc = SimpleDocTemplate(
                pdf_buffer,
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72,
            )

            # Build story with EPUB content
            story = self._extract_epub_content(epub_book)
            
            # Use Unicode font if available
            available_fonts = pdfmetrics.getRegisteredFontNames()
            font_name = 'UnicodeSans' if 'UnicodeSans' in available_fonts else 'Helvetica'
            
            # Update all paragraph styles to use Unicode font
            for element in story:
                if hasattr(element, 'style') and element.style:
                    element.style.fontName = font_name
            
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

    def _extract_epub_content(self, book: epub.EpubBook) -> list:
        """
        Extract content from EPUB book and convert to reportlab elements.

        Args:
            book: Parsed EpubBook object

        Returns:
            List of reportlab flowable elements
        """
        story = []
        styles = getSampleStyleSheet()
        
        # Use Unicode font if available
        available_fonts = pdfmetrics.getRegisteredFontNames()
        font_name = 'UnicodeSans' if 'UnicodeSans' in available_fonts else 'Helvetica'
        
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            textColor="black",
            spaceAfter=12,
            alignment=1,
            fontName=font_name,
        )
        heading_style = ParagraphStyle(
            "CustomHeading",
            parent=styles["Heading2"],
            fontSize=14,
            textColor="black",
            spaceAfter=10,
            fontName=font_name,
        )
        body_style = ParagraphStyle(
            "CustomBody",
            parent=styles["Normal"],
            fontSize=11,
            alignment=4,
            spaceAfter=6,
            fontName=font_name,
        )

        # Add book title if available
        if book.title:
            story.append(Paragraph(self._escape_text(book.title), title_style))
            story.append(Spacer(1, 0.3 * inch))

        # Process chapters
        for item in book.spine:
            # Spine items are typically tuples like ('chapter_id', 'yes'/'no')
            if isinstance(item, tuple):
                item_id = item[0]
            else:
                item_id = item

            chapter = book.get_item_with_id(item_id)
            if chapter is None:
                continue

            # Only process HTML/document items
            if isinstance(chapter, epub.EpubHtml):
                try:
                    content = chapter.get_content().decode("utf-8", errors="ignore")
                    html_elements = self._parse_html_content(content)
                    story.extend(html_elements)
                    story.append(PageBreak())
                except Exception as e:
                    self.logger.warning(f"Failed to process chapter: {str(e)}")
                    continue

        return story

    def _parse_html_content(self, html_content: str) -> list:
        """
        Parse HTML content and convert to reportlab elements.

        Args:
            html_content: HTML string

        Returns:
            List of reportlab flowable elements
        """
        elements = []
        styles = getSampleStyleSheet()

        # Use Unicode font if available
        available_fonts = pdfmetrics.getRegisteredFontNames()
        font_name = 'UnicodeSans' if 'UnicodeSans' in available_fonts else 'Helvetica'

        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=11,
            alignment=4,
            spaceAfter=6,
            fontName=font_name,
        )

        heading_style = ParagraphStyle(
            "Heading",
            parent=styles["Heading2"],
            fontSize=14,
            textColor="black",
            spaceAfter=10,
            fontName=font_name,
        )

        # Simple HTML parsing - extract text content and basic structure
        text_content = self._html_to_text(html_content)

        for line in text_content.split("\n"):
            stripped = line.strip()
            if not stripped:
                elements.append(Spacer(1, 0.1 * inch))
                continue

            # Check if line looks like a heading
            if self._is_heading(stripped):
                elements.append(Paragraph(self._escape_text(stripped), heading_style))
            else:
                elements.append(Paragraph(self._escape_text(stripped), body_style))

        return elements

    def _html_to_text(self, html_content: str) -> str:
        """
        Convert HTML to plain text, preserving basic structure.

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
        text = re.sub(r"</p>", "\n", text)
        text = re.sub(r"<div[^>]*>", "", text)
        text = re.sub(r"</div>", "\n", text)
        text = re.sub(r"<h[1-6][^>]*>", "", text)
        text = re.sub(r"</h[1-6]>", "\n", text)
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

    def _is_heading(self, text: str) -> bool:
        """
        Check if text looks like a heading.

        Args:
            text: Text to check

        Returns:
            True if text appears to be a heading
        """
        # Simple heuristic: if it's short and starts with capital letter, treat as heading
        return len(text) < 100 and text[0].isupper() and len(text.split()) < 10

    def _escape_text(self, text: str) -> str:
        """
        Escape special characters for reportlab.

        Args:
            text: Text to escape

        Returns:
            Escaped text safe for reportlab
        """
        # Replace problematic characters
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        return text
