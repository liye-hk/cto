import io
import logging
import os
import re
from typing import Optional, Dict, List, Tuple
from html.parser import HTMLParser
from html import unescape, escape

import ebooklib
from ebooklib import epub
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

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


class HTMLTextExtractor(HTMLParser):
    """Extract text while preserving structure and finding images"""
    def __init__(self):
        super().__init__()
        self.elements = [] 
        self.current_tag = None
        self.images = []
    
    def handle_starttag(self, tag, attrs):
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.current_tag = 'heading'
        elif tag == 'p':
            self.current_tag = 'paragraph'
        elif tag == 'li':
            self.current_tag = 'list_item'
        elif tag == 'img':
            attrs_dict = dict(attrs)
            src = attrs_dict.get('src', '')
            if src:
                self.images.append(src)
    
    def handle_data(self, data):
        if data.strip():
            # Use 'paragraph' as default if no tag matches
            tag_type = self.current_tag if self.current_tag else 'paragraph'
            self.elements.append((tag_type, data.strip()))
    
    def handle_endtag(self, tag):
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li']:
            self.current_tag = None


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
            
            # Extract images from EPUB
            epub_images = self._extract_images(epub_book)

            # Create PDF in memory
            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
            story = []

            # Check if CJK fonts were successfully registered
            wqy_registered = any(name.startswith('WenQuanYi') for name in pdfmetrics.getRegisteredFontNames())
            
            styles = getSampleStyleSheet()
            if wqy_registered:
                # Define styles using WenQuanYi
                styles.add(ParagraphStyle(
                    'CJKBody',
                    fontName='WenQuanYi',
                    fontSize=11,
                    leading=14,
                    spaceAfter=8,
                ))
                styles.add(ParagraphStyle(
                    'CJKHeading',
                    fontName='WenQuanYi',
                    fontBold=True,
                    fontSize=16,
                    leading=20,
                    spaceAfter=12,
                    textColor=colors.HexColor('#333333'),
                ))
                styles.add(ParagraphStyle(
                    'CJKList',
                    fontName='WenQuanYi',
                    fontSize=11,
                    leading=14,
                    leftIndent=20,
                    spaceAfter=6,
                ))
                self.logger.info("Using WenQuanYi CJK fonts for PDF generation")
            else:
                # Fallback styles
                styles.add(ParagraphStyle(
                    'CJKBody',
                    fontName='Helvetica',
                    fontSize=11,
                    leading=14,
                    spaceAfter=8,
                ))
                styles.add(ParagraphStyle(
                    'CJKHeading',
                    fontName='Helvetica-Bold',
                    fontSize=16,
                    leading=20,
                    spaceAfter=12,
                    textColor=colors.HexColor('#333333'),
                ))
                styles.add(ParagraphStyle(
                    'CJKList',
                    fontName='Helvetica',
                    fontSize=11,
                    leading=14,
                    leftIndent=20,
                    spaceAfter=6,
                ))
                self.logger.warning("Using fallback fonts - CJK characters may not render correctly")

            # Add book title if available
            if epub_book.title:
                try:
                    title_text = epub_book.title
                    if isinstance(title_text, tuple) or isinstance(title_text, list):
                        title_text = title_text[0]
                    
                    if title_text:
                        story.append(Paragraph(self._escape_text(str(title_text)[:500]), styles['CJKHeading']))
                        story.append(Spacer(1, 0.3 * inch))
                except Exception as e:
                    self.logger.warning(f"Skipped title: {str(e)}")

            # Process chapters
            for item in epub_book.spine:
                # Spine items are typically tuples like ('chapter_id', 'yes'/'no')
                if isinstance(item, tuple):
                    item_id = item[0]
                else:
                    item_id = item

                try:
                    chapter = epub_book.get_item_with_id(item_id)
                    if chapter is None:
                        continue
                    
                    # Only process HTML/document items
                    if not isinstance(chapter, epub.EpubHtml):
                        continue
                    
                    content = chapter.get_content().decode('utf-8', errors='ignore')
                    
                    # Extract text and structure
                    extractor = HTMLTextExtractor()
                    extractor.feed(content)
                    
                    # Add chapter content to PDF
                    for item_type, item_data in extractor.elements:
                        if item_type == 'heading':
                            p = Paragraph(escape(item_data[:500]), styles['CJKHeading'])
                            story.append(p)
                        elif item_type == 'paragraph':
                            p = Paragraph(escape(item_data[:500]), styles['CJKBody'])
                            story.append(p)
                        elif item_type == 'list_item':
                            text = f"• {item_data[:500]}"
                            p = Paragraph(escape(text), styles['CJKList'])
                            story.append(p)
                    
                    # Try to embed images found in chapter
                    for img_src in extractor.images:
                        # Extract basename from path
                        img_path = img_src.replace('../', '').split('/')[-1]
                        
                        if img_path in epub_images:
                            try:
                                img_bytes = io.BytesIO(epub_images[img_path])
                                img = Image(img_bytes, width=4*inch, height=3*inch)
                                story.append(img)
                                story.append(Spacer(1, 0.2*inch))
                            except Exception as e:
                                self.logger.warning(f"Failed to embed image {img_path}: {e}")
                    
                    story.append(PageBreak())
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process chapter: {e}")
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

    def _extract_images(self, book: epub.EpubBook) -> Dict[str, bytes]:
        """
        Extract all images from EPUB book, keyed by filename (basename).
        """
        images = {}
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_IMAGE:
                # Store by basename to match logic in converter
                # Some epubs might have same filename in different folders, this might overwrite
                # but it matches the simplified logic we are implementing.
                basename = os.path.basename(item.get_name())
                images[basename] = item.get_content()
        return images

    def _escape_text(self, text: str) -> str:
        """
        Escape special characters for reportlab.
        Using html.escape is preferred now but keeping this for compatibility/fallback usage.
        """
        return escape(text)
