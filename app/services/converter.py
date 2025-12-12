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
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    NextPageTemplate,
    Paragraph,
    PageBreak,
    Spacer,
    Image as RLImage,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

ALLOWED_INLINE_TAG_PATTERN = re.compile(
    r'(?i)(</?(?:b|strong|i|em|u|font)(?:\s+[^<>]*?)?>|<br\s*/?>)'
)

# Constants for dimension conversion
PIXELS_TO_POINTS = 72.0 / 96.0  # 96 DPI assumption

# Safe maximum image dimensions (in inches, not points)
MAX_IMG_WIDTH = 6.0  # 6 inches (safer than full page width)
MAX_IMG_HEIGHT = 8.0  # 8 inches (safer than full page height)
DEFAULT_IMAGE_WIDTH = 4.0  # inches
DEFAULT_IMAGE_HEIGHT = 3.0  # inches

# Content page margin definitions
CONTENT_LEFT_MARGIN = inch
CONTENT_RIGHT_MARGIN = inch
CONTENT_TOP_MARGIN = 0.5 * inch
CONTENT_BOTTOM_MARGIN = 0.5 * inch

_FONTS_INITIALIZED = False


# Register fonts at module initialization
def _initialize_fonts():
    """Initialize fonts once at startup."""

    global _FONTS_INITIALIZED
    if _FONTS_INITIALIZED:
        return

    def _try_register_ttf(font_name: str, path: str, **kwargs) -> bool:
        if font_name in pdfmetrics.getRegisteredFontNames():
            return True
        if not os.path.exists(path):
            return False

        try:
            pdfmetrics.registerFont(TTFont(font_name, path, **kwargs))
            logger.info(f"Registered font: {font_name} -> {path}")
            return True
        except TypeError:
            # Older reportlab versions may not support subfontIndex
            try:
                pdfmetrics.registerFont(TTFont(font_name, path))
                logger.info(f"Registered font: {font_name} -> {path}")
                return True
            except Exception as e:
                logger.warning(f"Failed to register font {font_name} ({path}): {e}")
                return False
        except Exception as e:
            logger.warning(f"Failed to register font {font_name} ({path}): {e}")
            return False

    def _try_register_family(family: str, normal: str, bold: str) -> None:
        try:
            pdfmetrics.registerFontFamily(
                family,
                normal=normal,
                bold=bold,
                italic=normal,
                boldItalic=bold,
            )
            logger.info(f"Registered font family: {family}")
        except Exception as e:
            logger.warning(f"Failed to register font family {family}: {e}")

    # CJK support (WenQuanYi)
    cjk_candidates = [
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttf',
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttf',
    ]

    cjk_registered = False
    for path in cjk_candidates:
        if not os.path.exists(path):
            continue

        if path.lower().endswith('.ttc'):
            normal_ok = _try_register_ttf('WenQuanYi', path, subfontIndex=0)
            if not normal_ok:
                continue

            # Many TTC files contain multiple faces; try index 1 for bold.
            bold_ok = _try_register_ttf('WenQuanYi-Bold', path, subfontIndex=1)
            if not bold_ok:
                bold_ok = _try_register_ttf('WenQuanYi-Bold', path, subfontIndex=0)
            cjk_registered = True
            break

        normal_ok = _try_register_ttf('WenQuanYi', path)
        if not normal_ok:
            continue

        # Try common bold file naming patterns first.
        bold_ok = False
        for bold_path in (
            path.replace('.ttf', '-Bold.ttf'),
            path.replace('.ttf', 'Bold.ttf'),
        ):
            if _try_register_ttf('WenQuanYi-Bold', bold_path):
                bold_ok = True
                break
        if not bold_ok:
            _try_register_ttf('WenQuanYi-Bold', path)

        cjk_registered = True
        break

    if cjk_registered:
        _try_register_family('WenQuanYi', normal='WenQuanYi', bold='WenQuanYi-Bold')
    else:
        logger.warning("WQY fonts not available, CJK characters may not render properly")

    # DejaVu fallback (good Unicode coverage + real bold variant)
    dejavu_ok = _try_register_ttf('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    dejavu_bold_ok = _try_register_ttf('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
    if dejavu_ok and dejavu_bold_ok:
        _try_register_family('DejaVuSans', normal='DejaVuSans', bold='DejaVuSans-Bold')

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
    FONT_WEIGHT_STYLE_PATTERN = re.compile(r'font-weight\s*:\s*([^;]+)', re.IGNORECASE)
    FONT_SHORTHAND_BOLD_PATTERN = re.compile(r'font\s*:\s*[^;]*\bbold\b', re.IGNORECASE)

    BOLD_WRAPPER_TAGS = BLOCK_TAGS.union({'span', 'font'})

    def __init__(self, bold_classes: Optional[set[str]] = None):
        super().__init__(convert_charrefs=True)
        self.elements: List[Tuple[str, object]] = []
        self.current_text: List[str] = []
        self.current_tag: Optional[str] = None
        self.current_attrs: Dict[str, str] = {}
        self.font_stack: List[bool] = []
        self.bold_stack: List[bool] = []
        self.bold_classes = {c.lower() for c in (bold_classes or set())}

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

        has_bold = False
        if tag in self.BOLD_WRAPPER_TAGS and tag not in {'b', 'strong'}:
            has_bold = self._attrs_indicate_bold(attrs_dict)

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

            if has_bold:
                self.current_text.append('<b>')
            self.bold_stack.append(has_bold)
        elif tag == 'span':
            color = self._extract_color_from_style(attrs_dict.get('style', ''))
            has_font = bool(color)
            if color:
                self.current_text.append(f'<font color="{color}">')
            self.font_stack.append(has_font)

            if has_bold:
                self.current_text.append('<b>')
            self.bold_stack.append(has_bold)
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
        else:
            if tag in self.BOLD_WRAPPER_TAGS and tag not in {'b', 'strong'}:
                if has_bold:
                    self.current_text.append('<b>')
                self.bold_stack.append(has_bold)

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        if tag == 'br':
            self.current_text.append('<br/>')
        elif tag == 'img':
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        tag = tag.lower()

        if tag in self.BOLD_WRAPPER_TAGS and tag not in {'b', 'strong'}:
            if self.bold_stack:
                had_bold = self.bold_stack.pop()
                if had_bold:
                    self.current_text.append('</b>')

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
    def _style_indicates_bold(cls, style: Optional[str]) -> bool:
        if not style:
            return False

        if cls.FONT_SHORTHAND_BOLD_PATTERN.search(style):
            return True

        match = cls.FONT_WEIGHT_STYLE_PATTERN.search(style)
        if not match:
            return False

        value = match.group(1).split('!important')[0].strip().lower()
        if value in {'bold', 'bolder'}:
            return True

        num_match = re.match(r'\s*([0-9]{3})\b', value)
        if num_match:
            try:
                return int(num_match.group(1)) >= 600
            except ValueError:
                return False

        return False

    def _attrs_indicate_bold(self, attrs: Dict[str, str]) -> bool:
        style = attrs.get('style') or ''
        if self._style_indicates_bold(style):
            return True

        class_attr = attrs.get('class') or ''
        class_names = [c.strip().lower() for c in class_attr.split() if c.strip()]
        if not class_names:
            return False

        if any(c in self.bold_classes for c in class_names):
            return True

        # Heuristic: common class names used for bold text in EPUB/CSS.
        for c in class_names:
            if c in {'bold', 'fw-bold', 'font-bold', 'strong'}:
                return True
            if 'bold' in c or 'strong' in c:
                return True

        return False

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
        return value * inch
    if unit == '%':
        return (value / 100.0) * MAX_IMG_WIDTH * inch  # Convert percentage of max width to points
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


def convert_css_classes_to_html(html_content: str) -> str:
    """Convert CSS class formatting to HTML tags for reportlab."""
    # Convert <span class="bold">text</span> to <b>text</b>
    html_content = re.sub(r'<span class="bold">(.*?)</span>', r'<b>\1</b>', html_content, flags=re.DOTALL)
    html_content = re.sub(r'<span class="bold\s+.*?">(.*?)</span>', r'<b>\1</b>', html_content, flags=re.DOTALL)

    # Convert <strong class="...">text</strong> to <b>text</b>
    html_content = re.sub(r'<strong class=".*?">(.*?)</strong>', r'<b>\1</b>', html_content, flags=re.DOTALL)

    # Handle center-aligned paragraphs
    html_content = re.sub(r'<p class=".*?center.*?">', '<p align="center">', html_content, flags=re.IGNORECASE)

    return html_content


_CSS_RULE_PATTERN = re.compile(r'([^{}]+)\{([^{}]+)\}', re.DOTALL)
_CSS_FONT_WEIGHT_PATTERN = re.compile(r'font-weight\s*:\s*([^;]+)', re.IGNORECASE)
_CSS_FONT_SHORTHAND_BOLD_PATTERN = re.compile(r'font\s*:\s*[^;]*\bbold\b', re.IGNORECASE)


def extract_bold_classes_from_css(css_text: str) -> set[str]:
    """Extract CSS class names that apply bold font-weight."""
    bold_classes: set[str] = set()
    if not css_text:
        return bold_classes

    for selector, declarations in _CSS_RULE_PATTERN.findall(css_text):
        if _CSS_FONT_SHORTHAND_BOLD_PATTERN.search(declarations):
            selectors = selector
        else:
            match = _CSS_FONT_WEIGHT_PATTERN.search(declarations)
            if not match:
                continue

            value = match.group(1).split('!important')[0].strip().lower()
            if value not in {'bold', 'bolder'}:
                num_match = re.match(r'\s*([0-9]{3})\b', value)
                if not num_match:
                    continue
                try:
                    if int(num_match.group(1)) < 600:
                        continue
                except ValueError:
                    continue
            selectors = selector

        for selector_part in selectors.split(','):
            part = selector_part.strip()
            if not part:
                continue
            if ' ' in part or any(op in part for op in ('>', '+', '~')):
                continue

            for class_name in re.findall(r'\.([a-zA-Z0-9_-]+)', part):
                bold_classes.add(class_name.lower())

    return bold_classes


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

            # DEBUG: Print chapter 3, 4, 5 HTML to find formatting
            debug_count = 0
            for item in epub_book.spine:
                item_id = item[0] if isinstance(item, tuple) else item
                try:
                    chapter = epub_book.get_item_with_id(item_id)
                    
                    # If not found by ID, try to find by filename (common issue with EpubHtml)
                    if chapter is None:
                        for book_item in epub_book.get_items():
                            if isinstance(book_item, epub.EpubHtml) and book_item.get_name() == item_id:
                                chapter = book_item
                                break
                    
                    if chapter is None or not isinstance(chapter, epub.EpubHtml):
                        continue
                    
                    debug_count += 1
                    content = chapter.get_content().decode('utf-8', errors='ignore')
                    
                    # Convert CSS classes to HTML tags
                    content = convert_css_classes_to_html(content)
                    
                    # Skip first chapter (usually cover), show chapter 3-5
                    if debug_count >= 3 and debug_count <= 5:
                        self.logger.info("=" * 80)
                        self.logger.info(f"CHAPTER {debug_count} HTML (first 3000 chars):")
                        self.logger.info("=" * 80)
                        sample = content[:3000]
                        sample = sample.replace('\n', ' ')
                        # Show with markers for important tags
                        sample = sample.replace('<', '\n<').replace('>', '>\n')
                        self.logger.info(sample)
                        self.logger.info("=" * 80)
                    
                    if debug_count > 5:
                        break
                
                except Exception as e:
                    self.logger.error(f"Debug error: {e}")
                    continue

            epub_images = self._extract_images(epub_book)
            bold_classes = self._extract_bold_classes(epub_book)

            pdf_buffer = io.BytesIO()
            story = []
            title_flowables: List = []
            title_inserted = False

            registered_fonts = set(pdfmetrics.getRegisteredFontNames())
            if 'WenQuanYi' in registered_fonts:
                base_font_name = 'WenQuanYi'
                bold_font_name = 'WenQuanYi-Bold' if 'WenQuanYi-Bold' in registered_fonts else 'WenQuanYi'
                cjk_font_available = True
            elif 'DejaVuSans' in registered_fonts:
                base_font_name = 'DejaVuSans'
                bold_font_name = 'DejaVuSans-Bold' if 'DejaVuSans-Bold' in registered_fonts else 'DejaVuSans'
                cjk_font_available = False
            else:
                base_font_name = 'Helvetica'
                bold_font_name = 'Helvetica-Bold'
                cjk_font_available = False

            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(
                'CJKHeading1',
                fontName=bold_font_name,
                fontSize=18,
                leading=22,
                spaceAfter=12,
                spaceBefore=12,
                textColor=colors.HexColor('#000000'),
                alignment=TA_JUSTIFY,
            ))
            styles.add(ParagraphStyle(
                'CJKHeading2',
                fontName=bold_font_name,
                fontSize=16,
                leading=20,
                spaceAfter=10,
                spaceBefore=10,
                alignment=TA_JUSTIFY,
            ))
            styles.add(ParagraphStyle(
                'CJKHeading3',
                fontName=bold_font_name,
                fontSize=14,
                leading=18,
                spaceAfter=8,
                spaceBefore=8,
                alignment=TA_JUSTIFY,
            ))
            styles.add(ParagraphStyle(
                'CJKBody',
                fontName=base_font_name,
                fontSize=11,
                leading=16,
                spaceAfter=6,
                alignment=TA_JUSTIFY,
                firstLineIndent=0.25 * inch,
            ))
            styles.add(ParagraphStyle(
                'CJKList',
                fontName=base_font_name,
                fontSize=11,
                leading=14,
                leftIndent=20,
                spaceAfter=4,
                alignment=TA_LEFT,
            ))

            if not cjk_font_available:
                self.logger.warning("Using fallback fonts - CJK characters may not render correctly")

            if epub_book.title:
                try:
                    title_text = epub_book.title
                    if isinstance(title_text, (tuple, list)):
                        title_text = title_text[0]
                    if title_text:
                        title_flowables.extend([
                            Paragraph(self._escape_text(str(title_text)[:500]), styles['CJKHeading1']),
                            Spacer(1, 0.3 * inch),
                        ])
                except Exception as e:
                    self.logger.warning(f"Skipped title: {str(e)}")

            self.logger.info("Processing chapters...")
            chapters_processed = 0
            images_added = 0
            center_count = 0
            bold_count = 0
            color_count = 0
            cover_detected = False

            for item in epub_book.spine:
                item_id = item[0] if isinstance(item, tuple) else item

                try:
                    # Try to get chapter by ID first
                    chapter = epub_book.get_item_with_id(item_id)
                    
                    # If not found by ID, try to find by filename (common issue with EpubHtml)
                    if chapter is None:
                        for book_item in epub_book.get_items():
                            if isinstance(book_item, epub.EpubHtml) and book_item.get_name() == item_id:
                                chapter = book_item
                                break
                    
                    if chapter is None or not isinstance(chapter, epub.EpubHtml):
                        continue

                    chapters_processed += 1
                    content = chapter.get_content().decode('utf-8', errors='ignore')

                    content = self._strip_non_content_tags(content)

                    # Convert CSS classes to HTML tags
                    content = convert_css_classes_to_html(content)

                    extractor = FormattingPreservingExtractor(bold_classes=bold_classes)
                    extractor.feed(content)
                    extractor.close()

                    chapter_has_images = any(
                        element and element[0] == 'img'
                        for element in extractor.elements
                    )
                    chapter_has_text = any(
                        element
                        and element[0] != 'img'
                        and isinstance(element[1], str)
                        and re.sub(r'<[^>]+>', '', element[1]).strip()
                        for element in extractor.elements
                    )
                    is_cover_candidate = (
                        chapters_processed == 1
                        and chapter_has_images
                        and not chapter_has_text
                    )

                    if is_cover_candidate and not cover_detected:
                        self.logger.info("Detected image-only first chapter; using it as cover page")
                        cover_added = False
                        for element in extractor.elements:
                            if not element or element[0] != 'img':
                                continue

                            img_data = element[1] if len(element) > 1 else {}
                            if not isinstance(img_data, dict):
                                continue

                            img_src = (img_data.get('src') or '').replace('../', '')
                            img_name = img_src.split('/')[-1]
                            if not img_name:
                                continue

                            for epub_img_name, raw_img in epub_images.items():
                                if img_name not in epub_img_name and not epub_img_name.endswith(img_name):
                                    continue

                                try:
                                    image_buffer = io.BytesIO(raw_img)
                                    full_width, full_height = letter
                                    img = RLImage(
                                        image_buffer,
                                        width=full_width,
                                        height=full_height,
                                    )
                                    story.append(img)
                                    story.append(NextPageTemplate('Content'))
                                    story.append(PageBreak())
                                    images_added += 1
                                    cover_detected = True
                                    cover_added = True
                                    self.logger.info(f"✓ Cover image fills first page: {epub_img_name}")
                                    break
                                except Exception as e:
                                    self.logger.error(f"✗ Failed to add cover image {epub_img_name}: {e}")

                            if cover_added:
                                break

                        if cover_added:
                            continue
                        else:
                            self.logger.warning("Cover chapter detected but no matching image found; falling back to standard layout")

                    if title_flowables and not title_inserted:
                        story.extend(title_flowables)
                        title_inserted = True

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
                                            # Formula: inches = pixels / 96
                                            width_inches = pil_width / 96.0
                                            height_inches = pil_height / 96.0
                                            
                                            self.logger.info(f"Image original: {pil_width}x{pil_height}px = {width_inches:.1f}x{height_inches:.1f}in")
                                        except Exception as e:
                                            self.logger.warning(f"Could not read image dimensions: {e}, using default")
                                            width_inches = DEFAULT_IMAGE_WIDTH
                                            height_inches = DEFAULT_IMAGE_HEIGHT
                                        
                                        # Scale down if exceeds safe limits
                                        if width_inches > MAX_IMG_WIDTH or height_inches > MAX_IMG_HEIGHT:
                                            # Calculate scale factor
                                            scale_w = MAX_IMG_WIDTH / width_inches if width_inches > MAX_IMG_WIDTH else 1.0
                                            scale_h = MAX_IMG_HEIGHT / height_inches if height_inches > MAX_IMG_HEIGHT else 1.0
                                            scale = min(scale_w, scale_h)
                                            
                                            width_inches = width_inches * scale
                                            height_inches = height_inches * scale
                                            self.logger.info(f"Scaled to: {width_inches:.1f}x{height_inches:.1f}in")
                                        
                                        # Convert back to points for reportlab
                                        width = width_inches * inch
                                        height = height_inches * inch
                                        
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

                                alignment = get_alignment(attrs)

                                # Check for formatting in text content
                                if '<b>' in safe_data or '<strong>' in safe_data:
                                    bold_count += 1
                                    self.logger.info(f"✓ Bold text: {safe_data[:50]}")
                                if '<font color' in safe_data:
                                    color_count += 1
                                    self.logger.info(f"✓ Color text: {safe_data[:50]}")

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
                                    if alignment == TA_CENTER:
                                        center_count += 1
                                        self.logger.info(f"✓ Center text: {safe_data[:50]}")
                                    
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

            if title_flowables and not title_inserted:
                story.extend(title_flowables)
                title_inserted = True

            doc = BaseDocTemplate(pdf_buffer, pagesize=letter)

            content_frame = Frame(
                CONTENT_LEFT_MARGIN,
                CONTENT_BOTTOM_MARGIN,
                letter[0] - CONTENT_LEFT_MARGIN - CONTENT_RIGHT_MARGIN,
                letter[1] - CONTENT_TOP_MARGIN - CONTENT_BOTTOM_MARGIN,
                leftPadding=0,
                bottomPadding=0,
                rightPadding=0,
                topPadding=0,
                id='content_frame',
            )

            if cover_detected:
                cover_frame = Frame(
                    0,
                    0,
                    letter[0],
                    letter[1],
                    leftPadding=0,
                    bottomPadding=0,
                    rightPadding=0,
                    topPadding=0,
                    id='cover_frame',
                )
                doc.addPageTemplates([
                    PageTemplate(id='Cover', frames=[cover_frame]),
                    PageTemplate(id='Content', frames=[content_frame]),
                ])
            else:
                doc.addPageTemplates([
                    PageTemplate(id='Content', frames=[content_frame]),
                ])

            self.logger.info(
                f"Summary: {chapters_processed} chapters, {images_added} images, {center_count} centered, {bold_count} bold, {color_count} colored"
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

    @staticmethod
    def _strip_non_content_tags(html: str) -> str:
        if not html:
            return ''
        html = re.sub(r'(?is)<style[^>]*>.*?</style>', '', html)
        html = re.sub(r'(?is)<script[^>]*>.*?</script>', '', html)
        return html

    def _extract_bold_classes(self, book: epub.EpubBook) -> set[str]:
        """Extract CSS class names that imply bold text."""
        bold_classes: set[str] = set()

        for item in book.get_items():
            try:
                item_type = item.get_type()
                media_type = getattr(item, 'media_type', '')

                is_css = item_type == ebooklib.ITEM_STYLE
                if not is_css and isinstance(media_type, str):
                    is_css = media_type.lower().startswith('text/css')

                if is_css:
                    css = item.get_content().decode('utf-8', errors='ignore')
                    bold_classes.update(extract_bold_classes_from_css(css))
                elif isinstance(item, epub.EpubHtml):
                    html = item.get_content().decode('utf-8', errors='ignore')
                    for css in re.findall(r'(?is)<style[^>]*>(.*?)</style>', html):
                        bold_classes.update(extract_bold_classes_from_css(css))
            except Exception:
                continue

        if bold_classes:
            self.logger.info(f"Detected {len(bold_classes)} CSS bold classes")

        return bold_classes

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
