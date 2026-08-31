"""
Create REAL printable sample label images for pipeline testing.
These are not hardcoded OCR results — OCR must actually read the pixels.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent / "test_images"
ROOT.mkdir(parents=True, exist_ok=True)


def _write_label(path: Path, lines: list[str], *, blur: bool = False, wide: bool = False) -> None:
    w, h = (1100, 700) if wide else (900, 1200)
    img = np.full((h, w, 3), 245, dtype=np.uint8)
    cv2.rectangle(img, (20, 20), (w - 20, h - 20), (11, 58, 110), 3)
    y = 70
    for i, line in enumerate(lines):
        scale = 1.1 if i == 0 else 0.75
        thickness = 2 if i == 0 else 1
        cv2.putText(
            img,
            line[:70],
            (50, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            (20, 20, 20),
            thickness,
            cv2.LINE_AA,
        )
        y += 48 if i == 0 else 38
    if blur:
        img = cv2.GaussianBlur(img, (31, 31), 0)
    cv2.imencode(".png", img)[1].tofile(str(path))


def main() -> None:
    _write_label(
        ROOT / "01_complete_biscuit.png",
        [
            "GOLDEN CRISP BISCUITS",
            "Net Qty: 200 g",
            "MRP Rs. 40.00 (inclusive of all taxes)",
            "Manufactured by: Sunrise Foods Pvt Ltd",
            "Plot 12 Industrial Area Indore MP",
            "Mfd: 03/2025",
            "Customer Care: 1800-123-4567",
            "Country of Origin: India",
        ],
    )
    _write_label(
        ROOT / "02_shampoo_with_qty.png",
        [
            "SILKSHINE SHAMPOO",
            "Net Quantity: 340 ml",
            "MRP: Rs 199.00 (incl. of all taxes)",
            "Packed by: AuraCare Cosmetics LLP",
            "Pkd: Jan 2025",
            "Consumer Care: help@auracare.in",
            "Made in India",
        ],
        wide=True,
    )
    _write_label(
        ROOT / "03_incomplete_cream.png",
        [
            "NATURA FACE CREAM",
            "MRP Rs. 249",
            "Net Wt. 50 g",
            "Mfd by Natura Beauty",
            "Mumbai",
        ],
    )
    _write_label(
        ROOT / "04_blurry_oil.png",
        [
            "PURE MUSTARD OIL",
            "Net Qty 1 L",
            "MRP Rs. 185 (inclusive of all taxes)",
            "Manufactured by: Bharat Agro Oils",
            "Mfg Date: 02/2025",
            "Customer Care No.: 1800-222-3344",
            "Country of Origin: India",
        ],
        blur=True,
    )
    _write_label(
        ROOT / "05_coffee_import_layout.png",
        [
            "FRESHBREW INSTANT COFFEE",
            "Net Qty: 100 g",
            "MRP Rs. 320.00 (inclusive of all taxes)",
            "Imported by: BeanWorld Imports Pvt Ltd",
            "Import Month/Year: 12/2024",
            "Customer Care: support@beanworld.in",
            "Country of Origin: Brazil",
        ],
        wide=True,
    )
    print(f"Wrote test images to {ROOT}")


if __name__ == "__main__":
    main()
