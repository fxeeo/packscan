"""
Real OCR service for PackScan.

Pipeline:
  image → OpenCV preprocess → PaddleOCR (preferred) / Tesseract (fallback)

Independently testable:
  python -m services.ocr path/to/image.jpg
"""

from __future__ import annotations

import json
import os
import re
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from services.image_preprocess import (
    draw_ocr_boxes,
    estimate_contrast,
    load_image,
    make_ocr_variants,
    preprocess_image,
)


@dataclass
class BoundingBox:
    text: str
    confidence: float
    x: float = 0.0
    y: float = 0.0
    w: float = 0.0
    h: float = 0.0


@dataclass
class OCRResult:
    raw_text: str
    boxes: list[BoundingBox] = field(default_factory=list)
    engine_name: str = "unknown"
    notes: str = ""
    success: bool = True
    error: str | None = None
    processed_image_path: str | None = None
    annotated_image_path: str | None = None
    mean_confidence: float = 0.0
    contrast_score: float = 0.0
    avg_box_height_px: float = 0.0


class OCRError(Exception):
    """Raised when OCR cannot produce usable text."""


_PADDLE_INSTANCE = None


def _quad_to_xywh(quad: list[list[float]]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in quad]
    ys = [p[1] for p in quad]
    x1, x2 = min(xs), max(xs)
    y1, y2 = min(ys), max(ys)
    return float(x1), float(y1), float(max(1.0, x2 - x1)), float(max(1.0, y2 - y1))


def _get_paddle():
    global _PADDLE_INSTANCE
    if _PADDLE_INSTANCE is not None:
        return _PADDLE_INSTANCE
    from paddleocr import PaddleOCR

    # Compatible init across paddleocr 2.x variants
    try:
        _PADDLE_INSTANCE = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    except TypeError:
        try:
            _PADDLE_INSTANCE = PaddleOCR(use_textline_orientation=True, lang="en")
        except TypeError:
            _PADDLE_INSTANCE = PaddleOCR(lang="en")
    return _PADDLE_INSTANCE


def _run_paddle(processed_path: Path) -> tuple[list[BoundingBox], str]:
    ocr = _get_paddle()
    # Prefer ocr() API used by 2.x
    result = ocr.ocr(str(processed_path), cls=True)
    boxes: list[BoundingBox] = []
    lines: list[str] = []

    # result can be list[page] where page is list of [box, (text, conf)]
    pages = result if isinstance(result, list) else []
    for page in pages:
        if not page:
            continue
        for item in page:
            if not item or len(item) < 2:
                continue
            quad = item[0]
            text_info = item[1]
            if isinstance(text_info, (list, tuple)):
                text = str(text_info[0]).strip()
                conf = float(text_info[1]) if len(text_info) > 1 else 0.0
            else:
                text = str(text_info).strip()
                conf = 0.0
            if not text:
                continue
            x, y, w, h = _quad_to_xywh(quad)
            boxes.append(BoundingBox(text=text, confidence=round(conf, 4), x=x, y=y, w=w, h=h))
            lines.append(text)

    return boxes, "\n".join(lines)


def _run_tesseract(processed_path: Path) -> tuple[list[BoundingBox], str]:
    import pytesseract
    from pytesseract import Output

    image = load_image(processed_path)
    data = pytesseract.image_to_data(image, output_type=Output.DICT)
    boxes: list[BoundingBox] = []
    lines_map: dict[tuple[int, int], list[str]] = {}
    n = len(data.get("text", []))
    for i in range(n):
        text = (data["text"][i] or "").strip()
        conf_raw = data["conf"][i]
        try:
            conf = float(conf_raw) / 100.0 if float(conf_raw) >= 0 else 0.0
        except Exception:
            conf = 0.0
        if not text:
            continue
        x, y, w, h = (
            float(data["left"][i]),
            float(data["top"][i]),
            float(data["width"][i]),
            float(data["height"][i]),
        )
        boxes.append(BoundingBox(text=text, confidence=round(conf, 4), x=x, y=y, w=w, h=h))
        key = (int(data["block_num"][i]), int(data["line_num"][i]))
        lines_map.setdefault(key, []).append(text)
    ordered = [" ".join(words) for _, words in sorted(lines_map.items())]
    return boxes, "\n".join(ordered)


def detect_available_engine() -> str:
    preferred = os.getenv("PACKSCAN_OCR_ENGINE", "auto").lower().strip()
    if preferred in {"paddle", "tesseract"}:
        return preferred
    try:
        import paddleocr  # noqa: F401
        import paddle  # noqa: F401

        return "paddle"
    except Exception:
        pass
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return "tesseract"
    except Exception as exc:
        raise OCRError(
            "No OCR engine available. Install PaddleOCR (preferred) or Tesseract+pytesseract."
        ) from exc


def _merge_box_sets(sets: list[list[BoundingBox]]) -> list[BoundingBox]:
    """Merge OCR passes; keep higher-confidence near-duplicates."""
    merged: list[BoundingBox] = []
    for boxes in sets:
        for b in boxes:
            key = re.sub(r"\s+", " ", b.text.lower()).strip()
            if len(key) < 1:
                continue
            dup = None
            for m in merged:
                mk = re.sub(r"\s+", " ", m.text.lower()).strip()
                if key == mk or (key in mk or mk in key) and abs(m.y - b.y) < 25:
                    dup = m
                    break
            if dup is None:
                merged.append(b)
            elif b.confidence > dup.confidence:
                dup.text = b.text
                dup.confidence = b.confidence
                dup.x, dup.y, dup.w, dup.h = b.x, b.y, b.w, b.h
    merged.sort(key=lambda x: (x.y, x.x))
    return merged


def run_ocr(
    image_path: str | Path,
    *,
    annotate: bool = True,
    engine: str | None = None,
) -> OCRResult:
    src = Path(image_path)
    if not src.exists():
        raise OCRError(f"Image not found: {src}")

    variants = make_ocr_variants(src)
    processed_path = variants[-1][1]
    processed_img = load_image(processed_path)
    contrast = estimate_contrast(processed_img)
    engine_name = engine or detect_available_engine()

    box_sets: list[list[BoundingBox]] = []
    last_error: Exception | None = None

    for label, path in variants:
        try:
            if engine_name == "paddle":
                boxes, _ = _run_paddle(path)
            elif engine_name == "tesseract":
                boxes, _ = _run_tesseract(path)
            else:
                raise OCRError(f"Unknown OCR engine: {engine_name}")
            box_sets.append(boxes)
        except OCRError:
            raise
        except Exception as exc:
            last_error = exc
            continue

    if not box_sets:
        if engine_name == "paddle":
            try:
                boxes, _ = _run_tesseract(processed_path)
                box_sets.append(boxes)
                engine_name = "tesseract"
            except Exception as exc2:
                raise OCRError(
                    f"OCR failed (paddle: {last_error}; tesseract: {exc2})"
                ) from exc2
        else:
            raise OCRError(f"OCR failed ({engine_name}): {last_error}")

    boxes = _merge_box_sets(box_sets)
    raw_text = "\n".join(b.text for b in boxes).strip()
    mean_conf = (
        round(sum(b.confidence for b in boxes) / len(boxes), 4) if boxes else 0.0
    )
    avg_h = round(sum(b.h for b in boxes) / len(boxes), 2) if boxes else 0.0

    annotated_path = None
    if annotate and boxes:
        annotated_path = str(
            draw_ocr_boxes(
                src,
                [asdict(b) for b in boxes],
                src.with_name(f"{src.stem}_annotated.png"),
            )
        )

    success = bool(raw_text) and len(raw_text) >= 3
    notes = (
        f"Engine={engine_name}; passes={len(box_sets)}; boxes={len(boxes)}; "
        f"contrast={contrast:.3f}; avg_box_h_px={avg_h}"
    )
    error = None if success else "No readable text detected after OCR."

    return OCRResult(
        raw_text=raw_text,
        boxes=boxes,
        engine_name=engine_name,
        notes=notes,
        success=success,
        error=error,
        processed_image_path=str(processed_path),
        annotated_image_path=annotated_path,
        mean_confidence=mean_conf,
        contrast_score=round(contrast, 4),
        avg_box_height_px=avg_h,
    )


def analyze_readability(ocr: OCRResult) -> dict[str, Any]:
    """
    Readability screening from OCR boxes + contrast.
    Does NOT claim legal font-size compliance without physical scale calibration.
    """
    if not ocr.success or not ocr.boxes:
        return {
            "status": "WARNING",
            "label": "Readability Screening",
            "value": "Manual verification required",
            "confidence": 0.0,
            "message": "Insufficient OCR regions for automated readability screening. Manual verification required.",
            "avg_box_height_px": ocr.avg_box_height_px,
            "contrast_score": ocr.contrast_score,
            "physical_font_claim": False,
        }

    avg_h = ocr.avg_box_height_px
    contrast = ocr.contrast_score
    mean_conf = ocr.mean_confidence

    # Heuristic only — pixel height ≠ legal printed mm without calibration
    if mean_conf >= 0.75 and contrast >= 0.12 and avg_h >= 14:
        status = "PASS"
        value = "Adequate for automated screening"
        message = (
            "Detected text regions appear sufficiently large/contrasty for OCR screening. "
            "This is NOT a legal font-size determination (no physical scale calibration)."
        )
        conf = min(0.95, 0.55 + mean_conf * 0.3 + min(avg_h, 40) / 120)
    elif mean_conf >= 0.45 and contrast >= 0.08:
        status = "WARNING"
        value = "Manual verification required"
        message = (
            "OCR confidence/contrast is moderate. Manual verification of label readability is required. "
            "Pixel measurements are not equivalent to statutory font size."
        )
        conf = 0.45
    else:
        status = "WARNING"
        value = "Manual verification required"
        message = (
            "Low OCR confidence or weak contrast. Manual verification required. "
            "Do not treat this as legal font-size compliance."
        )
        conf = 0.25

    return {
        "status": status,
        "label": "Readability Screening",
        "value": value,
        "confidence": round(conf, 2),
        "message": message,
        "avg_box_height_px": avg_h,
        "contrast_score": contrast,
        "mean_ocr_confidence": mean_conf,
        "physical_font_claim": False,
    }


def result_to_dict(result: OCRResult) -> dict[str, Any]:
    return {
        "raw_text": result.raw_text,
        "engine_name": result.engine_name,
        "notes": result.notes,
        "success": result.success,
        "error": result.error,
        "mean_confidence": result.mean_confidence,
        "contrast_score": result.contrast_score,
        "avg_box_height_px": result.avg_box_height_px,
        "processed_image_path": result.processed_image_path,
        "annotated_image_path": result.annotated_image_path,
        "boxes": [asdict(b) for b in result.boxes],
        "readability": analyze_readability(result),
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m services.ocr <image_path>")
        raise SystemExit(1)
    path = Path(sys.argv[1])
    try:
        out = run_ocr(path)
        print(json.dumps(result_to_dict(out), indent=2, ensure_ascii=False))
    except Exception:
        traceback.print_exc()
        raise SystemExit(2)
