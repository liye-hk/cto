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

# Register fonts at module initialization
def _initialize_fonts():
    """Initialize fonts once at startup"""
    # First try to register WQY fonts (CJK support)
    wqy_fonts = {
        'WenQuanYi': '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
        'WenQuanYi-Bold': '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
    }
    
    for name, path in wqy_fonts.items():
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                logger.info(f"Registered font: {name}")
            except Exception as e:
                logger.warning(f"Failed to register WQY font {name}: {e}")
    
    # Try .ttf extension if .ttc fails
    if not any(name.startswith('WenQuanYi') for name in pdfmetrics.getRegisteredFontNames()):
        wqy_ttf = {
            'WenQuanYi': '/usr/share/fonts/truetype/wqy/wqy-microhei.ttf',
            'WenQuanYi-Bold': '/usr/share/fonts/truetype/wqy/wqy-microhei.ttf',
        }
        
        for name, path in wqy_ttf.items():
            if os.path.exists(path):
                try:
                    pdfmetrics.registerFont(TTFont(name, path))
                    logger.info(f"Registered WQY TTF font: {name}")
                except Exception as e:
                    logger.warning(f"Failed to register WQY TTF font {name}: {e}")
    
    # Check if WQY fonts were registered successfully
    wqy_registered = any(name.startswith('WenQuanYi') for name in pdfmetrics.getRegisteredFontNames())
    
    if wqy_registered:
        # Register font family for proper CJK font usage
        try:
            pdfmetrics.registerFontFamily('WenQuanYi', normal='WenQuanYi', bold='WenQuanYi-Bold', 
                                         italic='WenQuanYi', boldItalic='WenQuanYi-Bold')
            logger.info("Registered WenQuanYi font family")
        except Exception as e:
            logger.error(f"Failed to register font family: {e}")
    else:
        logger.warning("WQY fonts not available, CJK characters may not render properly")
        
        # Ensure at least DejaVu fonts are available for fallback
        if 'DejaVuSans' not in pdfmetrics.getRegisteredFontNames():
            try:
                pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
                pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
                logger.info("Registered DejaVu fallback fonts")
            except Exception as e:
                logger.error(f"Failed to register DejaVu fonts: {e}")

# Call once at module load
_initialize_fonts()


class ConversionError(Exception):
    """Exception raised when conversion fails."""

    pass


class EPUBToPDFConverter:
    """Service to convert EPUB files to PDF."""

    def __init__(self):
        self.logger = logger

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

            # Check if CJK fonts were successfully registered
            wqy_registered = any(name.startswith('WenQuanYi') for name in pdfmetrics.getRegisteredFontNames())
            
            if wqy_registered:
                # Create custom style with explicit CJK font
                cjk_style = ParagraphStyle(
                    'CJKBody',
                    fontName='WenQuanYi',
                    fontSize=11,
                    leading=14,
                )
                
                # Create custom heading style with CJK font
                cjk_heading_style = ParagraphStyle(
                    'CJKHeading',
                    fontName='WenQuanYi-Bold',
                    fontSize=16,
                    leading=19,
                )
                self.logger.info("Using WenQuanYi CJK fonts for PDF generation")
            else:
                # Use default styles with enhanced fallback
                cjk_style = ParagraphStyle(
                    'CJKBody',
                    fontName='Helvetica',
                    fontSize=11,
                    leading=14,
                )
                
                cjk_heading_style = ParagraphStyle(
                    'CJKHeading',
                    fontName='Helvetica-Bold',
                    fontSize=16,
                    leading=19,
                )
                self.logger.warning("Using fallback fonts - CJK characters may not render correctly")

            # Add book title if available
            if epub_book.title:
                try:
                    title_text = self._extract_text_from_html(epub_book.title)
                    if title_text.strip():
                        story.append(Paragraph(self._escape_text(title_text[:500]), cjk_heading_style))
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
                            p = Paragraph(self._escape_text(text[:500]), cjk_style)
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