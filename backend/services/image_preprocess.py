"""
OpenCV image preprocessing for PackScan OCR pipeline.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def load_image(image_path: str | Path) -> np.ndarray:
    path = str(image_path)
    image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Unable to read image: {path}")
    return image


def resize_for_ocr(image: np.ndarray, max_side: int = 1800, min_side: int = 900) -> np.ndarray:
    h, w = image.shape[:2]
    longest = max(h, w)
    shortest = min(h, w)
    scale = 1.0
    if longest > max_side:
        scale = max_side / float(longest)
    elif shortest < min_side:
        scale = min_side / float(shortest)
    if abs(scale - 1.0) < 0.01:
        return image
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    interp = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
    return cv2.resize(image, (new_w, new_h), interpolation=interp)


def prepare_color(image: np.ndarray) -> np.ndarray:
    """Mild resize only — often best for PaddleOCR on packaging photos."""
    return resize_for_ocr(image)


def enhance_for_ocr(image: np.ndarray) -> np.ndarray:
    """Light contrast path (avoid heavy denoise that wipes fine print)."""
    image = resize_for_ocr(image)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=1.8, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    # Light unsharp only
    blur = cv2.GaussianBlur(enhanced, (0, 0), sigmaX=0.8)
    sharp = cv2.addWeighted(enhanced, 1.35, blur, -0.35, 0)
    return cv2.cvtColor(sharp, cv2.COLOR_GRAY2BGR)


def save_image(image: np.ndarray, out_path: str | Path) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    ok, buf = cv2.imencode(out.suffix or ".png", image)
    if not ok:
        raise ValueError(f"Failed to encode image for {out}")
    buf.tofile(str(out))
    return out


def make_ocr_variants(image_path: str | Path) -> list[tuple[str, Path]]:
    """
    Build multiple image variants for dual-pass OCR.
    Returns list of (label, path).
    """
    src = Path(image_path)
    image = load_image(src)
    color = prepare_color(image)
    enhanced = enhance_for_ocr(image)

    color_path = src.with_name(f"{src.stem}_ocr_color.png")
    enh_path = src.with_name(f"{src.stem}_preprocessed.png")
    save_image(color, color_path)
    save_image(enhanced, enh_path)
    return [("color", color_path), ("enhanced", enh_path)]


def preprocess_image(image_path: str | Path, processed_path: str | Path | None = None):
    src = Path(image_path)
    image = load_image(src)
    processed = enhance_for_ocr(image)
    if processed_path is None:
        processed_path = src.with_name(f"{src.stem}_preprocessed.png")
    saved = save_image(processed, processed_path)
    return processed, saved


def estimate_contrast(image: np.ndarray) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    return float(np.std(gray) / 255.0)


def draw_ocr_boxes(
    image_path: str | Path,
    boxes: list[dict],
    out_path: str | Path,
) -> Path:
    image = load_image(image_path)
    for b in boxes:
        x, y, w, h = int(b["x"]), int(b["y"]), int(b["w"]), int(b["h"])
        conf = float(b.get("confidence", 0))
        color = (16, 120, 48) if conf >= 0.7 else (0, 140, 220) if conf >= 0.45 else (40, 40, 200)
        cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)
        label = (b.get("text") or "")[:28]
        cv2.putText(
            image,
            label,
            (x, max(12, y - 4)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            color,
            1,
            cv2.LINE_AA,
        )
    return save_image(image, out_path)
