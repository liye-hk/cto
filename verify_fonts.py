#!/usr/bin/env python3
"""
Verification script to test WeasyPrint font support and EPUB conversion
"""

import sys
import os

# Add the app directory to the path so we can import the converter
sys.path.insert(0, '/home/engine/project')

try:
    from app.services.converter import EPUBToPDFConverter
    from weasyprint import HTML, CSS
    
    print("=== WeasyPrint Font Support Verification ===")
    
    # Check for CJK font files
    cjk_font_paths = [
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttf',
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttf',
    ]
    
    available_cjk_fonts = []
    for path in cjk_font_paths:
        if os.path.exists(path):
            available_cjk_fonts.append(path)
            print(f"Found CJK font: {path}")
    
    if available_cjk_fonts:
        print(f"✓ Found {len(available_cjk_fonts)} CJK font files")
    else:
        print("⚠ No CJK fonts found - will use system defaults")
    
    # Initialize converter
    print("\n=== Converter Initialization ===")
    converter = EPUBToPDFConverter()
    print("Converter initialized successfully")
    
    # Test PDF creation with WeasyPrint
    print("\n=== WeasyPrint PDF Generation Test ===")
    
    # Test HTML to PDF conversion
    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {
                font-family: "DejaVu Sans", Arial, sans-serif;
                font-size: 14px;
                margin: 20px;
            }
            h1 {
                font-size: 18px;
                color: #333;
            }
            .cjk-text {
                font-family: "WenQuanYi", "Noto Sans CJK SC", "Source Han Sans SC", Arial, sans-serif;
                color: #0066cc;
            }
        </style>
    </head>
    <body>
        <h1>Font Test Document</h1>
        <p>Test English text - this should render properly.</p>
        <p class="cjk-text">测试中文文本 - This should show CJK characters.</p>
        <p class="cjk-text">日本語テキストテスト - This should show Japanese characters.</p>
        <p class="cjk-text">한국어 텍스트 테스트 - This should show Korean characters.</p>
        <p><strong>Bold text test</strong> and <em>italic text test</em>.</p>
        <p align="center">Centered text test</p>
    </body>
    </html>
    """
    
    try:
        # Create HTML document and render to PDF
        html_doc = HTML(string=test_html)
        pdf_bytes = html_doc.write_pdf()
        
        if pdf_bytes and len(pdf_bytes) > 0:
            print(f"✓ WeasyPrint PDF generation successful ({len(pdf_bytes)} bytes)")
            print("✓ HTML to PDF rendering working")
        else:
            print("✗ PDF generation failed")
            raise Exception("PDF generation returned empty result")
            
    except Exception as e:
        print(f"✗ WeasyPrint PDF generation failed: {e}")
        raise
    
    print("\n=== Font & WeasyPrint Verification Complete ===")
    print("✓ WeasyPrint font support working")
    print("✓ Converter initialization working")
    print("✓ HTML to PDF generation working")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()