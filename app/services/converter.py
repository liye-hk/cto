import io
import logging
import os
from typing import Dict, List, Tuple, Optional, Union
from html.parser import HTMLParser
from html import escape

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


class TextAndImageExtractor(HTMLParser):
    """Extract text with structure info and images"""
    def __init__(self):
        super().__init__()
        self.elements = []
        self.current_text = []
        self.current_tag = None
    
    def handle_starttag(self, tag, attrs):
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self._flush_text()
            self.current_tag = tag
        elif tag == 'p':
            self._flush_text()
            self.current_tag = 'p'
        elif tag in ['li', 'ul', 'ol']:
            self._flush_text()
            self.current_tag = tag
        elif tag == 'img':
            self._flush_text()
            attrs_dict = dict(attrs)
            src = attrs_dict.get('src', '')
            if src:
                self.elements.append(('img', src))
    
    def handle_data(self, data):
        text = data.strip()
        if text:
            self.current_text.append(text)
    
    def handle_endtag(self, tag):
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li']:
            self._flush_text()
            self.current_tag = None
    
    def _flush_text(self):
        if self.current_text:
            text = ' '.join(self.current_text).strip()
            if text:
                self.elements.append((self.current_tag or 'p', text))
            self.current_text = []


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
            self.logger.info("EPUB loaded")
            
            # Extract images from EPUB with minimal logging
            epub_images = self._extract_images(epub_book)

            # Create PDF in memory
            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                pdf_buffer,
                pagesize=letter,
                topMargin=0.5 * inch,
                bottomMargin=0.5 * inch,
            )
            story = []

            # Check if CJK fonts were successfully registered
            wqy_registered = any(name.startswith('WenQuanYi') for name in pdfmetrics.getRegisteredFontNames())
            font_name = 'WenQuanYi' if wqy_registered else 'Helvetica'
            # If we didn't register family for Helvetica (built-in), we might need direct font names, 
            # but Helvetica is standard.
            
            styles = getSampleStyleSheet()
            
            # Define formatted styles
            styles.add(ParagraphStyle(
                'CJKHeading1',
                fontName=font_name,
                fontSize=18,
                leading=22,
                spaceAfter=12,
                spaceBefore=12,
                textColor=colors.HexColor('#000000'),
                fontBold=True
            ))
            
            styles.add(ParagraphStyle(
                'CJKHeading2',
                fontName=font_name,
                fontSize=16,
                leading=20,
                spaceAfter=10,
                spaceBefore=10,
                fontBold=True
            ))
            
            styles.add(ParagraphStyle(
                'CJKHeading3',
                fontName=font_name,
                fontSize=14,
                leading=18,
                spaceAfter=8,
                spaceBefore=8,
                fontBold=True
            ))
            
            styles.add(ParagraphStyle(
                'CJKBody',
                fontName=font_name,
                fontSize=11,
                leading=16,
                spaceAfter=6,
                alignment=4,  # Justify
            ))
            
            styles.add(ParagraphStyle(
                'CJKList',
                fontName=font_name,
                fontSize=11,
                leading=14,
                leftIndent=20,
                spaceAfter=4,
            ))
            
            if not wqy_registered:
                self.logger.warning("Using fallback fonts - CJK characters may not render correctly")

            # Add book title if available
            if epub_book.title:
                try:
                    title_text = epub_book.title
                    if isinstance(title_text, (tuple, list)):
                        title_text = title_text[0]
                    
                    if title_text:
                        story.append(Paragraph(self._escape_text(str(title_text)[:500]), styles['CJKHeading1']))
                        story.append(Spacer(1, 0.3 * inch))
                except Exception as e:
                    self.logger.warning(f"Skipped title: {str(e)}")

            self.logger.info("Processing chapters...")
            chapters_processed = 0
            images_added = 0

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
                    
                    chapters_processed += 1
                    content = chapter.get_content().decode('utf-8', errors='ignore')
                    
                    # Extract structured content
                    extractor = TextAndImageExtractor()
                    extractor.feed(content)

                    # Add elements to PDF
                    for elem_type, elem_data in extractor.elements:
                        try:
                            # Escape text content
                            safe_data = self._escape_text(elem_data)
                            
                            if elem_type == 'h1':
                                p = Paragraph(safe_data, styles['CJKHeading1'])
                                story.append(p)
                            elif elem_type == 'h2':
                                p = Paragraph(safe_data, styles['CJKHeading2'])
                                story.append(p)
                            elif elem_type in ['h3', 'h4', 'h5', 'h6']:
                                p = Paragraph(safe_data, styles['CJKHeading3'])
                                story.append(p)
                            elif elem_type == 'li':
                                p = Paragraph(f"• {safe_data}", styles['CJKList'])
                                story.append(p)
                            elif elem_type == 'img':
                                img_name = elem_data.replace('../', '').split('/')[-1]
                                found_img = False
                                for epub_img_name, img_data in epub_images.items():
                                    if img_name and (img_name in epub_img_name or epub_img_name.endswith(img_name)):
                                        try:
                                            img_buffer = io.BytesIO(img_data)
                                            # Using fixed size for now as per reference implementation
                                            img = Image(img_buffer, width=4*inch, height=3*inch)
                                            story.append(img)
                                            story.append(Spacer(1, 0.15*inch))
                                            images_added += 1
                                            self.logger.info(f"Added image to PDF: {epub_img_name}")
                                            found_img = True
                                            break
                                        except Exception as e:
                                            self.logger.warning(f"Could not add image {epub_img_name}: {e}")
                                
                                if not found_img:
                                    # Debug log only
                                    pass
                            else:  # Regular paragraph
                                p = Paragraph(safe_data, styles['CJKBody'])
                                story.append(p)
                                story.append(Spacer(1, 0.08*inch))
                        except Exception as e:
                            self.logger.warning(f"Failed to add element: {e}")

                    story.append(PageBreak())
                    
                except Exception as e:
                    self.logger.error(f"Error in chapter {item_id}: {e}")
                    continue

            self.logger.info(f"Conversion complete: {chapters_processed} chapters, {images_added} images added")

            # Build the PDF
            doc.build(story)
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
        Extract all images from EPUB book, keyed by the original item name.
        """
        images: Dict[str, bytes] = {}
        image_count = 0
        for item in book.get_items():
            item_type = item.get_type()
            is_image = item_type == ebooklib.ITEM_IMAGE

            if not is_image and isinstance(item_type, str):
                is_image = 'image' in item_type.lower()

            if not is_image:
                media_type = getattr(item, 'media_type', '')
                if isinstance(media_type, str):
                    is_image = 'image' in media_type.lower()

            if is_image:
                name = item.get_name()
                images[name] = item.get_content()
                image_count += 1
                # Disabled verbose logging as per requirement
                # self.logger.info(f"Found image: {name}")

        self.logger.info(f"Found {image_count} images in EPUB")
        return images

    def _escape_text(self, text: str) -> str:
        """
        Escape special characters for reportlab.
        """
        return escape(text)
