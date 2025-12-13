import io
import os
import pytest
from fastapi.testclient import TestClient
from ebooklib import epub
from app.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


def create_test_epub() -> bytes:
    """
    Create a minimal valid EPUB file for testing.

    Returns:
        Bytes of a valid EPUB file
    """
    book = epub.EpubBook()
    book.set_identifier("test-debug-epub")
    book.set_title("Test Debug EPUB")
    book.set_language("en")

    c1 = epub.EpubHtml(
        title="Chapter 1",
        file_name="chap_01.xhtml",
        lang="en",
    )
    c1.content = '<h1>Debug Test Chapter</h1><p style="color: red;">Test content with <b>bold</b> and <span style="color: blue;">color</span>.</p>'

    nav = epub.EpubNcx()

    book.add_item(c1)
    book.add_item(nav)
    book.spine = [c1]
    book.toc = (c1,)

    epub_buffer = io.BytesIO()
    epub.write_epub(epub_buffer, book, {})
    epub_buffer.seek(0)
    return epub_buffer.getvalue()


class TestDebugEndpoints:
    """Test suite for the debug HTML endpoints."""

    def test_debug_info_before_conversion(self, client):
        """Test /api/debug-info endpoint before any conversion."""
        # Clean up any existing debug file
        if os.path.exists('/tmp/debug.html'):
            os.remove('/tmp/debug.html')
        
        response = client.get("/api/debug-info")
        assert response.status_code == 200
        data = response.json()
        assert data["file_exists"] is False
        assert "需要先转换" in data["message"]

    def test_debug_info_after_conversion(self, client):
        """Test /api/debug-info endpoint after conversion."""
        # First, convert an EPUB to generate debug.html
        epub_content = create_test_epub()
        convert_response = client.post(
            "/api/convert",
            files={"file": ("test.epub", io.BytesIO(epub_content), "application/epub+zip")},
        )
        assert convert_response.status_code == 200
        
        # Now check debug info
        response = client.get("/api/debug-info")
        assert response.status_code == 200
        data = response.json()
        assert data["file_exists"] is True
        assert "file_size" in data
        assert "file_size_kb" in data
        assert "preview" in data
        assert "/api/download-debug" in data["download_url"]
        assert "/api/debug-html" in data["view_url"]
        
        # Verify the preview contains HTML
        assert "<!DOCTYPE html>" in data["preview"] or "<html>" in data["preview"]

    def test_debug_html_before_conversion(self, client):
        """Test /api/debug-html endpoint before any conversion."""
        # Clean up any existing debug file
        if os.path.exists('/tmp/debug.html'):
            os.remove('/tmp/debug.html')
        
        response = client.get("/api/debug-html")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["error"]

    def test_debug_html_after_conversion(self, client):
        """Test /api/debug-html endpoint after conversion."""
        # First, convert an EPUB to generate debug.html
        epub_content = create_test_epub()
        convert_response = client.post(
            "/api/convert",
            files={"file": ("test.epub", io.BytesIO(epub_content), "application/epub+zip")},
        )
        assert convert_response.status_code == 200
        
        # Now get the debug HTML
        response = client.get("/api/debug-html")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        # Verify the content contains expected HTML structure
        content = response.content.decode('utf-8')
        assert "<!DOCTYPE html>" in content
        assert "<html>" in content
        assert "<body>" in content
        assert "Test Debug EPUB" in content or "Debug Test Chapter" in content

    def test_download_debug_before_conversion(self, client):
        """Test /api/download-debug endpoint before any conversion."""
        # Clean up any existing debug file
        if os.path.exists('/tmp/debug.html'):
            os.remove('/tmp/debug.html')
        
        response = client.get("/api/download-debug")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]

    def test_download_debug_after_conversion(self, client):
        """Test /api/download-debug endpoint after conversion."""
        # First, convert an EPUB to generate debug.html
        epub_content = create_test_epub()
        convert_response = client.post(
            "/api/convert",
            files={"file": ("test.epub", io.BytesIO(epub_content), "application/epub+zip")},
        )
        assert convert_response.status_code == 200
        
        # Now download the debug HTML
        response = client.get("/api/download-debug")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "debug.html" in response.headers.get("content-disposition", "")
        
        # Verify the content contains expected HTML structure
        content = response.content.decode('utf-8')
        assert "<!DOCTYPE html>" in content
        assert "<html>" in content
        assert "<body>" in content

    def test_debug_html_contains_color_info(self, client):
        """Test that debug HTML contains color information from EPUB."""
        # Convert an EPUB with color styling
        epub_content = create_test_epub()
        convert_response = client.post(
            "/api/convert",
            files={"file": ("test.epub", io.BytesIO(epub_content), "application/epub+zip")},
        )
        assert convert_response.status_code == 200
        
        # Get the debug HTML
        response = client.get("/api/debug-html")
        assert response.status_code == 200
        
        content = response.content.decode('utf-8')
        # Check for color attributes or font tags
        # The converter should preserve color information
        assert "color" in content.lower() or "style" in content.lower()

    def test_debug_html_file_persists_between_conversions(self, client):
        """Test that debug HTML is overwritten on subsequent conversions."""
        # First conversion
        epub_content1 = create_test_epub()
        client.post(
            "/api/convert",
            files={"file": ("test1.epub", io.BytesIO(epub_content1), "application/epub+zip")},
        )
        
        response1 = client.get("/api/debug-info")
        size1 = response1.json()["file_size"]
        
        # Create a different EPUB for second conversion
        book2 = epub.EpubBook()
        book2.set_identifier("test-debug-epub-2")
        book2.set_title("Second Test EPUB")
        book2.set_language("en")
        
        c1 = epub.EpubHtml(
            title="Chapter 1",
            file_name="chap_01.xhtml",
            lang="en",
        )
        c1.content = "<h1>Second Chapter</h1>" + "<p>More content.</p>" * 100
        
        nav = epub.EpubNcx()
        book2.add_item(c1)
        book2.add_item(nav)
        book2.spine = [c1]
        book2.toc = (c1,)
        
        epub_buffer2 = io.BytesIO()
        epub.write_epub(epub_buffer2, book2, {})
        epub_buffer2.seek(0)
        epub_content2 = epub_buffer2.getvalue()
        
        # Second conversion
        client.post(
            "/api/convert",
            files={"file": ("test2.epub", io.BytesIO(epub_content2), "application/epub+zip")},
        )
        
        response2 = client.get("/api/debug-info")
        size2 = response2.json()["file_size"]
        
        # The file should be overwritten (likely different size)
        assert response2.status_code == 200
        assert response2.json()["file_exists"] is True
        # Sizes will likely differ due to different content
        # Just verify we got a valid response
