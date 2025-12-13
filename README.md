---
title: EPUB to PDF Converter
emoji: 📄
colorFrom: blue
colorTo: purple
sdk: docker
app_file: app.py
pinned: false
---

# EPUB to PDF Converter

A production-ready FastAPI service that converts EPUB files to PDF format with a modern web UI, robust error handling, comprehensive file validation, streaming responses, and full accessibility support.

## Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Setup & Installation](#setup--installation)
  - [Local Python Installation](#local-python-installation)
  - [Docker Deployment](#docker-deployment)
  - [Hugging Face Spaces Deployment](#hugging-face-spaces-deployment)
- [Usage Instructions](#usage-instructions)
  - [Web UI Workflow](#web-ui-workflow)
  - [API Usage](#api-usage)
- [Configuration](#configuration)
- [Error Handling](#error-handling)
- [Testing](#testing)
- [Contributing](#contributing)
- [Troubleshooting](#troubleshooting)
- [Performance & Scaling](#performance--scaling)
- [Project Structure](#project-structure)
- [License](#license)

## Project Overview

EPUB to PDF Converter is a modern web application that provides an intuitive interface for converting EPUB ebook files to PDF format. Designed with performance and user experience in mind, it features a drag-and-drop interface, real-time file validation, progress indicators, and direct PDF downloads without page reloads.

The application is built with a stateless architecture, meaning no files are stored on the server after conversion. All processing happens in-memory, making it suitable for deployment on platforms with limited disk storage like Hugging Face Spaces.

### Key Capabilities

- **Real-time Validation**: Client-side and server-side file validation
- **Memory-efficient Processing**: In-memory conversion without temporary files
- **Streaming Responses**: PDFs are streamed directly to the browser
- **Accessibility**: Full WCAG 2.1 compliance with ARIA labels and keyboard navigation
- **Multi-format Support**: Handles various EPUB structures and formats
- **Production Ready**: Comprehensive error handling, logging, and monitoring

## Features

### Modern Web UI
- **Bootstrap 5.3.2**: Responsive design that works on all devices
- **Drag-and-Drop**: Intuitive file upload with visual feedback
- **Real-time Validation**: Immediate feedback on file type and size
- **Progress Indicators**: Visual status during upload and conversion
- **Direct Download**: PDF downloads automatically without page reload
- **Full Accessibility**: ARIA labels, keyboard navigation, screen reader support
- **Keyboard Support**: Full functionality accessible via keyboard (Tab, Enter, Space)
- **Focus Management**: Clear visual focus indicators for all interactive elements

### EPUB to PDF Conversion
- **Multi-chapter Support**: Preserves EPUB structure with page breaks
- **Unicode Support**: Handles international characters and languages
- **Text Formatting**: Maintains heading hierarchy and basic formatting
- **Error Recovery**: Graceful handling of malformed EPUBs
- **Memory Streaming**: Efficient processing of large files

### File Validation & Security
- **Extension Validation**: Only accepts `.epub` files
- **MIME Type Checking**: Validates `application/epub+zip` or `application/zip`
- **Size Limits**: Configurable maximum file size (default: 50MB)
- **Content Safety**: No server-side file storage or execution
- **Input Sanitization**: Safe handling of uploaded content

### API & Integration
- **RESTful Endpoints**: Simple POST/GET API for conversion
- **Streaming Responses**: Efficient handling of large PDFs
- **JSON Error Responses**: Consistent error format
- **CORS Support**: Ready for cross-origin requests
- **Health Monitoring**: Built-in health check endpoint

## Architecture

### System Overview

```
┌─────────────────┐     HTTP Request      ┌─────────────────┐
│   Web Browser   │─────────────────────>│   FastAPI App   │
│                 │                        │                 │
│ - File Upload   │                        │ - Validate File │
│ - Progress UI   │                        │ - Convert EPUB  │
│ - Download PDF  │                        │ - Stream PDF    │
└─────────────────┘                        └─────────────────┘
                                                 │
                                                 │ In-Memory
                                                 │ Processing
                                                 ↓
                                           ┌─────────────────┐
                                           │    ebooklib     │
                                           │   weasyprint    │
                                           └─────────────────┘
```

### Component Architecture

1. **Frontend Layer** (`static/js/`, `templates/`)
   - Vanilla JavaScript with fetch API
   - Bootstrap 5 for UI components
   - Client-side validation and progress tracking
   - Drag-and-drop handling

2. **API Layer** (`app/api/`)
   - FastAPI router with upload endpoint
   - File validation (extension, MIME type, size)
   - Exception handling and HTTP responses

3. **Service Layer** (`app/services/`)
   - EPUB parsing via `ebooklib`
   - HTML content processing
   - PDF generation via `weasyprint`
   - Memory-efficient streaming

4. **Configuration Layer** (`app/core/`)
   - Pydantic v2 settings management
   - Environment-based configuration
   - Logging configuration

5. **Shared Resources**
   - Static assets (CSS, JS)
   - HTML templates
   - Exception handlers

### Data Flow

1. **Upload**: File selected/dropped in browser
2. **Validation**: Client validates size/type, then server re-validates
3. **Processing**: EPUB loaded into memory, parsed, converted to PDF
4. **Streaming**: PDF streamed back as attachment
5. **Cleanup**: All memory resources released automatically

## Tech Stack

### Core Technologies
- **FastAPI 0.104+**: Modern async web framework with automatic API documentation
- **Python 3.9+**: Required Python version for async features
- **uvicorn 0.24+**: ASGI server with performance and production features
- **Pydantic v2**: Data validation with `model_config` pattern
- **Pydantic-Settings v2**: Environment-based configuration management

### EPUB Processing
- **ebooklib 0.18+**: EPUB parsing library with comprehensive format support
- **HTML Parser**: Custom HTML-to-text conversion preserving structure

### PDF Generation
- **weasyprint 60.0+**: HTML/CSS to PDF rendering engine
- **CSS Styling**: Comprehensive text styling and layout via CSS
- **Page Breaks**: Automatic page separation for chapters

### Frontend
- **Jinja2 3.1+**: Modern template engine with async support
- **Bootstrap 5.3.2**: Responsive CSS framework
- **Bootstrap Icons**: UI icon library
- **Vanilla JavaScript**: No framework dependencies for lightweight UI

### Development & Testing
- **pytest 7.4+**: Testing framework with fixture support
- **pytest-asyncio 0.21+**: Async test support
- **httpx 0.25+**: Modern HTTP client for testing
- **setuptools**: Python packaging with `pyproject.toml` configuration

### Deployment Platforms
- **Local Development**: Direct Python execution
- **Docker**: Containerized deployment (coming soon)
- **Hugging Face Spaces**: Cloud deployment platform

## Prerequisites

### System Requirements
- **Python**: 3.9 or higher (3.10+ recommended)
- **Memory**: Minimum 512MB RAM (2GB recommended for large files)
- **Storage**: No persistent storage required (stateless design)
- **Network**: HTTP/HTTPS access for CDN resources

### Package Dependencies
Refer to `requirements.txt` for production dependencies and `pyproject.toml` for development dependencies. All dependencies are installable via pip.

### Browser Support
- **Modern Browsers**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **JavaScript**: ES6+ support required
- **Fetch API**: Native browser support needed
- **File API**: For drag-and-drop functionality

## Setup & Installation

### Local Python Installation

#### Step 1: Clone the Repository

```bash
git clone https://github.com/your-username/epub-to-pdf-converter.git
cd epub-to-pdf-converter
```

#### Step 2: Create Virtual Environment

```bash
# Using venv (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Verify Python version
python --version  # Should be 3.9+
```

#### Step 3: Install Dependencies

**For Development (includes testing tools):**
```bash
pip install -e ".[dev]"
```

**For Production:**
```bash
pip install -r requirements.txt
```

**Verify Installation:**
```bash
pip list | grep -E "(fastapi|uvicorn|ebooklib|weasyprint)"
```

#### Step 4: Configure Environment

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your preferred settings:

```env
APP_NAME="EPUB to PDF Converter"
DEBUG=false
MAX_UPLOAD_SIZE_MB=50
LOG_LEVEL=INFO
```

#### Step 5: Run Development Server

```bash
# Option 1: Direct Python execution
python3 -m app.main

# Option 2: Using uvicorn directly
uvicorn app.main:app --reload

# Option 3: Custom host/port
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The application will be available at:
- **Web UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **Health Check**: http://localhost:8000/health

#### Step 6: Verify Setup

```bash
# Test health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","app":"EPUB to PDF Converter"}
```

### Docker Deployment

**Note**: A Dockerfile will be provided in a future update. The following instructions are for when Docker support is available.

#### Build Docker Image

```bash
# Build the image
docker build -t epub-converter:latest .

# Verify image
docker images | grep epub-converter
```

#### Run Docker Container

```bash
# Basic run
docker run -p 8000:8000 epub-converter:latest

# With environment variables
docker run -p 8000:8000 \
  -e MAX_UPLOAD_SIZE_MB=100 \
  -e LOG_LEVEL=DEBUG \
  epub-converter:latest

# With custom name
docker run -p 8000:8000 \
  --name epub-converter \
  epub-converter:latest
```

#### Docker Compose

```yaml
# docker-compose.yml (example)
version: '3.8'
services:
  epub-converter:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MAX_UPLOAD_SIZE_MB=50
      - LOG_LEVEL=INFO
    restart: unless-stopped
```

Deploy with:
```bash
docker-compose up -d
docker-compose logs -f
```

### Hugging Face Spaces Deployment

Hugging Face Spaces provides a free platform for hosting machine learning and data processing applications. This guide covers complete deployment.

#### Prerequisites

1. **Hugging Face Account**: Create at [huggingface.co](https://huggingface.co)
2. **Git**: Installed locally for pushing code
3. **Space Configuration**: Basic understanding of Space settings

#### Step 1: Create New Space

1. Go to [huggingface.co/spaces](https://huggingface.co/spaces)
2. Click "New Space" (or "Create New Space")
3. Configure Space settings:
   - **Space name**: `epub-to-pdf-converter` (or your choice)
   - **License**: MIT (or your preference)
   - **Space Hardware**: `CPU basic` (free tier)
   - **Visibility**: Public or Private

#### Step 2: Configure Space Settings

In your Space settings, configure the following:

**Container Configuration:**
```yaml
# .huggingface.yml or configure via UI
sdk: docker
base: python:3.10-slim
port: 8000
```

**Important Settings:**
- **SDK**: Set to "docker" or "gradio" (Docker recommended)
- **Port**: Set to `8000` (or your FastAPI port)
- **Python Version**: Use 3.10 or higher

#### Step 3: Prepare Repository

From your local project directory:

```bash
# Initialize git (if not already)
git init

# Add Hugging Face Space as remote
# Replace USERNAME and SPACE_NAME with your values
git remote add space https://huggingface.co/spaces/USERNAME/SPACE_NAME

# Verify remote
git remote -v
```

#### Step 4: Create Hugging Face Configuration

Create a `.huggingface.yml` file in your project root:

```yaml
# .huggingface.yml
sdk: docker
base: python:3.10-slim
port: 8000

dockerfile: |
  FROM python:3.10-slim
  
  # Install system dependencies
  RUN apt-get update && apt-get install -y \
      gcc \
      libc6-dev \
      && rm -rf /var/lib/apt/lists/*
  
  # Set working directory
  WORKDIR /app
  
  # Copy requirements
  COPY requirements.txt .
  
  # Install Python dependencies
  RUN pip install --no-cache-dir -r requirements.txt
  
  # Copy application
  COPY . .
  
  # Expose port
  EXPOSE 8000
  
  # Start application
  CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

#### Step 5: Configure Environment Variables

In your Space settings, set environment variables:

```bash
APP_NAME=EPUB to PDF Converter
DEBUG=false
MAX_UPLOAD_SIZE_MB=50
LOG_LEVEL=INFO
```

**Accessing Space Settings:**
1. Go to your Space page
2. Click "Settings" tab
3. Scroll to "Variables and secrets"
4. Add each variable individually

#### Step 6: Deploy to Spaces

```bash
# Add all files
git add .

# Commit
git commit -m "Initial deployment to Hugging Face Spaces"

# Push to Spaces
git push space main

# Monitor deployment
# Go to your Space URL: https://huggingface.co/spaces/USERNAME/SPACE_NAME
```

#### Step 7: Monitor Deployment

View deployment logs:
- Go to your Space page
- Click "Logs" tab to see build and runtime logs
- Check for errors in the build process

**Common Build Log Output:**
```
Step 6/10 : RUN pip install --no-cache-dir -r requirements.txt
Successfully built package
Step 10/10 : CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", ...]
Launching... Uvicorn running on http://0.0.0.0:8000
```

#### Step 8: Configure App Port (Important!)

If you see "No app is running" error:

1. Go to Space Settings → App Configuration
2. Set "App Port" to `8000`
3. Click "Save" and restart the Space
4. Wait 1-2 minutes for restart

#### Step 9: Access Your Application

Your app will be available at:
```
https://USERNAME-SPACE-NAME.hf.space
```

Test the application:
1. Open the URL in your browser
2. Drag and drop an EPUB file
3. Click "Convert to PDF"
4. Verify PDF downloads successfully

#### Step 10: Test API Endpoint

```bash
# Your Space API endpoint
export SPACE_URL="https://USERNAME-SPACE-NAME.hf.space"

# Test health endpoint
curl $SPACE_URL/health

# Test with sample EPUB
curl -X POST -F "file=@sample.epub" \
  $SPACE_URL/api/convert \
  -o output.pdf
```

#### Troubleshooting Spaces Deployment

**Problem: "No app is running"**
- Check App Port is set to 8000
- Verify Dockerfile CMD exposes correct port
- Check Logs tab for startup errors

**Problem: Build fails with package errors**
- Ensure all dependencies in requirements.txt
- Check Python version compatibility
- Review build logs for specific error messages

**Problem: File upload timeout**
- Reduce MAX_UPLOAD_SIZE_MB in environment
- Check Hugging Face Spaces timeouts (usually 60s)
- Consider smaller EPUB files

**Problem: Memory errors**
- Upgrade Space Hardware (paid tier)
- Reduce maximum file size
- Monitor memory usage in logs

**Problem: CORS errors**
- CORS is configured in app/main.py with permissive settings
- Check browser console for specific error
- Verify HTTPS is used

## Usage Instructions

### Web UI Workflow

Follow these steps to convert EPUB to PDF using the web interface:

#### Step 1: Access the Application

Open your browser and navigate to:
- **Local**: http://localhost:8000
- **Docker**: http://localhost:8000
- **Spaces**: https://username-space-name.hf.space

#### Step 2: Upload EPUB File (Multiple Methods)

**Method A: Drag and Drop**
1. Locate EPUB file on your computer
2. Drag file into the dashed drop zone
3. Wait for validation checkmark

**Method B: File Browser**
1. Click "Click here to select files"
2. Navigate to EPUB file
3. Select file and click "Open"

**Method C: Keyboard**
1. Press Tab to focus drop zone (you'll see visual focus)
2. Press Enter or Space to open file dialog
3. Select file with keyboard navigation

#### Step 3: Verify File Validation

The UI will display:
- ✅ **Success**: Green checkmark, file name shown
- ❌ **Error**: Red message explaining the issue

**Validation checks:**
- File extension (.epub only)
- MIME type (application/epub+zip)
- File size (default: 50MB max)

#### Step 4: Convert to PDF

1. Click "Convert to PDF" button
2. Watch progress indicator:
   - **Uploading**: File sending to server
   - **Processing**: EPUB being converted
   - **Generating**: PDF being created
   - **Complete**: Green success message

**Button States:**
- **Active**: Ready to convert
- **Processing**: Animated spinner, disabled
- **Success**: Green with checkmark

#### Step 5: Download PDF

**Automatic Download:**
- PDF downloads automatically when complete
- Check your browser's downloads folder
- File named: `OriginalName.pdf`

**Manual Download (if needed):**
1. Look for download confirmation
2. Click download link if provided
3. Or check browser downloads (Ctrl+J / Cmd+J)

#### Step 6: Repeat for More Files

The UI is stateless:
1. Drop another file to start new conversion
2. No page reload needed
3. Previous PDF stays available in downloads

### Keyboard Shortcuts

- **Tab**: Navigate between interactive elements
- **Enter/Space**: Activate focused element (button, drop zone)
- **Esc**: Cancel during drag operation

### Screen Reader Support

- All buttons have descriptive labels
- Status messages announced via ARIA live regions
- Progress updates announced during conversion
- Download confirmation announced

### API Usage

#### Health Check Endpoint

```bash
GET /health
```

**Example:**
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "app": "EPUB to PDF Converter"
}
```

#### Convert EPUB to PDF

```bash
POST /api/convert
Content-Type: multipart/form-data
```

**Parameters:**
- `file`: EPUB file (required)

**Example using curl:**
```bash
curl -X POST \
  -F "file=@/path/to/document.epub" \
  http://localhost:8000/api/convert \
  -o output.pdf
```

**Example with metadata:**
```bash
curl -X POST \
  -F "file=@document.epub;filename=document.epub" \
  -F "title=My Ebook" \
  -F "author=John Doe" \
  http://localhost:8000/api/convert \
  -o document.pdf
```

**Example using Python (requests):**
```python
import requests

url = "http://localhost:8000/api/convert"
files = {"file": open("document.epub", "rb")}

response = requests.post(url, files=files)

if response.status_code == 200:
    with open("output.pdf", "wb") as f:
        f.write(response.content)
    print("PDF saved as output.pdf")
else:
    print(f"Error: {response.json()['error']}")
```

**Example using JavaScript (fetch):**
```javascript
async function convertEpub(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("/api/convert", {
    method: "POST",
    body: formData
  });

  if (response.ok) {
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = file.name.replace(".epub", ".pdf");
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
  } else {
    const error = await response.json();
    console.error("Error:", error.message);
  }
}
```

#### Response Codes

- **200 OK**: Success, PDF in response body
- **400 Bad Request**: Invalid file or conversion error
- **413 Request Entity Too Large**: File exceeds size limit
- **500 Internal Server Error**: Unexpected server error

#### Error Response Format

```json
{
  "error": "Error description message"
}
```

#### Debug HTML Endpoints

The application provides debug endpoints to inspect the generated HTML before PDF conversion. This is useful for diagnosing font size, color, and formatting issues.

##### Get Debug Info

```bash
GET /api/debug-info
```

Returns information about the debug HTML file, including size and preview.

**Example:**
```bash
curl http://localhost:8000/api/debug-info
```

**Response (when debug file exists):**
```json
{
  "file_exists": true,
  "file_size": "45678 bytes",
  "file_size_kb": "44.61 KB",
  "preview": "<!DOCTYPE html><html><head>...",
  "download_url": "/api/download-debug",
  "view_url": "/api/debug-html",
  "message": "Debug HTML 文件已生成，可以查看或下载"
}
```

**Response (before any conversion):**
```json
{
  "file_exists": false,
  "message": "需要先转换一个 EPUB 文件",
  "info": "上传 EPUB 文件后，系统会自动生成 debug.html 用于诊断"
}
```

##### View Debug HTML

```bash
GET /api/debug-html
```

Returns the debug HTML content to view directly in the browser.

**Example:**
```bash
curl http://localhost:8000/api/debug-html
# Or open in browser: http://localhost:8000/api/debug-html
```

**Response:** HTML content (200 OK) or error JSON (404 Not Found)

##### Download Debug HTML

```bash
GET /api/download-debug
```

Downloads the debug HTML file as an attachment.

**Example:**
```bash
curl http://localhost:8000/api/download-debug -o debug.html
```

**Response:** HTML file download (200 OK) or error JSON (404 Not Found)

##### Debug Workflow

1. **Convert an EPUB file** using `/api/convert`
2. **Check debug info** at `/api/debug-info` to confirm file was generated
3. **View in browser** at `/api/debug-html` to inspect rendering
4. **Download file** at `/api/download-debug` for detailed analysis

**Use Cases:**
- Verify font sizes are correct in the HTML
- Check if colors are properly embedded in style attributes
- Inspect paragraph indentation and alignment
- Debug image embedding and positioning
- Validate CSS class conversions to inline styles

**Note:** The debug HTML file is overwritten each time a new EPUB is converted. Only the most recent conversion's debug output is available.

## Configuration

### Environment Variables

Configuration is managed through environment variables or `.env` file. The application uses Pydantic v2 with SettingsConfigDict for validation.

#### Core Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `APP_NAME` | string | "EPUB to PDF Converter" | Application display name |
| `DEBUG` | boolean | false | Enable debug mode and verbose logging |
| `MAX_UPLOAD_SIZE_MB` | integer | 50 | Maximum file size in megabytes |
| `LOG_LEVEL` | string | INFO | Logging level: DEBUG, INFO, WARNING, ERROR |

#### File Validation Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ALLOWED_MIME_TYPES` | list | ["application/epub+zip", "application/zip"] | Valid MIME types |
| `ALLOWED_EXTENSIONS` | list | [".epub"] | Valid file extensions |

#### Logging Levels

- **DEBUG**: Detailed diagnostic information (development only)
- **INFO**: General operational messages (recommended for production)
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error conditions that don't stop execution

### Configuration Examples

#### Development Configuration (`.env`)

```env
APP_NAME=EPUB Converter Dev
DEBUG=true
MAX_UPLOAD_SIZE_MB=100
LOG_LEVEL=DEBUG
```

#### Production Configuration (`.env`)

```env
APP_NAME=EPUB to PDF Converter
DEBUG=false
MAX_UPLOAD_SIZE_MB=50
LOG_LEVEL=INFO
```

#### High-Volume Configuration (`.env`)

```env
APP_NAME=EPUB Converter Pro
DEBUG=false
MAX_UPLOAD_SIZE_MB=200
LOG_LEVEL=WARNING
```

### Customizing File Size Limits

To increase maximum upload size:

1. **Update Environment Variable:**
   ```env
   MAX_UPLOAD_SIZE_MB=100
   ```

2. **Update Frontend Validation** (optional):
   Edit `static/js/app.js`:
   ```javascript
   const MAX_FILE_SIZE = 104857600; // 100MB in bytes
   ```

3. **Restart Server**:
   Changes apply immediately on restart

**Note**: Large files require more memory.

### Customizing Conversion Parameters

Current conversion parameters are optimized for general use. To customize:

#### PDF Page Size

Edit `app/services/converter.py`:

```python
# Update CSS @page rule in converter.py
CSS_STYLES = """
@page {
    margin: 1in;
    size: A4;  # or letter, (595pt, 842pt) for A4
}
"""
```

#### Font Settings

```python
# Update CSS font settings
CSS_STYLES = """
body {
    font-family: "DejaVu Sans", Arial, sans-serif;
    font-size: 14pt;  # Change font size
    line-height: 1.4;  # Line spacing
}
"""
```

#### Heading Detection

Modify heading identification logic:

```python
def _is_heading(self, text, length):
    """Custom heading detection."""
    return (
        length < 100 and
        text[0].isupper() and
        not text.startswith(' ')  # Additional rules
    )
```

## Error Handling

### Error Types and Responses

The API returns consistent JSON error responses for all error conditions.

#### 400 Bad Request - File Validation Errors

##### Invalid File Extension
```json
{
  "error": "Invalid file extension: .txt. Allowed extensions: .epub"
}
```

**Solution**: Use only `.epub` files

##### Invalid MIME Type
```json
{
  "error": "Invalid MIME type: text/plain. Allowed types: application/epub+zip, application/zip"
}
```

**Solution**: Ensure file is proper EPUB format

##### File Too Large
```json
{
  "error": "File size exceeds maximum allowed size of 50MB"
}
```

**Solution**: Reduce file size or increase MAX_UPLOAD_SIZE_MB

##### Corrupted EPUB
```json
{
  "error": "Conversion error: Unable to parse EPUB file"
}
```

**Solution**: Validate EPUB file integrity

#### 413 Request Entity Too Large

```json
{
  "error": "File size exceeds maximum allowed size"
}
```

**Solution**: Compress EPUB or use smaller file

#### 500 Internal Server Error

```json
{
  "error": "An unexpected error occurred during conversion"
}
```

**Solution**: Check server logs, restart application

### Troubleshooting Errors

#### Common Issues

**Problem**: "Invalid file extension" error
- Verify file ends with `.epub`
- Check for hidden characters in filename
- Ensure file is not renamed ZIP

**Problem**: "Unable to parse EPUB file"
- EPUB may be corrupted
- Try opening with another EPUB reader
- Re-encode EPUB if possible

**Problem**: Conversion timeout
- File may be too large
- Check server memory (EPUBs can expand significantly)
- Try smaller file or increase resources

**Problem**: PDF missing chapters
- EPUB spine may be incorrectly configured
- Check EPUB with validation tool
- Verify all chapters in EPUB manifest

### Logging and Debugging

Enable debug logging to see detailed information:

1. **Set Debug Mode:**
   ```env
   DEBUG=true
   LOG_LEVEL=DEBUG
   ```

2. **View Logs:**
   ```bash
   # Local development
   python3 -m app.main

   # Docker
   docker logs epub-converter
   ```

3. **Log Locations:**
   - Local: Console output
   - Docker: `docker logs [container-id]`
   - Spaces: "Logs" tab in Space interface

**Debug Log Example:**
```
DEBUG: Received conversion request for file: sample.epub
DEBUG: File size: 2048576 bytes (1.95 MB)
DEBUG: MIME type: application/epub+zip
INFO: Successfully converted EPUB to PDF (3145728 bytes)
```

## Testing

### Running the Test Suite

#### Prerequisites

```bash
# Ensure dev dependencies installed
pip install -e ".[dev]"
```

#### Run All Tests

```bash
# Basic command
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html

# With specific pattern
pytest tests/ -k "test_convert" -v

# Stop on first failure
pytest tests/ -x

# Run with coverage threshold
pytest tests/ --cov=app --cov-report=term-missing --cov-fail-under=80
```

#### Test Structure

```
tests/
├── test_api.py           # API endpoint tests
│   ├── test_home_page    # UI rendering tests
│   ├── test_health_check # Health endpoint
│   ├── test_convert      # Conversion endpoint
│   └── test_validation   # File validation
└── test_converter.py     # Conversion service tests
    ├── test_convert      # Basic conversion
    ├── test_html_parsing # HTML processing
    ├── test_unicode      # Unicode handling
    └── test_errors       # Error conditions
```

#### Run Specific Test Categories

**API Tests Only:**
```bash
pytest tests/test_api.py -v
```

**Converter Service Tests:**
```bash
pytest tests/test_converter.py -v
```

**Validation Tests:**
```bash
pytest tests/ -k "validation"
```

### Test Coverage

Current test suite covers:
- ✅ Home page loading and UI rendering
- ✅ Static file serving (CSS, JS)
- ✅ Health check endpoint
- ✅ File validation (extension, MIME type, size)
- ✅ EPUB to PDF conversion
- ✅ HTML parsing and text extraction
- ✅ Unicode character support
- ✅ Multiple chapter handling
- ✅ Error handling and error messages
- ✅ Streaming response headers

**View Coverage Report:**
```bash
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html  # On macOS
# Or navigate to htmlcov/index.html
```

### Adding New Tests

#### Example: New API Test

```python
# tests/test_api.py

def test_custom_validation(client):
    """Test custom file validation rule."""
    with open("tests/fixtures/test.epub", "rb") as f:
        response = client.post(
            "/api/convert",
            files={"file": ("test.epub", f, "application/epub+zip")}
        )
    assert response.status_code == 200
```

#### Example: New Converter Test

```python
# tests/test_converter.py

def test_large_epub(converter, large_epub_content):
    """Test conversion of large EPUB files."""
    pdf_content = converter.convert(large_epub_content)
    assert len(pdf_content) > 0
    assert pdf_content.startswith(b"%PDF-")
```

### Integration Testing

**End-to-End Test Example:**

```python
def test_full_workflow(client, sample_epub):
    """Test complete user workflow."""
    # 1. Upload file
    with open(sample_epub, "rb") as f:
        response = client.post("/api/convert", files={"file": ("test.epub", f)})
    
    # 2. Verify success
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    
    # 3. Verify PDF content
    pdf_data = response.content
    assert pdf_data.startswith(b"%PDF-")
    assert response.headers["content-disposition"].contains("attachment")
```

### Manual Testing Checklist

Before deploying, manually test:

- [ ] Home page loads correctly
- [ ] Static files served (CSS styles apply)
- [ ] Drag and drop functionality
- [ ] File browser upload
- [ ] Invalid file validation (wrong extension)
- [ ] Invalid file validation (wrong MIME type)
- [ ] File size limit enforcement
- [ ] Successful EPUB conversion
- [ ] PDF download works
- [ ] Error messages display correctly
- [ ] Keyboard navigation works
- [ ] Screen reader announces properly
- [ ] Mobile responsiveness
- [ ] Cross-browser compatibility

## Contributing

### Contribution Guidelines

We welcome contributions! Please follow these guidelines:

#### Code Style

- **PEP 8**: Follow Python style guidelines
- **Black**: Use Black formatter for Python code
- **Type Hints**: Include type annotations for functions
- **Docstrings**: Document functions and classes with docstrings

```python
# Good example
def validate_file(file: UploadFile) -> bool:
    """Validate uploaded file format and size.
    
    Args:
        file: The uploaded file to validate
        
    Returns:
        True if file is valid, False otherwise
    """
    # Implementation here
```

#### Git Workflow

1. **Fork Repository**: Create your own fork
2. **Create Branch**: Use descriptive branch names
   ```bash
   git checkout -b feature/add-custom-fonts
   git checkout -b fix/unicode-handling
   git checkout -b docs/deployment-guide
   ```

3. **Make Changes**: Implement your feature or fix
4. **Run Tests**: Ensure all tests pass
   ```bash
   pytest tests/ -v
   ```

5. **Commit Changes**: Use clear commit messages
   ```bash
   git add .
   git commit -m "feat: add support for custom fonts
   
   - Add font configuration to converter
   - Update tests for font customization
   - Document new feature in README"
   ```

6. **Push Branch:**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create Pull Request**: Submit PR with description

### Commit Message Format

Follow conventional commits:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation update
- `test:` Test addition or update
- `refactor:` Code refactoring
- `chore:` Maintenance tasks

Examples:
```
feat: add PDF metadata extraction
fix: resolve unicode handling for non-Latin characters
docs: update Hugging Face deployment guide
test: add integration tests for large files
```

### Testing Your Changes

Before submitting PR:

1. **Run All Tests:**
   ```bash
   pytest tests/ -v --cov=app
   ```

2. **Check Coverage:**
   ```bash
   pytest tests/ --cov=app --cov-fail-under=80
   ```

3. **Manual Testing:**
   Test the feature manually following the testing checklist

4. **Clean Code:**
   ```bash
   # Format code
   black app/ tests/

   # Sort imports
   isort app/ tests/

   # Type check (if mypy configured)
   mypy app/
   ```

### Adding New Features

#### Feature Request Process

1. **Check Existing Issues**: Look for similar feature requests
2. **Create Issue**: Describe the feature with use cases
3. **Wait for Discussion**: Get feedback from maintainers
4. **Implement**: Code the feature
5. **Test**: Add comprehensive tests
6. **Document**: Update README and docstrings

#### Feature Implementation Steps

1. **Plan Architecture**: Design the feature integration
2. **Update Core Logic**: Modify converter or API as needed
3. **Add Configuration**: Update config.py if needed
4. **Write Tests**: Unit and integration tests
5. **Update Documentation**: README and docstrings
6. **Manual Testing**: Test all user workflows

#### Example: Adding New Output Format

```python
# 1. Update converter.py
class EPUBToPDFConverter:
    def convert_to_format(self, content, format="pdf"):
        if format == "pdf":
            return self._to_pdf(content)
        elif format == "docx":
            return self._to_docx(content)

# 2. Update API route
@router.post("/convert")
async def convert(file: UploadFile, format: str = "pdf"):
    # Validate format
    if format not in ["pdf", "docx"]:
        raise HTTPException(status_code=400, detail="Invalid format")

# 3. Add tests
def test_convert_to_docx(converter):
    result = converter.convert_to_format(epub_content, "docx")
    assert result.startswith(b"PK")  # DOCX signature

# 4. Update documentation
```

### Bug Reports

When reporting bugs, include:

1. **Environment**: Python version, OS, deployment method
2. **Steps to Reproduce**: Detailed steps
3. **Expected Behavior**: What should happen
4. **Actual Behavior**: What actually happens
5. **Error Messages**: Full error text and logs
6. **Sample File**: If possible, provide problematic EPUB

#### Bug Report Template

```markdown
**Environment**
- Python version: 3.10.8
- OS: Ubuntu 22.04
- Deployment: Local/Docker/Spaces

**Steps to Reproduce**
1. Upload [sample.epub](link)
2. Click convert
3. Error occurs

**Expected Behavior**
PDF should download successfully

**Actual Behavior**
Error: "Conversion failed - memory error"

**Error Logs**
```
Full error log here
```

**Sample File**
If applicable, attach the problematic EPUB
```

### Documentation Contributions

#### Documentation Standards

- **Clarity**: Use simple, direct language
- **Completeness**: Cover all options and edge cases
- **Examples**: Include code examples for common uses
- **Screenshots**: Include for UI documentation
- **Updates**: Keep in sync with code changes

#### Areas for Documentation

- Tutorials and how-to guides
- API documentation
- Deployment guides
- Troubleshooting sections
- Example use cases

### Pull Request Process

1. **Update Branch**: Ensure your branch is up-to-date
   ```bash
   git fetch origin
   git rebase origin/main
   ```

2. **Run Checks**: All tests and quality checks pass

3. **Submit PR**: Create detailed pull request
   - Clear title
   - Description of changes
   - Related issues
   - Testing performed
   - Screenshots (for UI changes)

4. **Code Review**: Address feedback from maintainers

5. **Merge**: Maintainers will merge after approval

### Community Guidelines

- **Be Respectful**: Treat all contributors with respect
- **Constructive Feedback**: Provide helpful, specific feedback
- **Stay On Topic**: Keep discussions relevant to the issue
- **Help Others**: Welcome newcomers and help them contribute
- **Acknowledge Work**: Give credit where due

## Troubleshooting

### Common Issues and Solutions

#### Installation Problems

**Issue**: `pip install` fails with compilation errors
```
error: Microsoft Visual C++ 14.0 is required
```

**Solution**:
- Windows: Install Visual C++ Build Tools
- Linux: Install `gcc` and `python3-dev`
- macOS: Install Xcode Command Line Tools

```bash
# Ubuntu/Debian
sudo apt-get install gcc python3-dev

# macOS
xcode-select --install
```

**Issue**: Dependency conflicts
```
ERROR: Cannot install because these package versions have conflicting dependencies
```

**Solution**:
```bash
# Clean install
pip install --upgrade pip
pip install --force-reinstall -r requirements.txt

# Or use virtualenv
python3 -m venv fresh_env
source fresh_env/bin/activate
pip install -r requirements.txt
```

#### Runtime Problems

**Issue**: Application starts but immediately crashes

**Diagnosis**:
```bash
# Check Python version
python --version  # Must be 3.9+

# Check for missing imports
python -c "import app.main"  # Should be silent

# Check for port conflicts
netstat -an | grep 8000  # Should be empty
```

**Solution**:
- Close applications using port 8000
- Change port in uvicorn command
- Check all dependencies installed

**Issue**: Memory errors with large files
```
MemoryError: Unable to allocate 123.45 MiB
```

**Solution**:
```env
# Reduce file size limit
MAX_UPLOAD_SIZE_MB=30
```

Or increase system memory allocation (Docker/Spaces).

#### Conversion Problems

**Issue**: EPUB fails to convert, Unknown error

**Debug Steps**:
1. Enable debug logging
2. Try different EPUB
3. Check EPUB validity with online validator
4. Examine file structure

**Common Causes**:
- Corrupted EPUB file
- Invalid EPUB structure
- Missing chapters in spine
- Encoding issues

**Workarounds**:
- Re-encode EPUB with Calibre
- Convert to EPUB again from source
- Check file permissions

**Issue**: PDF is blank or missing text

**Debug Steps**:
1. Verify EPUB contains text (not just images)
2. Check encoding is UTF-8
3. Try simpler EPUB
4. Enable debug to see if chapters detected

#### Hugging Face Spaces Issues

**Issue**: "No app is running"

**Solutions**:
1. Verify App Port setting is 8000
2. Check Logs tab for startup errors
3. Ensure all files pushed correctly
4. Check if `app.main:app` is correct module path

**Issue**: Build succeeds but app crashes

**Debug**:
1. Check Logs tab immediately after startup
2. Look for import errors
3. Verify Python version in Space
4. Check memory limits

**Issue**: File uploads timeout

**Solutions**:
1. Reduce MAX_UPLOAD_SIZE_MB
2. Test with smaller EPUB
3. Check network connection
4. Consider upgrading Space hardware

**Issue**: CORS errors in browser console

**Solution**: CORS is configured permissively by default. If customizing:
```python
# In app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend.com"],  # Specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### Performance Issues

**Issue**: Slow conversion for large EPUBs

**Optimization Tips**:
1. Check server memory (should be 2x largest EPUB size)
2. Reduce MAX_UPLOAD_SIZE_MB
3. Monitor CPU usage during conversion
4. Consider async worker configuration

**Issue**: UI slow to respond

**Solutions**:
- Check browser Developer Tools (F12) Network tab
- Look for slow API responses
- Enable FastAPI debug for more info
- Check server resource usage

### Getting Help

If you encounter issues not covered here:

1. **Check Existing Issues**: Search GitHub issues
2. **Enable Debug Logging**: Get detailed error information
3. **Provide Context**: Include error logs, environment details
4. **Create Issue**: Submit bug report with reproduction steps
5. **Join Community**: Look for discussions or forums

**Debug Information to Include**:
```bash
# Environment
python --version
pip list | grep -E "(fastapi|uvicorn|ebooklib|weasyprint)"

# Error logs
tail -f app.log  # If logging to file

# Test basic functionality
curl -v http://localhost:8000/health
```

## Performance & Scaling

### Performance Characteristics

**Conversion Speed**:
- Small EPUBs (< 1MB): ~1-2 seconds
- Medium EPUBs (1-10MB): ~3-8 seconds
- Large EPUBs (10-50MB): ~10-30 seconds

**Memory Usage**:
- Base application: ~50-100MB RAM
- Per conversion: ~2-3x EPUB file size
- Peak usage: During PDF generation

**Example Resource Usage**:
```
EPUB Size: 10MB
Memory Used: 25-30MB
CPU Time: ~5 seconds
PDF Output: ~8MB
```

### Optimization Tips

#### For Large Files

1. **Increase Memory**:
   - Local: Use machine with 4GB+ RAM
   - Docker: Set memory limits appropriately
   - Spaces: Upgrade to paid tier

2. **Optimize EPUB**:
   - Compress images within EPUB
   - Remove unnecessary metadata
   - Split very large EPUBs

3. **Configure Limits**:
   ```env
   MAX_UPLOAD_SIZE_MB=100  # Only if resources support it
   ```

#### For High Traffic

1. **Multiple Workers**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

2. **Load Balancing**: Use reverse proxy (nginx)

3. **Caching**: Consider caching converted files (if privacy allows)

4. **Queue System**: Implement Celery for background processing

### Production Considerations

#### Security

- **File Scanning**: Consider virus scanning for uploaded files
- **Rate Limiting**: Prevent abuse with rate limits
- **Size Limits**: Conservative MAX_UPLOAD_SIZE_MB
- **Monitoring**: Log all conversion attempts
- **HTTPS**: Always use HTTPS in production

#### Monitoring

**Health Checks**:
```bash
# Monitor health endpoint every 30 seconds
curl -f http://localhost:8000/health || echo "DOWN"
```

**Application Metrics**:
- Conversion success rate
- Average conversion time
- Memory usage patterns
- Error frequency

#### Logging

Configure structured logging in production:
```env
LOG_LEVEL=INFO  # DEBUG for development
```

**Log Format**:
```
2024-01-15 10:30:45,123 - app.api.routes - INFO - Converted mybook.epub (2.3MB) in 3.2s
```

### Limitations

**Current Limitations**:
- In-memory processing (no temporary files)
- Single-threaded conversion per instance
- No built-in rate limiting
- No persistent storage
- Browser upload limits may apply

**Future Considerations**:
- Background task processing
- Persistent API keys
- Batch conversion endpoint
- Advanced PDF customization

#### Known Issues

1. **Very Large EPUBs**: Files >100MB may fail on limited hardware
2. **Complex EPUBs**: Heavily formatted EPUBs may lose some styling
3. **Image-Heavy EPUBs**: Conversion focuses on text, images not included
4. **Network Timeouts**: Large uploads may timeout on slow connections

**Workarounds**:
- Pre-process EPUBs to reduce complexity
- Use smaller files or split large EPUBs
- Deploy on hardware with more memory
- Consider paid tiers for better resources

#### Scaling Strategies

**Vertical Scaling**:
- Increase CPU and RAM
- Use instances with more resources

**Horizontal Scaling**:
- Multiple instances with load balancer
- Shared nothing architecture (stateless)
- Perfect for container orchestration

**Hybrid Approach**:
- Stateless FastAPI instances
- Shared Redis for rate limiting
- Distributed task queue for conversion
- Central logging (ELK stack)

## Project Structure

```
.
├── app/                          # Main application package
│   ├── __init__.py
│   ├── main.py                  # FastAPI app initialization
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py            # API endpoint definitions
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py            # Configuration management
│   └── services/
│       ├── __init__.py
│       └── converter.py         # EPUB to PDF conversion logic
├── static/                      # Static assets
│   ├── css/
│   │   └── styles.css          # Custom CSS styles
│   └── js/
│       └── app.js              # Frontend JavaScript
├── templates/                   # Jinja2 templates
│   └── index.html              # Main UI template
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── test_api.py            # API endpoint tests
│   └── test_converter.py      # Converter service tests
├── .env.example                # Environment variables template
├── .gitignore                  # Git ignore rules
├── pyproject.toml              # Project configuration
├── requirements.txt            # Production dependencies
└── README.md                   # This file
```

### Key Files Description

**app/main.py**: FastAPI application
- App initialization and configuration
- Middleware setup (CORS, static files)
- Exception handlers
- Router registration

**app/api/routes.py**: Conversion endpoint
- File validation
- Conversion orchestration
- Streaming response generation
- Error handling

**app/services/converter.py**: Core conversion logic
- EPUB parsing
- HTML content extraction
- PDF generation
- Memory-efficient processing

**app/core/config.py**: Configuration
- Pydantic v2 settings
- Environment variable loading
- Type validation
- Default values

**static/js/app.js**: Frontend logic
- Drag-and-drop handling
- File validation
- Fetch API calls
- Progress updates
- Download handling

**static/css/styles.css**: UI styling
- Bootstrap customization
- Drop zone styling
- Progress indicators
- Responsive design

**templates/index.html**: Main UI template
- Accessible HTML structure
- Bootstrap components
- Form elements
- ARIA labels

### Backend Architecture

The backend follows a layered architecture:

1. **API Layer** (routes.py): HTTP request handling
2. **Service Layer** (converter.py): Business logic
3. **Config Layer** (config.py): Configuration management
4. **Shared Layer** (main.py): Application setup

**Request Flow:**
1. HTTP POST to `/api/convert`
2. File validation (type, size, security)
3. EPUB parsing and content extraction
4. PDF generation with WeasyPrint
5. Streaming response to client
6. Memory cleanup

This architecture ensures:
- Clear separation of concerns
- Easy testing of components
- Modular feature addition
- Maintainable codebase

## License

MIT License

Copyright (c) 2024 EPUB Converter Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

**Made with ❤️ by the EPUB Converter Team**
