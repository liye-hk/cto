import io
import logging
import os
import re
from typing import Dict, List, Tuple, Optional
from html.parser import HTMLParser
from html import escape

import ebooklib
from ebooklib import epub
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Spacer, Image as RLImage
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

ALLOWED_INLINE_TAG_PATTERN = re.compile(
    r'(?i)(</?(?:b|strong|i|em|u|font)(?:\s+[^<>]*?)?>|<br\s*/?>)'
)

# Safe maximum image dimensions (smaller than page limits)
MAX_IMG_WIDTH = 6.0 * inch  # 6 inches (safer than full page width)
MAX_IMG_HEIGHT = 8.0 * inch  # 8 inches (safer than full page height)
DEFAULT_IMAGE_WIDTH = 4 * inch
DEFAULT_IMAGE_HEIGHT = 3 * inch

_FONTS_INITIALIZED = False


# Register fonts at module initialization
def _initialize_fonts():
    """Initialize fonts once at startup"""
    global _FONTS_INITIALIZED
    if _FONTS_INITIALIZED:
        return

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

    _FONTS_INITIALIZED = True


# Call once at module load
_initialize_fonts()


class FormattingPreservingExtractor(HTMLParser):
    """Extract text with formatting, colors, alignment, and images."""

    HEADING_TAGS = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
    BLOCK_TAGS = HEADING_TAGS.union({'p', 'li', 'div', 'center'})
    LIST_CONTAINER_TAGS = {'ul', 'ol'}
    INLINE_FORMATTING_TAGS = {'b', 'strong', 'i', 'em', 'u'}
    COLOR_STYLE_PATTERN = re.compile(r'color\s*:\s*([^;]+)', re.IGNORECASE)

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.elements: List[Tuple[str, object]] = []
        self.current_text: List[str] = []
        self.current_tag: Optional[str] = None
        self.current_attrs: Dict[str, str] = {}
        self.font_stack: List[bool] = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs_dict = {
            k.lower(): v for k, v in attrs
            if isinstance(k, str) and v is not None
        }

        if tag in self.BLOCK_TAGS:
            self._flush_text()
            if tag in self.HEADING_TAGS:
                self.current_tag = tag
            elif tag == 'li':
                self.current_tag = 'li'
            elif tag == 'div':
                self.current_tag = 'div'
            elif tag == 'center':
                self.current_tag = 'center'
                attrs_dict = dict(attrs_dict)
                attrs_dict.setdefault('align', 'center')
            else:
                self.current_tag = 'p'
            self.current_attrs = dict(attrs_dict)
        elif tag in self.LIST_CONTAINER_TAGS:
            self._flush_text()
            self.current_tag = None
            self.current_attrs = {}

        if tag in {'b', 'strong'}:
            self.current_text.append('<b>')
        elif tag in {'i', 'em'}:
            self.current_text.append('<i>')
        elif tag == 'u':
            self.current_text.append('<u>')
        elif tag == 'font':
            color = self._normalize_color(attrs_dict.get('color'))
            if not color:
                color = self._extract_color_from_style(attrs_dict.get('style', ''))
            has_font = bool(color)
            if color:
                self.current_text.append(f'<font color="{color}">')
            self.font_stack.append(has_font)
        elif tag == 'span':
            color = self._extract_color_from_style(attrs_dict.get('style', ''))
            has_font = bool(color)
            if color:
                self.current_text.append(f'<font color="{color}">')
            self.font_stack.append(has_font)
        elif tag == 'br':
            self.current_text.append('<br/>')
        elif tag == 'img':
            self._flush_text()
            src = attrs_dict.get('src') or ''
            width = attrs_dict.get('width') or ''
            height = attrs_dict.get('height') or ''
            style = attrs_dict.get('style') or ''
            if not width:
                width_match = re.search(r'width\s*:\s*([^;]+)', style, re.IGNORECASE)
                if width_match:
                    width = width_match.group(1).strip()
            if not height:
                height_match = re.search(r'height\s*:\s*([^;]+)', style, re.IGNORECASE)
                if height_match:
                    height = height_match.group(1).strip()
            if src:
                self.elements.append(('img', {
                    'src': src,
                    'width': width,
                    'height': height,
                }))

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        if tag == 'br':
            self.current_text.append('<br/>')
        elif tag == 'img':
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {'b', 'strong'}:
            self.current_text.append('</b>')
        elif tag in {'i', 'em'}:
            self.current_text.append('</i>')
        elif tag == 'u':
            self.current_text.append('</u>')
        elif tag in {'font', 'span'}:
            if self.font_stack:
                has_font = self.font_stack.pop()
                if has_font:
                    self.current_text.append('</font>')
        elif tag == 'br':
            self.current_text.append('<br/>')
        elif tag in self.BLOCK_TAGS or tag in self.LIST_CONTAINER_TAGS:
            self._flush_text()
            self.current_tag = None
            self.current_attrs = {}

    def handle_data(self, data):
        if not data:
            return
        normalized = data.replace('\xa0', ' ')
        normalized = re.sub(r'\s+', ' ', normalized)
        if normalized:
            self.current_text.append(normalized)

    def close(self):
        super().close()
        self._flush_text()

    def _flush_text(self):
        if not self.current_text:
            return
        text = ''.join(self.current_text)
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        if text:
            attrs_copy = dict(self.current_attrs)
            self.elements.append((self.current_tag or 'p', text, attrs_copy))
        self.current_text = []

    @classmethod
    def _extract_color_from_style(cls, style: Optional[str]) -> Optional[str]:
        if not style:
            return None
        match = cls.COLOR_STYLE_PATTERN.search(style)
        if not match:
            return None
        color = match.group(1).strip()
        color = color.split('!important')[0].strip()
        return cls._normalize_color(color)

    @staticmethod
    def _normalize_color(color: Optional[str]) -> Optional[str]:
        if not color:
            return None
        color = color.strip().strip('"\'')
        if not color:
            return None
        base_color = color.split('!important')[0].strip()
        if not base_color:
            return None
        base_color = base_color.replace(' ', '')
        if base_color.startswith('#'):
            if re.fullmatch(r'#([0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})', base_color):
                return base_color
            return None
        hex_match = re.fullmatch(r'([0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})', base_color)
        if hex_match:
            return f"#{hex_match.group(1)}"
        if base_color.lower().startswith('rgb'):
            return base_color.lower()
        if re.fullmatch(r'[a-zA-Z]+', base_color):
            return base_color.lower()
        return None


def parse_dimension(dim_str: Optional[str]) -> Optional[float]:
    """Parse a dimension string (e.g. 100px, 10cm, 50%)."""
    if not dim_str:
        return None

    dim_value = str(dim_str).strip().strip('"\'')
    if not dim_value:
        return None

    dim_value = dim_value.split('!important')[0].strip()
    match = re.match(r'([0-9]*\.?[0-9]+)\s*(%|px|pt|cm|mm|in)?', dim_value, re.IGNORECASE)
    if not match:
        return None

    value = float(match.group(1))
    unit = (match.group(2) or 'px').lower()

    if unit == 'px':
        return value * PIXELS_TO_POINTS
    if unit == 'pt':
        return value
    if unit == 'cm':
        return value * 28.35
    if unit == 'mm':
        return value * 2.835
    if unit == 'in':
        return value * 72
    if unit == '%':
        return (value / 100.0) * MAX_IMAGE_WIDTH
    return None


def get_alignment(attrs_dict: Optional[Dict[str, str]]) -> int:
    """Determine paragraph alignment from attributes, classes, or styles."""
    if not attrs_dict:
        return TA_JUSTIFY

    align_attr = (attrs_dict.get('align') or '').strip().lower()
    if align_attr == 'center':
        return TA_CENTER
    if align_attr == 'right':
        return TA_RIGHT
    if align_attr == 'left':
        return TA_LEFT
    if align_attr == 'justify':
        return TA_JUSTIFY

    style_attr = attrs_dict.get('style') or ''
    style_match = re.search(r'text-align\s*:\s*(left|center|right|justify)', style_attr, re.IGNORECASE)
    if style_match:
        value = style_match.group(1).lower()
        if value == 'center':
            return TA_CENTER
        if value == 'right':
            return TA_RIGHT
        if value == 'left':
            return TA_LEFT
        if value == 'justify':
            return TA_JUSTIFY

    class_attr = attrs_dict.get('class') or ''
    if re.search(r'\b(center|centered)\b', class_attr, re.IGNORECASE):
        return TA_CENTER

    return TA_JUSTIFY


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
            _initialize_fonts()

            epub_book = self._parse_epub(epub_content)
            self.logger.info("EPUB loaded")

            epub_images = self._extract_images(epub_book)

            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                pdf_buffer,
                pagesize=letter,
                topMargin=0.5 * inch,
                bottomMargin=0.5 * inch,
            )
            story = []

            wqy_registered = any(name.startswith('WenQuanYi') for name in pdfmetrics.getRegisteredFontNames())
            font_name = 'WenQuanYi' if wqy_registered else 'Helvetica'

            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(
                'CJKHeading1',
                fontName=font_name,
                fontSize=18,
                leading=22,
                spaceAfter=12,
                spaceBefore=12,
                textColor=colors.HexColor('#000000'),
                fontBold=True,
                alignment=TA_JUSTIFY,
            ))
            styles.add(ParagraphStyle(
                'CJKHeading2',
                fontName=font_name,
                fontSize=16,
                leading=20,
                spaceAfter=10,
                spaceBefore=10,
                fontBold=True,
                alignment=TA_JUSTIFY,
            ))
            styles.add(ParagraphStyle(
                'CJKHeading3',
                fontName=font_name,
                fontSize=14,
                leading=18,
                spaceAfter=8,
                spaceBefore=8,
                fontBold=True,
                alignment=TA_JUSTIFY,
            ))
            styles.add(ParagraphStyle(
                'CJKBody',
                fontName=font_name,
                fontSize=11,
                leading=16,
                spaceAfter=6,
                alignment=TA_JUSTIFY,
                firstLineIndent=0.25 * inch,
            ))
            styles.add(ParagraphStyle(
                'CJKList',
                fontName=font_name,
                fontSize=11,
                leading=14,
                leftIndent=20,
                spaceAfter=4,
                alignment=TA_LEFT,
            ))

            if not wqy_registered:
                self.logger.warning("Using fallback fonts - CJK characters may not render correctly")

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
            center_count = 0
            bold_count = 0
            color_count = 0

            for item in epub_book.spine:
                item_id = item[0] if isinstance(item, tuple) else item

                try:
                    chapter = epub_book.get_item_with_id(item_id)
                    if chapter is None or not isinstance(chapter, epub.EpubHtml):
                        continue

                    chapters_processed += 1
                    content = chapter.get_content().decode('utf-8', errors='ignore')

                    extractor = FormattingPreservingExtractor()
                    extractor.feed(content)
                    extractor.close()

                    for element in extractor.elements:
                        try:
                            if not element:
                                continue

                            elem_type = element[0]

                            if elem_type == 'img':
                                img_data = element[1] if len(element) > 1 else {}
                                if not isinstance(img_data, dict):
                                    continue

                                img_src = (img_data.get('src') or '').replace('../', '')
                                img_name = img_src.split('/')[-1]
                                if not img_name:
                                    continue

                                matched = False
                                for epub_img_name, raw_img in epub_images.items():
                                    if img_name not in epub_img_name and not epub_img_name.endswith(img_name):
                                        continue

                                    try:
                                        # Try to load image to get actual size using PIL
                                        try:
                                            from PIL import Image as PILImage
                                            img_pil = PILImage.open(io.BytesIO(raw_img))
                                            pil_width, pil_height = img_pil.size
                                            
                                            # Convert pixels to inches (assume 96 dpi)
                                            width = pil_width / 96.0 * inch
                                            height = pil_height / 96.0 * inch
                                            
                                            self.logger.info(f"Image original size: {pil_width}x{pil_height}px ({width:.1f}x{height:.1f}in)")
                                        except Exception as e:
                                            self.logger.warning(f"Could not read image dimensions: {e}, using default")
                                            width = DEFAULT_IMAGE_WIDTH
                                            height = DEFAULT_IMAGE_HEIGHT
                                        
                                        # Scale down if exceeds safe limits
                                        if width > MAX_IMG_WIDTH or height > MAX_IMG_HEIGHT:
                                            # Calculate scale factor
                                            scale_w = MAX_IMG_WIDTH / width if width > MAX_IMG_WIDTH else 1.0
                                            scale_h = MAX_IMG_HEIGHT / height if height > MAX_IMG_HEIGHT else 1.0
                                            scale = min(scale_w, scale_h)
                                            
                                            width = width * scale
                                            height = height * scale
                                            self.logger.info(f"Scaled image to: {width:.1f}x{height:.1f}in")
                                        
                                        image_buffer = io.BytesIO(raw_img)
                                        img = RLImage(image_buffer, width=width, height=height)
                                        story.append(img)
                                        story.append(Spacer(1, 0.1 * inch))
                                        images_added += 1
                                        self.logger.info(f"✓ Added image: {epub_img_name}")
                                        matched = True
                                        break
                                    except Exception as e:
                                        self.logger.error(f"✗ Failed to add image {epub_img_name}: {e}")
                                        continue

                                if not matched:
                                    continue
                            else:
                                elem_text = element[1]
                                attrs = element[2] if len(element) > 2 and isinstance(element[2], dict) else {}
                                if not isinstance(elem_text, str):
                                    continue

                                safe_data = self._escape_text(elem_text)
                                if not safe_data:
                                    continue

                                # Check for bold and color
                                has_bold = '<b>' in elem_text or '<strong>' in elem_text
                                has_color = '<font color' in elem_text
                                
                                if has_bold:
                                    bold_count += 1
                                    self.logger.debug(f"Bold text detected: {elem_text[:50]}")
                                if has_color:
                                    color_count += 1
                                    self.logger.debug(f"Color text detected: {elem_text[:50]}")

                                alignment = get_alignment(attrs)
                                
                                # Check for center alignment
                                if alignment == TA_CENTER:
                                    center_count += 1
                                    self.logger.debug(f"Center text detected: {elem_text[:50]}")

                                if elem_type == 'h1':
                                    style = ParagraphStyle('H1Temp', parent=styles['CJKHeading1'], alignment=alignment)
                                    story.append(Paragraph(safe_data, style))
                                elif elem_type == 'h2':
                                    style = ParagraphStyle('H2Temp', parent=styles['CJKHeading2'], alignment=alignment)
                                    story.append(Paragraph(safe_data, style))
                                elif elem_type in ['h3', 'h4', 'h5', 'h6']:
                                    style = ParagraphStyle('H3Temp', parent=styles['CJKHeading3'], alignment=alignment)
                                    story.append(Paragraph(safe_data, style))
                                elif elem_type == 'li':
                                    style = ParagraphStyle('ListTemp', parent=styles['CJKList'], alignment=alignment)
                                    story.append(Paragraph(f"<b>•</b> {safe_data}", style))
                                else:
                                    body_kwargs = {'alignment': alignment}
                                    if alignment in (TA_CENTER, TA_RIGHT):
                                        body_kwargs['firstLineIndent'] = 0
                                    style = ParagraphStyle('BodyTemp', parent=styles['CJKBody'], **body_kwargs)
                                    story.append(Paragraph(safe_data, style))
                                    story.append(Spacer(1, 0.08 * inch))
                        except Exception as e:
                            self.logger.warning(f"Failed to add element: {e}")

                    story.append(PageBreak())
                except Exception as e:
                    self.logger.error(f"Error in chapter {item_id}: {e}")
                    continue

            self.logger.info(
                f"Done: {chapters_processed} chapters, {images_added} images, {center_count} centered, {bold_count} bold, {color_count} colored"
            )

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
        Escape text for reportlab while preserving styling tags.
        """
        if not text:
            return ''

        parts: List[str] = []
        last_index = 0
        for match in ALLOWED_INLINE_TAG_PATTERN.finditer(text):
            start, end = match.span()
            if start > last_index:
                parts.append(escape(text[last_index:start]))
            parts.append(match.group(0))
            last_index = end

        if last_index < len(text):
            parts.append(escape(text[last_index:]))

        return ''.join(parts)
