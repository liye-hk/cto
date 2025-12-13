import io
import logging
import os
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse, JSONResponse

from app.core.config import settings
from app.services.converter import EPUBToPDFConverter, ConversionError

router = APIRouter(prefix="/api", tags=["converter"])
logger = logging.getLogger(__name__)
converter = EPUBToPDFConverter()

# Path to debug HTML file
DEBUG_HTML_PATH = '/tmp/debug.html'


def get_disposition_header(original_filename: str) -> str:
    """Generate Content-Disposition header with RFC 5987 UTF-8 filename support"""
    # Remove .epub extension and add .pdf
    pdf_name = original_filename.rsplit('.', 1)[0] + '.pdf' if '.' in original_filename else original_filename + '.pdf'
    
    # RFC 5987 encoding: supports UTF-8 filenames with ASCII fallback
    encoded_name = quote(pdf_name.encode('utf-8'), safe='')
    ascii_fallback = "output.pdf"
    
    return f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded_name}'


def _validate_file(file: UploadFile) -> None:
    """
    Validate uploaded file.

    Args:
        file: The uploaded file

    Raises:
        HTTPException: If file is invalid
    """
    # Check file extension
    filename = file.filename or ""
    file_ext = Path(filename).suffix.lower()
    if file_ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension: {file_ext}. Allowed extensions: {', '.join(settings.allowed_extensions)}",
        )

    # Check MIME type
    content_type = file.content_type or ""
    if content_type not in settings.allowed_mime_types:
        logger.warning(f"File MIME type {content_type} not in allowed list")
        # We'll still allow it if extension is valid, but log the warning
        if file_ext not in [".epub"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid MIME type: {content_type}. Allowed types: {', '.join(settings.allowed_mime_types)}",
            )


async def _validate_file_size(file: UploadFile) -> None:
    """
    Validate file size.

    Args:
        file: The uploaded file

    Raises:
        HTTPException: If file is too large
    """
    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024
    file_content = await file.read()
    await file.seek(0)

    if len(file_content) > max_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds maximum allowed size of {settings.max_upload_size_mb}MB",
        )

    return len(file_content)


@router.post("/convert")
async def convert_epub_to_pdf(file: UploadFile = File(...)) -> StreamingResponse:
    """
    Convert an EPUB file to PDF.

    Args:
        file: The EPUB file to convert

    Returns:
        PDF file as a streaming response

    Raises:
        HTTPException: If conversion fails or file is invalid
    """
    logger.info(f"Received conversion request for file: {file.filename}")

    try:
        # Validate file type and extension
        _validate_file(file)

        # Validate file size
        file_size = await _validate_file_size(file)
        logger.info(f"File size: {file_size} bytes")

        # Read file content
        epub_content = await file.read()
        logger.info(f"Read {len(epub_content)} bytes from file")

        # Convert EPUB to PDF
        pdf_content = converter.convert(epub_content)
        logger.info(f"Successfully converted EPUB to PDF ({len(pdf_content)} bytes)")

        # Generate output filename with RFC 5987 UTF-8 support
        original_filename = file.filename
        disposition = get_disposition_header(original_filename)

        # Return PDF as streaming response
        return StreamingResponse(
            io.BytesIO(pdf_content),
            media_type="application/pdf",
            headers={"Content-Disposition": disposition},
        )

    except HTTPException:
        raise
    except ConversionError as e:
        logger.error(f"Conversion error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Conversion error: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error during conversion: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during conversion",
        )


@router.get("/debug-html")
async def get_debug_html():
    """
    获取最后生成的 debug.html（作为网页显示）
    访问: /api/debug-html
    
    Returns:
        HTMLResponse: The debug HTML content to view in browser
    """
    try:
        if os.path.exists(DEBUG_HTML_PATH):
            with open(DEBUG_HTML_PATH, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info("Debug HTML accessed successfully")
            return HTMLResponse(content=content)
        else:
            logger.warning("Debug HTML file not found")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": "debug.html not found. Convert an EPUB first.",
                    "info": "上传一个 EPUB 文件进行转换，转换完成后就会生成 debug.html"
                }
            )
    except Exception as e:
        logger.error(f"Error reading debug HTML: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read debug.html: {str(e)}"
        )


@router.get("/download-debug")
async def download_debug():
    """
    下载 debug.html 文件
    访问: /api/download-debug
    
    Returns:
        FileResponse: The debug HTML file as a download
    """
    try:
        if os.path.exists(DEBUG_HTML_PATH):
            logger.info("Debug HTML file download requested")
            return FileResponse(
                DEBUG_HTML_PATH,
                filename='debug.html',
                media_type='text/html'
            )
        else:
            logger.warning("Debug HTML file not found for download")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="debug.html not found. Convert an EPUB first."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading debug HTML: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download debug.html: {str(e)}"
        )


@router.get("/debug-info")
async def debug_info():
    """
    获取调试信息（文件大小等）
    访问: /api/debug-info
    
    Returns:
        dict: Debug file information including size, preview, and URLs
    """
    try:
        if os.path.exists(DEBUG_HTML_PATH):
            size = os.path.getsize(DEBUG_HTML_PATH)
            # 读取前 1000 字符作为预览
            with open(DEBUG_HTML_PATH, 'r', encoding='utf-8') as f:
                preview = f.read(1000)
            
            logger.info(f"Debug info accessed: file size {size} bytes")
            return {
                "file_exists": True,
                "file_size": f"{size} bytes",
                "file_size_kb": f"{size / 1024:.2f} KB",
                "preview": preview + "...",
                "download_url": "/api/download-debug",
                "view_url": "/api/debug-html",
                "message": "Debug HTML 文件已生成，可以查看或下载"
            }
        else:
            logger.info("Debug info accessed but file doesn't exist yet")
            return {
                "file_exists": False,
                "message": "需要先转换一个 EPUB 文件",
                "info": "上传 EPUB 文件后，系统会自动生成 debug.html 用于诊断"
            }
    except Exception as e:
        logger.error(f"Error getting debug info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get debug info: {str(e)}"
        )
