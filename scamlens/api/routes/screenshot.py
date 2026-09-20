import asyncio

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from scamlens.api.schemas import OCRResponse
from scamlens.screenshot_analysis import (
    MAX_UPLOAD_BYTES,
    OCRProcessingError,
    ScreenshotValidationError,
    extract_english_text,
    validate_screenshot,
)

router = APIRouter()


async def _extract_without_blocking(screenshot, timeout_seconds: int):
    return await asyncio.to_thread(extract_english_text, screenshot, timeout_seconds)


@router.post("/ocr", response_model=OCRResponse)
async def ocr(request: Request, file: UploadFile = File(...)) -> OCRResponse:
    # UploadFile.size is computed by the multipart parser from bytes received; it
    # does not trust the part's declared Content-Length. The stream read remains
    # bounded because multipart parsing has already occurred at this layer.
    if file.size is not None and file.size > MAX_UPLOAD_BYTES:
        await file.close()
        raise HTTPException(status_code=422, detail="Screenshot exceeds the 5 MiB upload limit.")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()
    capacity = request.app.state.ocr_capacity
    if not await capacity.try_acquire():
        raise HTTPException(status_code=503, detail="Local OCR is busy. Wait briefly and try again.")
    try:
        screenshot = validate_screenshot(data, file.content_type or "")
        text = await _extract_without_blocking(
            screenshot, request.app.state.settings.ocr_execution_timeout_seconds
        )
    except ScreenshotValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except OCRProcessingError as error:
        raise HTTPException(status_code=503, detail="Local OCR could not process this screenshot.") from error
    finally:
        await capacity.release()
    return OCRResponse(
        extracted_text=text,
        usable_text=bool(text.strip()),
        limitations=[
            "English-only local OCR can make transcription errors; review and edit the text before analysis.",
            "OCR does not classify the screenshot or extracted text automatically.",
            "The application does not intentionally persist or log screenshots or OCR text.",
        ],
    )
