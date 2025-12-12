#!/usr/bin/env python3
"""
Simple verification script to test WeasyPrint font support
"""

import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_font_support():
    """Test font support for WeasyPrint"""
    
    try:
        from weasyprint import HTML, CSS
        
        print("=== WeasyPrint Font Support Test ===")
        
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
                logger.info(f"Found CJK font: {path}")
        
        if available_cjk_fonts:
            print(f"✓ Found {len(available_cjk_fonts)} CJK font files")
            cjk_font_path = available_cjk_fonts[0]
        else:
            print("⚠ No CJK fonts found - will use system defaults")
            cjk_font_path = None
        
        # Test basic HTML rendering
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {
                    font-family: "DejaVu Sans", Arial, sans-serif;
                    font-size: 14px;
                }
                @font-face {
                    font-family: "WenQuanYi";
                    src: url('file://""" + (cjk_font_path or '') + """');
                }
                .cjk-text {
                    font-family: "WenQuanYi", "Noto Sans CJK SC", "Source Han Sans SC", Arial, sans-serif;
                }
            </style>
        </head>
        <body>
            <h1>Font Test</h1>
            <p>English text test</p>
            <p class="cjk-text">中文文本测试</p>
            <p class="cjk-text">日本語テキストテスト</p>
            <p class="cjk-text">한국어 텍스트 테스트</p>
        </body>
        </html>
        """
        
        try:
            # Create a simple PDF to test rendering
            html_doc = HTML(string=test_html)
            pdf_bytes = html_doc.write_pdf()
            
            if pdf_bytes and len(pdf_bytes) > 0:
                print("✓ Basic HTML to PDF rendering successful")
                print(f"✓ Generated PDF size: {len(pdf_bytes)} bytes")
            else:
                print("✗ PDF generation failed")
                return False
                
        except Exception as e:
            print(f"✗ HTML rendering failed: {e}")
            return False
        
        # Test CSS font face
        try:
            css_content = """
            @font-face {
                font-family: "TestFont";
                src: url('file:///usr/share/fonts/truetype/dejavu/DejaVuSans.ttf');
            }
            .test-font {
                font-family: "TestFont", Arial, sans-serif;
            }
            """
            
            css = CSS(string=css_content)
            print("✓ CSS @font-face parsing successful")
            
        except Exception as e:
            print(f"⚠ CSS font face test failed: {e}")
        
        print("\n✓ WeasyPrint font support test completed")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_font_support()
    print(f"\nResult: {'SUCCESS' if success else 'FAILED'}")