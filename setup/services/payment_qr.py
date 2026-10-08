# setup/services/payment_qr.py
"""Checks an uploaded scan-and-pay QR image without changing a single byte of it.

Menu photos are re-encoded on upload (core/validators.process_uploaded_image),
which would blur a QR code's modules. A payment QR has to stay exactly as the
bank or app issued it, so it is only checked to be a real JPEG/PNG/WebP image
of sensible size, then stored as-is.
"""
import io
import uuid

from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError

MAX_BYTES = 5 * 1024 * 1024
FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


class QRImageError(Exception):
    pass


def read_qr_upload(uploaded):
    """Return (filename, ContentFile) holding the original bytes, or raise QRImageError."""
    if uploaded.size > MAX_BYTES:
        raise QRImageError("That QR image is larger than 5 MB. Upload the original image from your UPI app.")
    raw = uploaded.read()
    try:
        with Image.open(io.BytesIO(raw)) as img:
            fmt = img.format
            img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise QRImageError("That file is not an image. Upload the QR as a JPG or PNG.")
    if fmt not in FORMATS:
        raise QRImageError("Upload the QR as a JPG, PNG or WebP image.")
    return f"upi_qr_{uuid.uuid4().hex[:10]}.{FORMATS[fmt]}", ContentFile(raw)
