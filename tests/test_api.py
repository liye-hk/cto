import io
import pytest
from fastapi.testclient import TestClient
from ebooklib import epub
from app.main import app
from app.core.config import settings


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
    book.set_identifier("test-api-epub")
    book.set_title("Test API EPUB")
    book.set_language("en")

    c1 = epub.EpubHtml(
        title="Chapter 1",
        file_name="chap_01.xhtml",
        lang="en",
    )
    c1.content = "<h1>API Test Chapter</h1><p>Test content for API endpoint.</p>"

    nav = epub.EpubNcx()

    book.add_item(c1)
    book.add_item(nav)
    book.spine = [c1]
    book.toc = (c1,)

    epub_buffer = io.BytesIO()
    epub.write_epub(epub_buffer, book, {})
    epub_buffer.seek(0)
    return epub_buffer.getvalue()


class TestConvertEndpoint:
    """Test suite for the /api/convert endpoint."""

    def test_home_page(self, client):
        """Test home page returns HTML."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"EPUB to PDF Converter" in response.content
        assert b"dropZone" in response.content

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_static_files_js(self, client):
        """Test static JavaScript file is accessible."""
        response = client.get("/static/js/app.js")
        assert response.status_code == 200
        assert b"selectedFile" in response.content

    def test_static_files_css(self, client):
        """Test static CSS file is accessible."""
        response = client.get("/static/css/styles.css")
        assert response.status_code == 200
        assert b"drop-zone" in response.content

    def test_convert_valid_epub(self, client):
        """Test converting a valid EPUB file."""
        epub_content = create_test_epub()
        response = client.post(
            "/api/convert",
            files={"file": ("test.epub", io.BytesIO(epub_content), "application/epub+zip")},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers.get("content-disposition", "")
        assert "test.pdf" in response.headers.get("content-disposition", "")
        # Check PDF signature
        assert response.content.startswith(b"%PDF")

    def test_convert_with_application_zip_mime_type(self, client):
        """Test converting EPUB with application/zip MIME type."""
        epub_content = create_test_epub()
        response = client.post(
            "/api/convert",
            files={"file": ("test.epub", io.BytesIO(epub_content), "application/zip")},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

    def test_convert_invalid_extension(self, client):
        """Test conversion with invalid file extension."""
        epub_content = b"dummy content"
        response = client.post(
            "/api/convert",
            files={"file": ("test.pdf", io.BytesIO(epub_content), "application/pdf")},
        )

        assert response.status_code == 400
        assert "Invalid file extension" in response.json()["error"]

    def test_convert_invalid_mime_type(self, client):
        """Test conversion with invalid MIME type."""
        epub_content = create_test_epub()
        response = client.post(
            "/api/convert",
            files={"file": ("test.epub", io.BytesIO(epub_content), "text/plain")},
        )

        # Should still succeed because extension is valid
        assert response.status_code == 200

    def test_convert_invalid_epub_content(self, client):
        """Test conversion with invalid EPUB content."""
        response = client.post(
            "/api/convert",
            files={"file": ("test.epub", io.BytesIO(b"not a valid epub"), "application/epub+zip")},
        )

        assert response.status_code == 400
        assert "Conversion error" in response.json()["error"]

    def test_convert_file_too_large(self, client):
        """Test conversion with file exceeding size limit."""
        # Create a file larger than max_upload_size_mb
        max_size = settings.max_upload_size_mb * 1024 * 1024
        large_content = b"x" * (max_size + 1)

        response = client.post(
            "/api/convert",
            files={"file": ("large.epub", io.BytesIO(large_content), "application/epub+zip")},
        )

        assert response.status_code == 413
        assert "exceeds maximum allowed size" in response.json()["error"]

    def test_convert_no_file_provided(self, client):
        """Test conversion without providing a file."""
        response = client.post("/api/convert")

        assert response.status_code == 422  # Unprocessable Entity

    def test_convert_output_filename(self, client):
        """Test that output filename is correctly set."""
        epub_content = create_test_epub()
        response = client.post(
            "/api/convert",
            files={"file": ("my_book.epub", io.BytesIO(epub_content), "application/epub+zip")},
        )

        assert response.status_code == 200
        assert "my_book.pdf" in response.headers.get("content-disposition", "")

    def test_convert_pdf_size_reasonable(self, client):
        """Test that generated PDF has reasonable size."""
        epub_content = create_test_epub()
        response = client.post(
            "/api/convert",
            files={"file": ("test.epub", io.BytesIO(epub_content), "application/epub+zip")},
        )

        assert response.status_code == 200
        # PDF should be at least a few KB but not unreasonably large
        assert 1000 < len(response.content) < 1024 * 1024  # Between 1KB and 1MB
