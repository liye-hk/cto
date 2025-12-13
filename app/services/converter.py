import io
import logging
import os
import re
import base64
from typing import Dict, List, Tuple, Optional
from html.parser import HTMLParser
from html import escape
from pathlib import Path

import ebooklib
from ebooklib import epub
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

logger = logging.getLogger(__name__)

ALLOWED_INLINE_TAG_PATTERN = re.compile(
    r'(?i)(</?(?:b|strong|i|em|u|font)(?:\s+[^<>]*?)?>|<br\s*/?>)'
)

# CSS for PDF styling
CSS_STYLES = """
@page {
    margin: 1in;
    size: letter;
}

body {
    font-family: "DejaVu Sans", Arial, sans-serif;
    font-size: 13pt;
    line-height: 1.6;
    text-align: justify;
    color: black;
    margin: 0;
    padding: 0;
}

section.chapter {
    break-after: page;
}

section.chapter:last-child {
    break-after: auto;
}

section.cover-page {
    page-break-after: always;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    margin: 0;
    padding: 0;
}

section.cover-page img {
    width: 8.5in;
    height: 11in;
    object-fit: cover;
    margin: 0;
    padding: 0;
    page-break-inside: avoid;
}

h1 {
    font-size: 20pt;
    font-weight: bold;
    margin: 12pt 0;
    page-break-after: avoid;
    text-indent: 0;
}

h2 {
    font-size: 18pt;
    font-weight: bold;
    margin: 10pt 0;
    page-break-after: avoid;
    text-indent: 0;
}

h3 {
    font-size: 15pt;
    font-weight: bold;
    margin: 8pt 0;
    page-break-after: avoid;
    text-indent: 0;
}

h4, h5, h6 {
    text-indent: 0;
}

p {
    margin: 6pt 0;
    text-indent: 2em;
}

div {
    margin: 6pt 0;
}

li {
    margin: 4pt 0;
    margin-left: 20pt;
    text-indent: 0;
}

/* Comprehensive center alignment rules */
center {
    text-align: center !important;
}

.center, .centered, .text-center, .align-center {
    text-align: center !important;
}

[align="center"] {
    text-align: center !important;
}

p[style*="center"], div[style*="center"], section[style*="center"] {
    text-align: center !important;
}

b, strong {
    font-weight: bold;
}

i, em {
    font-style: italic;
}

u {
    text-decoration: underline;
}

/* Color preservation - ensure styles with color are applied */
span[style*="color"] {
    /* color defined in style attribute */
}

font {
    /* deprecated but should respect color attribute if present */
}

img {
    max-width: 100%;
    height: auto;
    margin: 12pt 0;
    page-break-inside: avoid;
}

/* Chinese/Japanese/Korean font support */
@font-face {
    font-family: "WenQuanYi";
    src: url('/usr/share/fonts/truetype/wqy/wqy-microhei.ttc');
}

.wqy-font {
    font-family: "WenQuanYi", "Noto Sans CJK SC", "Source Han Sans SC", "PingFang SC", "Microsoft YaHei", Arial, sans-serif;
}
"""

# CJK font support - add fallback if available
CJK_FONT_PATHS = [
    '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
    '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
    '/usr/share/fonts/truetype/wqy/wqy-microhei.ttf',
    '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttf',
]

def _get_available_cjk_font() -> Optional[str]:
    """Check if CJK fonts are available and return the path."""
    for font_path in CJK_FONT_PATHS:
        if os.path.exists(font_path):
            logger.info(f"Found CJK font: {font_path}")
            return font_path
    logger.warning("No CJK fonts found, CJK characters may not render properly")
    return None


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
            if src:
                self.elements.append(('img', {
                    'src': src,
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


def _remove_nested_bold_tags(html_str: str) -> str:
    """Remove nested bold tags like <b><b>...</b></b> to avoid duplication.
    
    This handles cases where content is already bold due to existing tags.
    """
    # Pattern to match nested <b> tags: <b>...<b>...</b>...</b>
    # This is a simple approach that removes one layer of nesting
    html_str = re.sub(r'<b>(\s*<b>)', r'\1', html_str)
    html_str = re.sub(r'(</b>)\s*</b>', r'\1', html_str)
    return html_str


def convert_css_classes_to_html(html_content: str) -> str:
    """Convert CSS class formatting to HTML tags for WeasyPrint.
    
    This function converts:
    1. CSS classes indicating bold (bold, fw-bold, font-bold, strong) to <b> tags
    2. CSS classes indicating center alignment (center, centered, text-center) to align="center" attribute
    """
    
    # Pattern to match opening tags with class attributes
    tag_with_class_pattern = re.compile(
        r'<(\w+)([^>]*?\s+class="([^"]*)")([^>]*)>',
        re.IGNORECASE | re.DOTALL
    )
    
    # Process bold classes by wrapping content with <b> tags
    def wrap_bold_content(html_str):
        """Wrap content of bold-class elements with <b> tags."""
        result = []
        i = 0
        while i < len(html_str):
            match = tag_with_class_pattern.search(html_str, i)
            if not match:
                result.append(html_str[i:])
                break
                
            tag, attrs, class_value, remaining_attrs = match.groups()
            class_names = [c.strip().lower() for c in class_value.split() if c.strip()]
            
            # Check for bold classes
            has_bold_class = any(_is_bold_class(c) for c in class_names)
            
            if has_bold_class:
                # Add opening tag (remove bold classes from attribute list)
                remaining_classes = [c for c in class_names if not _is_bold_class(c)]
                
                # Reconstruct opening tag attributes without bold classes
                # attrs includes ' class="value"' so we need to replace it
                if remaining_classes:
                    new_class_attr = f' class="{" ".join(remaining_classes)}"'
                    # Replace the old class attribute with the new one
                    attrs_without_class = re.sub(
                        r'\s+class="[^"]*"',
                        new_class_attr,
                        attrs,
                        flags=re.IGNORECASE,
                        count=1
                    )
                else:
                    # Remove the class attribute entirely
                    attrs_without_class = re.sub(
                        r'\s+class="[^"]*"',
                        '',
                        attrs,
                        flags=re.IGNORECASE,
                        count=1
                    )
                
                result.append(html_str[i:match.start()])
                result.append(f'<{tag}{attrs_without_class}{remaining_attrs}>')
                
                # Find closing tag and wrap content
                closing_tag = f'</{tag}>'
                close_pos = html_str.find(closing_tag, match.end())
                if close_pos != -1:
                    content_between = html_str[match.end():close_pos]
                    
                    # Check if content already has bold tags to avoid nesting
                    has_bold_tag = bool(re.search(r'<\s*b\s*>|<\s*/\s*b\s*>|<\s*strong\s*>|<\s*/\s*strong\s*>', content_between, re.IGNORECASE))
                    
                    if not has_bold_tag:
                        # Only wrap with <b> if content doesn't already have bold tags
                        result.append('<b>')
                        result.append(content_between)
                        result.append('</b>')
                    else:
                        # Content already has bold tags, just add it as-is
                        result.append(content_between)
                    
                    result.append(closing_tag)
                    i = close_pos + len(closing_tag)
                else:
                    # Malformed HTML, just add the match and continue
                    result.append(html_str[match.end():match.end() + 100] + '...')
                    i = match.end() + 100
            else:
                result.append(html_str[i:match.end()])
                i = match.end()
        
        return ''.join(result)
    
    # Process center classes by adding align attribute and style
    def add_center_alignment(html_str):
        """Add align="center" and style="text-align: center" to elements with center classes."""
        def replace_tag(match):
            tag, attrs, class_value, remaining_attrs = match.groups()
            class_names = [c.strip().lower() for c in class_value.split() if c.strip()]
            
            has_center_class = any(_is_center_class(c) for c in class_names)
            
            if has_center_class:
                # Add center alignment with both align attribute and style for maximum compatibility
                if 'align=' in attrs.lower():
                    # Replace existing align attribute
                    attrs = re.sub(r'\s+align="[^"]*"', '', attrs, flags=re.IGNORECASE)
                    attrs = re.sub(r'\s+align=\'[^\']*\'', '', attrs, flags=re.IGNORECASE)
                    attrs = attrs + f' align="center"'
                else:
                    attrs = attrs + f' align="center"'
                
                # Also add style with text-align: center for WeasyPrint
                if 'style=' in attrs.lower():
                    # Update existing style attribute
                    attrs = re.sub(
                        r'style="([^"]*)"',
                        lambda m: f'style="{m.group(1).rstrip(";")}; text-align: center;"',
                        attrs,
                        flags=re.IGNORECASE,
                        count=1
                    )
                else:
                    attrs = attrs + f' style="text-align: center;"'
            
            return f'<{tag}{attrs}{remaining_attrs}>'
        
        return tag_with_class_pattern.sub(replace_tag, html_str)
    
    # Apply transformations
    result = wrap_bold_content(html_content)
    result = add_center_alignment(result)
    
    # Clean up any remaining nested bold tags
    result = _remove_nested_bold_tags(result)
    
    return result


def _is_bold_class(class_name: str) -> bool:
    """Check if a CSS class name indicates bold text."""
    class_name = class_name.lower()
    bold_keywords = ['bold', 'strong', 'fw-bold', 'font-bold', 'weight-bold']
    return any(keyword in class_name for keyword in bold_keywords)


def _is_center_class(class_name: str) -> bool:
    """Check if a CSS class name indicates center alignment."""
    class_name = class_name.lower()
    center_keywords = ['center', 'centered', 'text-center', 'align-center']
    return any(keyword in class_name for keyword in center_keywords)


def extract_bold_classes_from_css(css_content: str) -> set[str]:
    """Extract CSS class names that imply bold text from CSS content."""
    bold_classes = set()
    
    # Pattern to match class selectors with font-weight: bold
    bold_pattern = re.compile(r'\.([\w-]+)[^{]*\{[^}]*font-weight\s*:\s*bold', re.IGNORECASE)
    
    for match in bold_pattern.finditer(css_content):
        class_name = match.group(1)
        bold_classes.add(class_name)
    
    return bold_classes


class ConversionError(Exception):
    """Custom exception for conversion errors."""
    pass


class EPUBToPDFConverter:
    """Convert EPUB files to PDF using WeasyPrint."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.cjk_font_path = _get_available_cjk_font()

    def convert(self, epub_content) -> bytes:
        """Convert EPUB content to PDF.
        
        Args:
            epub_content: Either bytes or an io.BytesIO object containing EPUB data.
        """
        try:
            self.logger.info("Starting EPUB to PDF conversion with WeasyPrint")
            
            # Convert bytes to BytesIO if needed
            if isinstance(epub_content, bytes):
                epub_buffer = io.BytesIO(epub_content)
            else:
                epub_buffer = epub_content
            
            # Read EPUB
            epub_book = epub.read_epub(epub_buffer)
            logger.info(f"Read EPUB: {epub_book.title}")
            
            # Build HTML document
            html_content = self._build_html_document(epub_book)
            
            # Log first 500 characters for debugging
            self.logger.debug(f"Generated HTML (first 500 chars):\n{html_content[:500]}")
            
            # Extract CSS from EPUB
            epub_css = self._extract_all_css(epub_book)
            
            # Add CJK font support if available
            css_content = CSS_STYLES
            if epub_css:
                # Prepend EPUB CSS so our base styles override if needed
                css_content = epub_css + "\n" + css_content
            
            if self.cjk_font_path:
                # Embed the CJK font in CSS
                font_dir = os.path.dirname(self.cjk_font_path)
                css_content += f"""
@font-face {{
    font-family: "WenQuanYi";
    src: url('file://{self.cjk_font_path}');
}}
"""
            
            # Create CSS object
            css = CSS(string=css_content)
            
            # Create HTML object and render to PDF with FontConfiguration
            font_config = FontConfiguration()
            html_doc = HTML(string=html_content)
            pdf_bytes = html_doc.write_pdf(stylesheets=[css], font_config=font_config)
            
            self.logger.info("EPUB to PDF conversion completed successfully")
            return pdf_bytes
            
        except Exception as e:
            self.logger.error(f"Conversion failed: {str(e)}")
            raise ConversionError(f"Failed to convert EPUB to PDF: {str(e)}")

    def _build_html_document(self, epub_book: epub.EpubBook) -> str:
        """Build complete HTML document from EPUB book.
        
        This is the main helper method for building the HTML document from an EPUB.
        It's exposed to allow tests to inspect the generated HTML structure.
        
        Process:
        1. Parse EPUB metadata and spine items
        2. Detect cover image via metadata or first image-only chapter
        3. Collect HTML content and binary resources
        4. Generate full HTML document with proper CSS-based pagination
        """
        html_parts = ['<!DOCTYPE html>', '<html><head>', '<meta charset="utf-8">', '<title>']
        
        # Add title
        if epub_book.title:
            title_text = epub_book.title
            if isinstance(title_text, (tuple, list)):
                title_text = title_text[0]
            html_parts.append(escape(str(title_text)[:500]))
        
        html_parts.extend(['</title>', '</head>', '<body>'])
        
        # Extract images and bold classes early so we can detect cover
        epub_images = self._extract_images(epub_book)
        bold_classes = self._extract_bold_classes(epub_book)
        
        # Detect and add cover page if available
        cover_image_data = self._detect_cover_image(epub_book, epub_images)
        if cover_image_data:
            img_b64 = base64.b64encode(cover_image_data).decode('utf-8')
            html_parts.append(
                f'<section class="cover-page"><img src="data:image/png;base64,{img_b64}" alt="Cover" /></section>'
            )
        
        # Add title as heading
        if epub_book.title:
            title_text = epub_book.title
            if isinstance(title_text, (tuple, list)):
                title_text = title_text[0]
            if title_text:
                html_parts.append(f'<h1>{escape(str(title_text)[:500])}</h1>')
        
        self.logger.info("Processing chapters...")
        chapters_processed = 0
        
        # Process spine items
        for item in epub_book.spine:
            item_id = item[0] if isinstance(item, tuple) else item

            try:
                # Try to get chapter by ID first
                chapter = epub_book.get_item_with_id(item_id)
                
                # If not found by ID, try to find by filename
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

                # Start chapter section for proper pagination
                html_parts.append('<section class="chapter">')
                
                # Process elements
                for element in extractor.elements:
                    if not element:
                        continue

                    element_type = element[0]
                    
                    if element_type == 'img':
                        img_data = element[1]
                        src = img_data.get('src', '')
                        
                        # Try to resolve image from EPUB
                        resolved_img = self._resolve_image_path(src, epub_images)
                        if resolved_img:
                            # Embed image as base64
                            img_b64 = base64.b64encode(resolved_img).decode('utf-8')
                            html_parts.append(f'<img src="data:image/png;base64,{img_b64}" alt="Image" />')
                        else:
                            html_parts.append(f'<p><em>Image: {escape(src)}</em></p>')
                    
                    elif element_type in ['h1', 'h2', 'h3']:
                        text = self._escape_text(element[1])
                        attrs = element[2] if len(element) > 2 else {}
                        # Build attributes string
                        attrs_str = ''
                        if attrs:
                            for key, value in attrs.items():
                                attrs_str += f' {key}="{value}"'
                        html_parts.append(f'<{element_type}{attrs_str}>{text}</{element_type}>')
                    
                    elif element_type == 'center':
                        text = self._escape_text(element[1])
                        html_parts.append(f'<div align="center">{text}</div>')
                    
                    elif element_type in ['p', 'div', 'li']:
                        text = self._escape_text(element[1])
                        attrs = element[2] if len(element) > 2 else {}
                        # Build attributes string
                        attrs_str = ''
                        if attrs:
                            for key, value in attrs.items():
                                attrs_str += f' {key}="{value}"'
                        html_parts.append(f'<{element_type}{attrs_str}>{text}</{element_type}>')
                
                # Close chapter section
                html_parts.append('</section>')
            
            except Exception as e:
                self.logger.warning(f"Skipping chapter {item_id}: {str(e)}")
                continue

        html_parts.extend(['</body>', '</html>'])
        return ''.join(html_parts)
    
    def _escape_text(self, text: str) -> str:
        """Escape text while preserving formatting tags.
        
        This method escapes HTML special characters but preserves allowed formatting tags
        like <b>, <strong>, <i>, <em>, <u>, <font>, and <br>.
        """
        # First, escape all text
        escaped = escape(text)
        
        # Then, unescape allowed tags and characters
        # Pattern to match allowed inline formatting tags
        escaped = escaped.replace('&lt;b&gt;', '<b>')
        escaped = escaped.replace('&lt;/b&gt;', '</b>')
        escaped = escaped.replace('&lt;strong&gt;', '<strong>')
        escaped = escaped.replace('&lt;/strong&gt;', '</strong>')
        escaped = escaped.replace('&lt;i&gt;', '<i>')
        escaped = escaped.replace('&lt;/i&gt;', '</i>')
        escaped = escaped.replace('&lt;em&gt;', '<em>')
        escaped = escaped.replace('&lt;/em&gt;', '</em>')
        escaped = escaped.replace('&lt;u&gt;', '<u>')
        escaped = escaped.replace('&lt;/u&gt;', '</u>')
        escaped = escaped.replace('&lt;br&gt;', '<br>')
        escaped = escaped.replace('&lt;br/&gt;', '<br/>')
        escaped = escaped.replace('&lt;br /&gt;', '<br />')
        
        # Handle font tags with color attributes - convert to span with style
        escaped = re.sub(
            r'&lt;font color=&quot;([^&]*?)&quot;&gt;',
            r'<span style="color: \1;">',
            escaped
        )
        escaped = escaped.replace('&lt;/font&gt;', '</span>')
        
        return escaped

    def _detect_cover_image(self, book: epub.EpubBook, epub_images: Dict[str, bytes]) -> Optional[bytes]:
        """Detect cover image from EPUB metadata or first image-only chapter.
        
        Returns:
            Image bytes if found, None otherwise.
        """
        # Try to find cover from metadata
        try:
            # Check for cover in metadata
            cover_id = None
            if hasattr(book, 'metadata') and book.metadata:
                # Look for cover image reference in metadata
                for key in book.metadata.get('cover', []):
                    if isinstance(key, str):
                        cover_id = key
                        break
            
            if cover_id:
                try:
                    item = book.get_item_with_id(cover_id)
                    if item:
                        return item.get_content()
                except (AttributeError, KeyError):
                    pass
            
            # Try to get cover by common names
            for item in book.get_items():
                if isinstance(item, epub.EpubImage):
                    name = item.get_name().lower()
                    if 'cover' in name:
                        return item.get_content()
        except Exception:
            pass
        
        # Try to detect from first image-only chapter
        try:
            for item in book.spine:
                item_id = item[0] if isinstance(item, tuple) else item
                chapter = book.get_item_with_id(item_id)
                
                if chapter is None:
                    for book_item in book.get_items():
                        if isinstance(book_item, epub.EpubHtml) and book_item.get_name() == item_id:
                            chapter = book_item
                            break
                
                if chapter and isinstance(chapter, epub.EpubHtml):
                    content = chapter.get_content().decode('utf-8', errors='ignore')
                    # Check if this is an image-only chapter
                    if '<img' in content.lower() and len(content) < 1000:
                        # Try to extract image
                        img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE)
                        if img_match:
                            src = img_match.group(1)
                            img_data = self._resolve_image_path(src, epub_images)
                            if img_data:
                                return img_data
        except Exception:
            pass
        
        return None
    
    def _extract_images(self, book: epub.EpubBook) -> Dict[str, bytes]:
        """Extract all images from EPUB."""
        images = {}
        
        for item in book.get_items():
            try:
                item_type = item.get_type()
                is_image = False

                # Check if it's an image based on type or content
                try:
                    if hasattr(ebooklib, 'ITEM_IMAGE') and item_type == ebooklib.ITEM_IMAGE:
                        is_image = True
                except (AttributeError, TypeError):
                    pass

                if not is_image and isinstance(item_type, str):
                    is_image = 'image' in item_type.lower()

                if not is_image:
                    media_type = getattr(item, 'media_type', '')
                    if isinstance(media_type, str):
                        is_image = 'image' in media_type.lower()

                if is_image:
                    name = item.get_name()
                    images[name] = item.get_content()
            except Exception:
                continue

        return images

    def _resolve_image_path(self, src: str, epub_images: Dict[str, bytes]) -> Optional[bytes]:
        """Resolve image source to content."""
        if not src:
            return None
            
        # Try direct match first
        if src in epub_images:
            return epub_images[src]
            
        # Try with different path components
        src_parts = src.split('/')
        for i in range(len(src_parts)):
            candidate = '/'.join(src_parts[i:])
            if candidate in epub_images:
                return epub_images[candidate]
                
        # Try just the filename
        filename = src_parts[-1]
        for img_name in epub_images:
            if img_name.endswith(filename):
                return epub_images[img_name]
        
        return None

    @staticmethod
    def _strip_non_content_tags(html: str) -> str:
        """Remove script and style tags from HTML."""
        if not html:
            return ''
        html = re.sub(r'(?is)<style[^>]*>.*?</style>', '', html)
        html = re.sub(r'(?is)<script[^>]*>.*?</script>', '', html)
        return html

    def _extract_bold_classes(self, book: epub.EpubBook) -> set[str]:
        """Extract CSS class names that imply bold text."""
        bold_classes = set()

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

        return bold_classes

    def _extract_all_css(self, book: epub.EpubBook) -> str:
        """Extract all CSS from EPUB book files.
        
        This extracts CSS from both standalone CSS files and inline style tags
        in HTML chapters. All color definitions and other styling rules are preserved.
        """
        css_parts = []
        
        for item in book.get_items():
            try:
                item_type = item.get_type()
                media_type = getattr(item, 'media_type', '')
                
                # Check if it's a CSS file
                is_css = item_type == ebooklib.ITEM_STYLE
                if not is_css and isinstance(media_type, str):
                    is_css = media_type.lower().startswith('text/css')
                
                if is_css:
                    try:
                        css = item.get_content().decode('utf-8', errors='ignore')
                        if css.strip():
                            css_parts.append(css)
                    except (AttributeError, ValueError):
                        continue
                elif isinstance(item, epub.EpubHtml):
                    # Extract inline style tags from HTML chapters
                    try:
                        html = item.get_content().decode('utf-8', errors='ignore')
                        # Find all <style> tags and extract their content
                        style_blocks = re.findall(r'(?is)<style[^>]*>(.*?)</style>', html)
                        for style_block in style_blocks:
                            if style_block.strip():
                                css_parts.append(style_block)
                    except (AttributeError, ValueError):
                        continue
            except Exception:
                continue
        
        # Combine all CSS
        combined_css = '\n'.join(css_parts)
        
        # Clean up unnecessary parts and warnings
        # Remove @import and @namespace that might cause issues
        combined_css = re.sub(r'@import\s+[^;]+;', '', combined_css)
        combined_css = re.sub(r'@namespace\s+[^;]+;', '', combined_css)
        
        return combined_css if combined_css.strip() else ""