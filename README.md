# EPUB to PDF Converter API

A FastAPI service that converts EPUB files to PDF format with robust error handling, file validation, and streaming responses.

## Features

- **EPUB to PDF Conversion**: Convert EPUB files to PDF using ebooklib and reportlab
- **File Validation**: 
  - MIME type validation (application/epub+zip, application/zip)
  - File extension validation (.epub)
  - Configurable file size limits
- **Streaming Responses**: PDF files are streamed back with proper headers and attachment filename
- **Error Handling**: Comprehensive error handling with meaningful JSON error responses
- **Logging**: Built-in logging for debugging and monitoring
- **Unit Tests**: Full test coverage for converter service and API endpoints

## Setup

### Installation

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -e ".[dev]"
```

Or for production:
```bash
pip install -r requirements.txt
```

### Configuration

Configuration can be set via environment variables in a `.env` file:

```env
APP_NAME="EPUB to PDF Converter"
DEBUG=false
MAX_UPLOAD_SIZE_MB=50
LOG_LEVEL=INFO
```

Available settings:
- `APP_NAME`: Application name (default: "EPUB to PDF Converter")
- `DEBUG`: Enable debug mode (default: false)
- `MAX_UPLOAD_SIZE_MB`: Maximum file upload size in MB (default: 50)
- `LOG_LEVEL`: Logging level - DEBUG, INFO, WARNING, ERROR (default: INFO)

## Running the Server

Start the development server:
```bash
python3 -m app.main
```

Or with uvicorn directly:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Health Check
```
GET /health
```
Returns the health status of the service.

### Convert EPUB to PDF
```
POST /api/convert
```

Upload an EPUB file and receive the converted PDF.

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: File upload with field name `file`

**Response:**
- Success (200): PDF file as binary attachment
- Bad Request (400): Invalid file format or conversion error
- Request Entity Too Large (413): File exceeds size limit
- Internal Server Error (500): Unexpected error

**Example:**
```bash
curl -X POST -F "file=@document.epub" http://localhost:8000/api/convert -o output.pdf
```

## Testing

Run the test suite:
```bash
pytest tests/ -v
```

Run with coverage:
```bash
pytest tests/ --cov=app --cov-report=html
```

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py           # API endpoint definitions
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py           # Configuration management
│   └── services/
│       ├── __init__.py
│       └── converter.py        # EPUB to PDF conversion logic
├── tests/
│   ├── __init__.py
│   ├── test_api.py            # API endpoint tests
│   └── test_converter.py      # Converter service tests
├── pyproject.toml             # Project configuration
├── requirements.txt           # Production dependencies
└── README.md                  # This file
```

## Conversion Process

1. **File Validation**: Validates MIME type, extension, and file size
2. **EPUB Parsing**: Reads the EPUB file using ebooklib
3. **Content Extraction**: Extracts chapters from the EPUB spine
4. **HTML Parsing**: Converts HTML content to plain text, preserving structure
5. **PDF Generation**: Renders content using reportlab with proper formatting
6. **Streaming**: Returns the PDF as a streaming response with download headers

## Error Handling

The API returns consistent JSON error responses:

```json
{
  "error": "Error description"
}
```

Common error scenarios:
- Invalid file extension: Returns 400
- Invalid MIME type: Returns 400
- File too large: Returns 413
- Corrupted EPUB: Returns 400
- Conversion failures: Returns 400
- Unexpected errors: Returns 500

## Dependencies

### Core Dependencies
- **fastapi**: Web framework
- **uvicorn**: ASGI server
- **ebooklib**: EPUB parsing library
- **reportlab**: PDF generation library
- **python-multipart**: Multipart form data parsing
- **pydantic**: Data validation

### Development Dependencies
- **pytest**: Testing framework
- **pytest-asyncio**: Async test support
- **httpx**: HTTP client for testing

## Performance Notes

- File uploads are limited to 50MB by default (configurable)
- PDFs are generated in memory
- Large EPUBs may consume significant memory during conversion
- Consider implementing a task queue for production use with very large files

## License

MIT