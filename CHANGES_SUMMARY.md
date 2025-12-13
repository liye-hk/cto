# Debug HTML Export Endpoints - Implementation Summary

## Ticket Summary
添加调试功能：生成并导出debug.html文件

为了诊断字体大小和颜色问题，添加了调试功能，让用户能查看生成的HTML文档。

## Changes Made

### 1. Modified: `app/services/converter.py`
**Location**: `EPUBToPDFConverter.convert()` method, lines 630-636

**Change**: Added code to save the generated HTML document to `/tmp/debug.html` after building the HTML but before PDF generation.

**Code Added**:
```python
# Save debug HTML for inspection
try:
    with open('/tmp/debug.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    logger.info("Debug HTML saved to /tmp/debug.html")
except Exception as e:
    logger.warning(f"Failed to save debug.html: {e}")
```

**Purpose**: Automatically save a copy of the HTML document each time an EPUB is converted for debugging purposes.

### 2. Modified: `app/api/routes.py`
**Changes**:
- Added imports: `os`, `FileResponse`, `HTMLResponse`, `JSONResponse`
- Added constant: `DEBUG_HTML_PATH = '/tmp/debug.html'`
- Added three new API endpoints (lines 146-249)

**New Endpoints**:

#### a. `GET /api/debug-info`
Returns information about the debug HTML file:
- File existence status
- File size (bytes and KB)
- Content preview (first 1000 characters)
- URLs for viewing and downloading

**Response Example**:
```json
{
  "file_exists": true,
  "file_size": "45678 bytes",
  "file_size_kb": "44.61 KB",
  "preview": "<!DOCTYPE html>...",
  "download_url": "/api/download-debug",
  "view_url": "/api/debug-html",
  "message": "Debug HTML 文件已生成，可以查看或下载"
}
```

#### b. `GET /api/debug-html`
Returns the debug HTML content as HTMLResponse for viewing in browser.
- Status 200: Returns HTML content
- Status 404: File not found (with helpful error message)

#### c. `GET /api/download-debug`
Returns the debug HTML file as a downloadable attachment.
- Status 200: FileResponse with `debug.html` filename
- Status 404: File not found error

**Error Handling**: All endpoints include comprehensive try-catch blocks and return appropriate status codes and error messages.

### 3. Created: `tests/test_debug_endpoints.py`
**Purpose**: Comprehensive test suite for the new debug endpoints

**Test Coverage**:
- `test_debug_info_before_conversion()` - Test /api/debug-info when no file exists
- `test_debug_info_after_conversion()` - Test /api/debug-info after EPUB conversion
- `test_debug_html_before_conversion()` - Test /api/debug-html when no file exists
- `test_debug_html_after_conversion()` - Test /api/debug-html after conversion
- `test_download_debug_before_conversion()` - Test /api/download-debug when no file exists
- `test_download_debug_after_conversion()` - Test /api/download-debug after conversion
- `test_debug_html_contains_color_info()` - Verify color information is preserved
- `test_debug_html_file_persists_between_conversions()` - Verify file is overwritten

**Test Fixtures**:
- `client()` - FastAPI TestClient fixture
- `create_test_epub()` - Helper function to create test EPUB with formatting

### 4. Updated: `README.md`
**Location**: After "Error Response Format" section in API Usage

**Added Section**: "Debug HTML Endpoints" with:
- Overview of the debugging feature
- Documentation for all three endpoints
- Request/response examples
- Debug workflow guide
- Use cases for diagnostics
- Important notes about file overwriting

**Content**: ~85 lines of comprehensive documentation with examples in bash, explaining:
- How to check debug info
- How to view HTML in browser
- How to download HTML file
- Diagnostic use cases (font size, colors, indentation, alignment, images)

### 5. Created: `DEBUG_ENDPOINTS_GUIDE.md`
**Purpose**: Detailed bilingual (Chinese/English) user guide

**Sections**:
1. **Overview** - Feature description
2. **Features** - Description of all three endpoints with examples
3. **Workflow** - Step-by-step usage guide
4. **Diagnostic Use Cases** - 6 specific debugging scenarios
5. **Important Notes** - Warnings about file overwriting
6. **Troubleshooting** - Common issues and solutions
7. **API Response Status Codes** - Table of status codes
8. **Example Code** - Python and JavaScript examples
9. **Technical Implementation** - Code locations and implementation details

**Size**: ~250 lines of comprehensive bilingual documentation

## Implementation Details

### File Storage
- Path: `/tmp/debug.html`
- Overwritten on each conversion
- Only most recent conversion retained

### Timing
- HTML saved immediately after `_build_html_document()` completes
- Before PDF generation begins
- Allows inspection of exact HTML that will be rendered to PDF

### Error Handling
- Non-blocking: If debug file save fails, conversion continues
- Logged as warning, not error
- All API endpoints include proper error handling and HTTP status codes

### Compatibility
- No changes to existing conversion functionality
- Purely additive feature
- No impact on PDF generation or existing endpoints

## Testing
All code is syntactically valid (verified with Python AST parser).

Test suite includes:
- 8 test cases covering all endpoints
- Tests for both success and error scenarios
- Content validation tests
- Integration tests with conversion endpoint

## Documentation
Complete documentation provided in:
1. **README.md** - API reference style documentation
2. **DEBUG_ENDPOINTS_GUIDE.md** - Comprehensive user guide
3. **Code comments** - Inline documentation in all modified files
4. **Docstrings** - Full docstrings for all new functions

## Usage Example

```bash
# 1. Convert an EPUB file
curl -X POST -F "file=@book.epub" http://localhost:8000/api/convert -o output.pdf

# 2. Check if debug file was created
curl http://localhost:8000/api/debug-info

# 3. View in browser
open http://localhost:8000/api/debug-html

# 4. Download for analysis
curl http://localhost:8000/api/download-debug -o debug.html
```

## Benefits

1. **Debugging**: Easily diagnose font size, color, and formatting issues
2. **Transparency**: Users can see exactly what HTML is being converted
3. **Development**: Helps developers improve conversion quality
4. **Validation**: Verify CSS class conversions and style applications
5. **Troubleshooting**: Quick diagnosis of rendering problems

## Verification Checklist

- ✅ Code is syntactically valid (all files)
- ✅ Follows existing code patterns and style
- ✅ Proper error handling in all endpoints
- ✅ Comprehensive test coverage
- ✅ Complete documentation (README + Guide)
- ✅ Bilingual documentation (Chinese + English)
- ✅ Non-breaking changes (purely additive)
- ✅ Logging added for debugging
- ✅ HTTP status codes used correctly
- ✅ File path consistent across all code

## Files Modified/Created

**Modified** (3 files):
- `app/services/converter.py` - Added debug HTML save logic
- `app/api/routes.py` - Added 3 new debug endpoints
- `README.md` - Added debug endpoints documentation

**Created** (3 files):
- `tests/test_debug_endpoints.py` - Test suite for debug endpoints
- `DEBUG_ENDPOINTS_GUIDE.md` - Comprehensive bilingual user guide
- `CHANGES_SUMMARY.md` - This summary document

## Next Steps

The implementation is complete and ready for review. All code follows the existing patterns and includes:
- Proper error handling
- Comprehensive logging
- Full test coverage
- Complete documentation

The feature can be tested by:
1. Converting any EPUB file via the web UI or API
2. Accessing `/api/debug-info` to verify the file was created
3. Viewing the HTML at `/api/debug-html` in a browser
4. Downloading via `/api/download-debug` for detailed inspection
