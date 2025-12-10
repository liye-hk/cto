import io
import logging
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.services.converter import EPUBToPDFConverter, ConversionError

router = APIRouter(prefix="/api", tags=["converter"])
logger = logging.getLogger(__name__)
converter = EPUBToPDFConverter()


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

        # Generate output filename
        input_filename = Path(file.filename or "document").stem
        output_filename = f"{input_filename}.pdf"

        # Return PDF as streaming response
        return StreamingResponse(
            io.BytesIO(pdf_content),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{output_filename}"'},
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
