"""
Thumbnail generation service for PDF materials.

Extracts the first page of a PDF and converts it to a JPEG image
using PyMuPDF (fitz) + Pillow. Designed to be called from the
Material model's save() method or a serializer.

Failures are caught and logged so they never break an upload.
"""

import io
import logging
import tempfile
import os

from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


def generate_pdf_thumbnail(pdf_file, material_title: str = "material") -> ContentFile | None:
    """
    Generate a JPEG thumbnail from the first page of a PDF file.

    Args:
        pdf_file: A file-like object (Django InMemoryUploadedFile / opened file).
        material_title: Used to build the thumbnail filename.

    Returns:
        A ``ContentFile`` ready to be assigned to an ``ImageField``,
        or ``None`` if generation fails (so the upload still succeeds).
    """
    try:
        import fitz  # PyMuPDF
        from PIL import Image
    except ImportError:
        logger.warning("PyMuPDF or Pillow is not installed — thumbnail generation skipped.")
        return None

    try:
        # Read the PDF bytes; reset the pointer so the field can still save the original.
        pdf_file.seek(0)
        pdf_bytes = pdf_file.read()
        pdf_file.seek(0)

        # Open PDF from bytes (no temp file needed for reading).
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        if doc.page_count == 0:
            logger.warning("PDF has no pages — thumbnail skipped.")
            doc.close()
            return None

        # Render first page at 2× resolution (144 dpi) for a crisp thumbnail.
        page = doc[0]
        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat)
        doc.close()

        # Convert PyMuPDF pixmap → Pillow Image → JPEG bytes.
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Resize to a standard thumbnail size while keeping aspect ratio.
        img.thumbnail((400, 566))  # roughly A4 portrait proportion

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85, optimize=True)
        buffer.seek(0)

        safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in material_title)
        filename = f"thumb_{safe_title}.jpg"

        return ContentFile(buffer.read(), name=filename)

    except Exception as exc:  # noqa: BLE001
        logger.error("Thumbnail generation failed: %s", exc, exc_info=True)
        return None
