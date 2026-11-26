from __future__ import annotations
import io
import logging
import re
import zlib
from typing import Optional

logger = logging.getLogger(__name__)


def _extract_text_from_pdf_stream_fallback(file_bytes: bytes, filename: str) -> str:
    """Robust fallback stream reader for PDFs when pypdf is not installed or raises."""
    extracted_chunks: list[str] = []

    # 1. Search for FlateDecode or uncompressed streams
    # Standard PDF streams: stream ... endstream
    stream_pattern = re.compile(rb"stream[\r\n]+(.*?)[\r\n]+endstream", re.DOTALL)
    for match in stream_pattern.finditer(file_bytes):
        stream_data = match.group(1)
        decompressed: Optional[bytes] = None

        # Try zlib decompression
        try:
            decompressed = zlib.decompress(stream_data)
        except Exception:
            try:
                decompressed = zlib.decompress(stream_data, -15)
            except Exception:
                decompressed = stream_data

        if decompressed:
            # Extract strings in parentheses: (Text) Tj or [(T) -10 (ext)] TJ
            tj_matches = re.findall(rb"\(([^)]+)\)", decompressed)
            for m in tj_matches:
                try:
                    decoded = m.decode("utf-8", errors="ignore").strip()
                    if decoded and len(decoded) > 1:
                        extracted_chunks.append(decoded)
                except Exception:
                    continue

    # 2. Direct string regex over the raw byte buffer if streams yielded nothing
    if not extracted_chunks:
        # Match printable sequences of ASCII/UTF-8 characters of reasonable length
        raw_matches = re.findall(rb"[a-zA-Z0-9\s.,;:'\"()\-/#]{4,}", file_bytes)
        # Exclude common PDF syntax keywords
        pdf_keywords = {
            b"obj", b"endobj", b"stream", b"endstream", b"xref", b"trailer",
            b"startxref", b"Catalog", b"Pages", b"Page", b"Parent", b"Kids",
            b"Count", b"MediaBox", b"Resources", b"Font", b"Type", b"Subtype",
            b"FlateDecode", b"Length", b"Width", b"Height", b"BitsPerComponent",
        }
        for rm in raw_matches:
            stripped = rm.strip()
            if stripped not in pdf_keywords and not stripped.startswith(b"/"):
                try:
                    s = stripped.decode("utf-8", errors="ignore").strip()
                    if len(s) > 3 and not all(c in "%/<>()[]{}" for c in s):
                        extracted_chunks.append(s)
                except Exception:
                    continue

    if extracted_chunks:
        return " ".join(extracted_chunks).strip()

    return f"[PDF_DOCUMENT: {filename} (size: {len(file_bytes)} bytes) - Scanned or image-only PDF document]"


def _extract_text_from_image_fallback(file_bytes: bytes, filename: str) -> str:
    """Heuristic text / metadata extractor for scanned image files."""
    chunks: list[str] = []
    # Search for embedded UTF-8 / ASCII text strings (such as EXIF, IPTC, or OCR annotations)
    raw_matches = re.findall(rb"[a-zA-Z0-9\s.,;:'\"()\-/#]{4,}", file_bytes)
    image_magic_keywords = {b"JFIF", b"Exif", b"Photoshop", b"IHDR", b"IDAT", b"IEND"}
    for rm in raw_matches:
        stripped = rm.strip()
        if stripped not in image_magic_keywords:
            try:
                s = stripped.decode("utf-8", errors="ignore").strip()
                if len(s) > 4:
                    chunks.append(s)
            except Exception:
                continue

    if chunks:
        return " ".join(chunks[:20]).strip()

    return f"[IMAGE_DOCUMENT: {filename} (size: {len(file_bytes)} bytes) - Scanned property document image]"


async def extract_text_from_file_buffer(file_bytes: bytes, filename: str) -> str:
    """Extracts readable text from PDF and image file buffers.
    
    Pipeline:
    1. PDFs: Attempts pypdf parsing if installed; falls back to robust stream extraction.
    2. Images (.png, .jpg, .jpeg, etc.): Attempts pytesseract OCR if installed;
       falls back to heuristic string extraction / structured document placeholders.
    3. Plain text / CSV / JSON: Direct UTF-8 decode.
    4. Corrupt or empty buffers: Graceful readable placeholder strings.
    """
    if not file_bytes:
        return f"[EMPTY_DOCUMENT: {filename}]"

    fn_lower = (filename or "").lower()

    # --- 1. PDF Documents ---
    if fn_lower.endswith(".pdf") or file_bytes.startswith(b"%PDF"):
        # Try pypdf if installed
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            pages_text = []
            for page in reader.pages:
                txt = page.extract_text()
                if txt and txt.strip():
                    pages_text.append(txt.strip())
            if pages_text:
                return "\n\n".join(pages_text)
        except Exception as e:
            logger.debug("pypdf extraction failed or not available for %s: %s", filename, e)

        # Fallback stream parser
        try:
            fallback_text = _extract_text_from_pdf_stream_fallback(file_bytes, filename)
            if fallback_text:
                return fallback_text
        except Exception as e:
            logger.warning("Stream fallback failed for %s: %s", filename, e)

        return f"[PDF_DOCUMENT: {filename} (size: {len(file_bytes)} bytes)]"

    # --- 2. Image Files ---
    image_exts = (".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp")
    is_image = any(fn_lower.endswith(ext) for ext in image_exts) or file_bytes.startswith((b"\x89PNG", b"\xff\xd8\xff", b"GIF8"))
    if is_image:
        try:
            from PIL import Image
            import pytesseract
            img = Image.open(io.BytesIO(file_bytes))
            ocr_text = pytesseract.image_to_string(img)
            if ocr_text and ocr_text.strip():
                return ocr_text.strip()
        except Exception as e:
            logger.debug("pytesseract OCR extraction failed or not available for %s: %s", filename, e)

        # Fallback image heuristic
        try:
            return _extract_text_from_image_fallback(file_bytes, filename)
        except Exception as e:
            logger.warning("Image fallback failed for %s: %s", filename, e)
            return f"[IMAGE_DOCUMENT: {filename} (size: {len(file_bytes)} bytes)]"

    # --- 3. Text / Structured Files ---
    try:
        decoded = file_bytes.decode("utf-8", errors="replace").strip()
        if decoded:
            return decoded
    except Exception:
        pass

    return f"[DOCUMENT: {filename} (size: {len(file_bytes)} bytes)]"
