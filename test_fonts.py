#!/usr/bin/env python3
"""
Simple verification script to test font registration
"""

import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simulate the font initialization code
def test_font_registration():
    """Test font registration logic"""
    
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        print("=== Font Registration Test ===")
        
        # First try to register WQY fonts (CJK support)
        wqy_fonts = {
            'WenQuanYi': '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
            'WenQuanYi-Bold': '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
        }
        
        fonts_registered = []
        for name, path in wqy_fonts.items():
            if os.path.exists(path):
                try:
                    pdfmetrics.registerFont(TTFont(name, path))
                    fonts_registered.append(name)
                    logger.info(f"Registered font: {name}")
                except Exception as e:
                    logger.warning(f"Failed to register WQY font {name}: {e}")
            else:
                logger.warning(f"Font file not found: {path}")
        
        # Try .ttf extension if .ttc fails
        if not fonts_registered:
            wqy_ttf = {
                'WenQuanYi': '/usr/share/fonts/truetype/wqy/wqy-microhei.ttf',
                'WenQuanYi-Bold': '/usr/share/fonts/truetype/wqy/wqy-microhei.ttf',
            }
            
            for name, path in wqy_ttf.items():
                if os.path.exists(path):
                    try:
                        pdfmetrics.registerFont(TTFont(name, path))
                        fonts_registered.append(name)
                        logger.info(f"Registered WQY TTF font: {name}")
                    except Exception as e:
                        logger.warning(f"Failed to register WQY TTF font {name}: {e}")
                else:
                    logger.warning(f"TTF font file not found: {path}")
        
        # Check if WQY fonts were registered successfully
        wqy_registered = any(name.startswith('WenQuanYi') for name in pdfmetrics.getRegisteredFontNames())
        
        if wqy_registered:
            # Register font family for proper CJK font usage
            try:
                pdfmetrics.registerFontFamily('WenQuanYi', normal='WenQuanYi', bold='WenQuanYi-Bold', 
                                             italic='WenQuanYi', boldItalic='WenQuanYi-Bold')
                logger.info("Registered WenQuanYi font family")
                print("✓ WenQuanYi CJK fonts successfully registered")
            except Exception as e:
                logger.error(f"Failed to register font family: {e}")
                print("✗ Font family registration failed")
        else:
            logger.warning("WQY fonts not available, CJK characters may not render properly")
            print("⚠ WQY fonts not available - will use fallback fonts")
            
            # Ensure at least DejaVu fonts are available for fallback
            if 'DejaVuSans' not in pdfmetrics.getRegisteredFontNames():
                try:
                    pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
                    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
                    logger.info("Registered DejaVu fallback fonts")
                    print("✓ DejaVu fallback fonts registered")
                except Exception as e:
                    logger.error(f"Failed to register DejaVu fonts: {e}")
                    print("✗ DejaVu fallback registration failed")
        
        # List all registered fonts
        registered_fonts = pdfmetrics.getRegisteredFontNames()
        print(f"\nAll registered fonts: {registered_fonts}")
        
        # Test font availability
        font_names = ['WenQuanYi', 'WenQuanYi-Bold', 'DejaVuSans', 'DejaVuSans-Bold']
        print("\nFont availability test:")
        for font_name in font_names:
            if font_name in registered_fonts:
                print(f"✓ {font_name} - Available")
            else:
                print(f"✗ {font_name} - Not available")
        
        return wqy_registered
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_font_registration()
    print(f"\nResult: {'SUCCESS' if success else 'PARTIAL (using fallbacks)'}")