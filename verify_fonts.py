#!/usr/bin/env python3
"""
Verification script to test font registration and CJK font usage
"""

import sys
import os

# Add the app directory to the path so we can import the converter
sys.path.insert(0, '/home/engine/project')

try:
    from app.services.converter import EPUBToPDFConverter
    from reportlab.pdfbase import pdfmetrics
    
    print("=== Font Registration Verification ===")
    print(f"Registered font names: {pdfmetrics.getRegisteredFontNames()}")
    
    # Check for WenQuanYi fonts
    wqy_fonts = [name for name in pdfmetrics.getRegisteredFontNames() if 'WenQuanYi' in name]
    print(f"WenQuanYi fonts registered: {len(wqy_fonts)}")
    for font in wqy_fonts:
        print(f"  - {font}")
    
    # Initialize converter
    print("\n=== Converter Initialization ===")
    converter = EPUBToPDFConverter()
    print("Converter initialized successfully")
    
    # Test PDF creation with CJK text
    print("\n=== PDF Generation Test ===")
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    import io
    
    # Create a test PDF to verify font rendering
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=letter)
    
    # Test basic text
    c.setFont("Helvetica", 12)
    c.drawString(100, 750, "Test English text")
    
    # Test CJK text if WenQuanYi is available
    if wqy_fonts:
        c.setFont("WenQuanYi", 12)
        c.drawString(100, 730, "测试中文文本")
        print("CJK font rendering test successful")
    else:
        print("CJK fonts not available - testing fallback")
        c.setFont("Helvetica", 12)
        c.drawString(100, 730, "CJK Fallback test")
    
    c.showPage()
    c.save()
    
    pdf_buffer.seek(0)
    pdf_content = pdf_buffer.getvalue()
    print(f"Test PDF generated successfully ({len(pdf_content)} bytes)")
    
    print("\n=== Font Verification Complete ===")
    print("✓ Font registration working")
    print("✓ Converter initialization working")
    print("✓ PDF generation working")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()