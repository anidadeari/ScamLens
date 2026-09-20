"""Validation and local OCR for user-reviewed screenshot analysis."""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import hashlib
from typing import MutableMapping

from PIL import Image, UnidentifiedImageError
import pytesseract

from scamlens import message_inference


MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
SUPPORTED_FORMATS = {"PNG", "JPEG", "WEBP"}
SUPPORTED_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}
FORMAT_MIME_TYPES = {
    "PNG": {"image/png"},
    "JPEG": {"image/jpeg"},
    "WEBP": {"image/webp"},
}


class ScreenshotValidationError(ValueError):
    """Raised when an upload is not a supported, safely bounded image."""


class OCRProcessingError(RuntimeError):
    """Raised when local OCR cannot complete."""


@dataclass(frozen=True)
class ValidatedScreenshot:
    image: Image.Image
    image_format: str
    sha256: str
    byte_size: int


def validate_screenshot(data: bytes, declared_mime: str) -> ValidatedScreenshot:
    if not isinstance(data, bytes) or not data:
        raise ScreenshotValidationError("Upload a non-empty screenshot file.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ScreenshotValidationError(
            f"Screenshot exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MiB upload limit."
        )
    if declared_mime not in SUPPORTED_MIME_TYPES:
        raise ScreenshotValidationError("Screenshot must be PNG, JPEG/JPG, or WEBP.")
    try:
        with Image.open(BytesIO(data)) as probe:
            image_format = str(probe.format).upper()
            width, height = probe.size
            probe.verify()
        if image_format not in SUPPORTED_FORMATS:
            raise ScreenshotValidationError("Decoded image format is not supported.")
        if declared_mime not in FORMAT_MIME_TYPES[image_format]:
            raise ScreenshotValidationError(
                "The file's declared type does not match its decoded image format."
            )
        if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
            raise ScreenshotValidationError(
                "Decoded screenshot dimensions exceed the 20-megapixel safety limit."
            )
        with Image.open(BytesIO(data)) as decoded:
            decoded.load()
            image = decoded.convert("RGB")
    except ScreenshotValidationError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as error:
        raise ScreenshotValidationError(
            "The screenshot is corrupted or could not be decoded safely."
        ) from error
    return ValidatedScreenshot(
        image=image,
        image_format=image_format,
        sha256=hashlib.sha256(data).hexdigest(),
        byte_size=len(data),
    )


def extract_english_text(screenshot: ValidatedScreenshot, timeout_seconds: int = 15) -> str:
    """Run local English OCR; no preprocessing or external service is used."""
    try:
        return pytesseract.image_to_string(
            screenshot.image, lang="eng", config="--psm 6", timeout=timeout_seconds
        ).strip()
    except (pytesseract.TesseractError, RuntimeError, OSError) as error:
        raise OCRProcessingError("Local OCR could not process this screenshot.") from error


def analyze_reviewed_text(bundle: dict[str, object], reviewed_text: object):
    """Delegate explicit reviewed text analysis to the existing SMS pipeline."""
    return message_inference.predict_message(bundle, reviewed_text)


def apply_ocr_to_state(
    state: MutableMapping[str, object], *, fingerprint: str, text: str
) -> None:
    """Install OCR text for a new image and invalidate any prior analysis."""
    if state.get("screenshot_fingerprint") != fingerprint:
        state["screenshot_fingerprint"] = fingerprint
        state["reviewed_ocr_text"] = text
        clear_analysis_state(state)


def clear_analysis_state(state: MutableMapping[str, object]) -> None:
    state.pop("screenshot_result", None)
    state.pop("analyzed_reviewed_text", None)
