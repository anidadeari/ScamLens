"""Tests for bounded local screenshot validation, OCR, and review workflow."""
from io import BytesIO

from PIL import Image
import pytest

from scamlens import screenshot_analysis as screenshots


def image_bytes(image_format: str) -> bytes:
    output=BytesIO(); Image.new("RGB",(40,20),"white").save(output,format=image_format); return output.getvalue()


@pytest.mark.parametrize(("image_format","mime"),[("PNG","image/png"),("JPEG","image/jpeg"),("WEBP","image/webp")])
def test_supported_image_validation(image_format,mime):
    result=screenshots.validate_screenshot(image_bytes(image_format),mime)
    assert result.image_format==image_format
    assert result.image.size==(40,20)


def test_corrupt_unsupported_and_mismatched_uploads_are_rejected():
    with pytest.raises(screenshots.ScreenshotValidationError,match="corrupted"):
        screenshots.validate_screenshot(b"not an image","image/png")
    with pytest.raises(screenshots.ScreenshotValidationError,match="must be"):
        screenshots.validate_screenshot(image_bytes("PNG"),"image/gif")
    with pytest.raises(screenshots.ScreenshotValidationError,match="does not match"):
        screenshots.validate_screenshot(image_bytes("PNG"),"image/jpeg")


def test_upload_size_limit_is_enforced_before_decoding():
    with pytest.raises(screenshots.ScreenshotValidationError,match="upload limit"):
        screenshots.validate_screenshot(b"x"*(screenshots.MAX_UPLOAD_BYTES+1),"image/png")


def test_empty_ocr_output_is_returned_for_review_not_analyzed(monkeypatch):
    calls=[]
    monkeypatch.setattr(screenshots.pytesseract,"image_to_string",lambda *args,**kwargs: calls.append(kwargs) or "  \n")
    validated=screenshots.validate_screenshot(image_bytes("PNG"),"image/png")
    assert screenshots.extract_english_text(validated)==""
    assert calls==[{"lang":"eng","config":"--psm 6","timeout":15}]


def test_ocr_state_requires_separate_analysis_and_clears_stale_results(monkeypatch):
    state={"screenshot_result":"old","analyzed_reviewed_text":"old"}
    screenshots.apply_ocr_to_state(state,fingerprint="first",text="OCR draft")
    assert state=={"screenshot_fingerprint":"first","reviewed_ocr_text":"OCR draft"}
    called=[]
    monkeypatch.setattr(screenshots.message_inference,"predict_message",lambda bundle,text: called.append((bundle,text)) or "prediction")
    assert called==[]
    state["reviewed_ocr_text"]="user corrected text"
    result=screenshots.analyze_reviewed_text({"model":True},state["reviewed_ocr_text"])
    assert result=="prediction"
    assert called==[({"model":True},"user corrected text")]
    state.update(screenshot_result=result,analyzed_reviewed_text=state["reviewed_ocr_text"])
    screenshots.clear_analysis_state(state)
    assert "screenshot_result" not in state
    screenshots.apply_ocr_to_state(state,fingerprint="second",text="different OCR")
    assert state["reviewed_ocr_text"]=="different OCR"
