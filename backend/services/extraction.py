"""
Real declaration extraction from OCR output (no invented values).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from services.ocr import BoundingBox, OCRResult, analyze_readability


@dataclass
class ExtractedDeclaration:
    field_key: str
    field_label: str
    value: str | None
    confidence: float
    found: bool
    status: str  # DETECTED | NOT_DETECTED | LOW_CONFIDENCE | NOT_APPLICABLE


def _normalize(text: str) -> str:
    text = text.replace("₹", " Rs ")
    text = text.replace("—", "-").replace("–", "-")
    text = text.replace("&", " & ")
    # Fix common OCR splits: "Rs.40" already ok; join "m r p"
    text = re.sub(r"(?i)\bm\s*r\s*p\b", "MRP", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _nearby_text(boxes: list[BoundingBox], idx: int, radius_y: float = 55) -> str:
    if idx < 0 or idx >= len(boxes):
        return ""
    anchor = boxes[idx]
    parts = [anchor.text]
    for j, b in enumerate(boxes):
        if j == idx:
            continue
        if abs(b.y - anchor.y) <= radius_y:
            parts.append(b.text)
    # also next line below
    for j, b in enumerate(boxes):
        if j == idx:
            continue
        if 0 < (b.y - anchor.y) <= 90 and abs(b.x - anchor.x) < 250:
            parts.append(b.text)
    return " ".join(parts)


FIELD_SPECS: list[dict[str, Any]] = [
    {
        "field_key": "product_name",
        "field_label": "Product Name",
        "patterns": [],
        "special": "product_name",
    },
    {
        "field_key": "mrp",
        "field_label": "MRP",
        "patterns": [
            r"(?i)\b(?:m\.?\s*r\.?\s*p\.?|maximum\s*retail\s*price)\b\s*[:\-]?\s*(?:rs\.?|inr)?\s*([0-9]+(?:[.,][0-9]{1,2})?)",
            r"(?i)(?:rs\.?|inr)\s*\.?\s*([0-9]+(?:[.,][0-9]{1,2})?).{0,60}(?:incl|inclusive|all\s*taxes|tax)",
            r"(?i)(?:price|mrp).{0,12}(?:rs\.?|inr)?\s*([0-9]+(?:[.,][0-9]{1,2})?)",
        ],
        "keywords": ["mrp", "maximum retail", "incl. of all taxes", "inclusive of all taxes"],
    },
    {
        "field_key": "net_quantity",
        "field_label": "Net Quantity",
        "patterns": [
            r"(?i)\bnet\s*(?:qty|quantity|wt\.?|weight|content|vol\.?|volume)?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?\s*(?:kg|g|gm|grams?|ml|m\.?l\.?|l|ltr|litre|liter|pcs|n))",
            r"(?i)\b([0-9]+(?:\.[0-9]+)?\s*(?:kg|g|gm|ml|m\.?l\.?|ltr|litre|liter))\b",
            r"(?i)\b([0-9]+(?:\.[0-9]+)?)\s*(kg|g|gm|ml|ltr|l)\b",
        ],
        "keywords": ["net qty", "net quantity", "net wt", "net weight", "net vol"],
    },
    {
        "field_key": "manufacturer",
        "field_label": "Manufacturer",
        "patterns": [
            r"(?i)(?:manufactured\s*by|mfd\.?\s*by|mfr\.?\s*by|manufacturer|mfg\.?\s*by)\s*[:\-]?\s*([^\n]{3,80})",
        ],
        "keywords": ["manufactured by", "mfd by", "mfg by", "manufacturer"],
    },
    {
        "field_key": "packer",
        "field_label": "Packer",
        "patterns": [
            r"(?i)(?:packed\s*by|packer|pkd\.?\s*by)\s*[:\-]?\s*(.+)",
        ],
        "keywords": ["packed by", "packer", "pkd by"],
        "optional_entity": True,
    },
    {
        "field_key": "importer",
        "field_label": "Importer",
        "patterns": [
            r"(?i)(?:imported\s*by|importer)\s*[:\-]?\s*(.+)",
        ],
        "keywords": ["imported by", "importer"],
        "optional_entity": True,
    },
    {
        "field_key": "manufacturing_information",
        "field_label": "Manufacturing / Packing / Import Information",
        "patterns": [
            r"(?i)(?:mfd\.?|manufactured(?:\s*on|\s*date)?|date\s*of\s*manufacture|pkd\.?|packed(?:\s*on)?|packing\s*date|import(?:ed)?(?:\s*on|\s*month|\s*date)?|month(?:\s*&\s*|\s*/\s*)year\s*of\s*(?:mfg|manufacture|import|packing))\s*[:\-]?\s*([A-Za-z0-9/\-\s,]{2,40})",
            # Bare month/year often printed near batch codes
            r"(?i)\b((?:0?[1-9]|1[0-2])[/\-.](?:20)?[0-9]{2})\b",
            r"(?i)\b((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s\-/.]*20[0-9]{2})\b",
        ],
        "keywords": ["mfd", "pkd", "manufactured", "import month", "mfg"],
    },
    {
        "field_key": "consumer_care",
        "field_label": "Consumer Care",
        "patterns": [
            r"(?i)(?:customer\s*care|consumer\s*care|helpline|for\s*complaints|toll[\-\s]?free|care\s*(?:no\.?|number|email)?)\s*[:\-]?\s*(.+)",
            r"(?i)\b((?:1800|1860|18600)[\-\s]?[0-9]{2,4}[\-\s]?[0-9]{3,4}[\-\s]?[0-9]{0,4})\b",
            r"(?i)\b(\+?91[\-\s]?[6-9][0-9]{9})\b",
            r"(?i)\b([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})\b",
        ],
        "keywords": ["customer care", "consumer care", "helpline", "toll free"],
    },
    {
        "field_key": "country_of_origin",
        "field_label": "Country of Origin",
        "patterns": [
            r"(?i)(?:country\s*of\s*origin|made\s*in|origin)\s*[:\-]?\s*([A-Za-z ]{2,40})",
        ],
        "keywords": ["country of origin", "made in"],
        "optional_entity": True,
    },
]


SKIP_NAME_KEYWORDS = re.compile(
    r"(?i)\b(mrp|net\s*qty|net\s*quantity|manufactur|packed|imported|customer|consumer|country|mfd|pkd|best\s*before|expiry|inclusive|tax|helpline|anti[\-\s]?dandruff)\b"
)


def _clean_entity_value(value: str) -> str:
    value = re.split(
        r"(?i)\b(?:mfd\.?|pkd\.?|customer\s*care|consumer\s*care|country\s*of\s*origin|net\s*qty|mrp|best\s*before)\b",
        value,
        maxsplit=1,
    )[0]
    value = re.sub(r"\s+", " ", value).strip(" :-|,;")
    return value[:120]


def _match_patterns(text: str, patterns: list[str]) -> tuple[str | None, float]:
    for i, pattern in enumerate(patterns):
        m = re.search(pattern, text)
        if not m:
            continue
        if m.lastindex and m.lastindex >= 2 and m.group(2) and ("kg|g|gm|ml" in pattern or "ltr|litre" in pattern):
            value = f"{m.group(1)} {m.group(2)}".strip()
        else:
            value = m.group(1).strip() if m.lastindex else m.group(0).strip()
        value = _clean_entity_value(value)
        if value.lower() in {"by", "on", "of", "date", "the"}:
            continue
        if value:
            return value, round(max(0.55, 0.93 - i * 0.06), 2)
    return None, 0.0


def _search_with_boxes(
    raw_text: str,
    boxes: list[BoundingBox],
    patterns: list[str],
    keywords: list[str] | None = None,
) -> tuple[str | None, float]:
    flat = _flat(raw_text)
    value, conf = _match_patterns(flat, patterns)
    if not value:
        value, conf = _match_patterns(raw_text, patterns)
    if value:
        if keywords and boxes:
            joined = " ".join(b.text for b in boxes).lower()
            if any(k in joined for k in keywords):
                conf = min(0.99, conf + 0.03)
        return value, conf

    if keywords and boxes:
        for i, b in enumerate(boxes):
            low = b.text.lower()
            if any(k in low for k in keywords):
                local = _nearby_text(boxes, i)
                value, conf = _match_patterns(_flat(local), patterns)
                if value:
                    box_conf = b.confidence if b.confidence else 0.6
                    return value, round(min(0.95, max(conf, box_conf)), 2)
                if ":" in b.text:
                    tail = _clean_entity_value(b.text.split(":", 1)[1])
                    if len(tail) >= 2:
                        return tail, round(max(0.55, b.confidence or 0.6), 2)
    return None, 0.0


def _extract_product_name(raw_text: str, boxes: list[BoundingBox]) -> tuple[str | None, float]:
    stop = re.compile(
        r"(?i)\b(mrp|net\s*qty|net\s*quantity|net\s*wt|manufactur|packed\s*by|imported\s*by|customer\s*care|consumer\s*care|country\s*of|mfd|pkd|best\s*before|inclusive|plot\s*\d)\b"
    )
    product_type = re.compile(r"(?i)\b(shampoo|soap|oil|cream|biscuit|rice|atta|gel|lotion|coffee|juice)\b")

    if boxes:
        top = sorted(boxes, key=lambda b: (b.y, -b.h * b.w))
        brand_parts: list[str] = []
        confs: list[float] = []
        y0 = None
        for b in top:
            t = b.text.strip()
            if len(t) < 2:
                continue
            if stop.search(t) and not product_type.search(t):
                if brand_parts:
                    break
                continue
            if re.fullmatch(r"[\d\W]+", t):
                continue
            if y0 is None:
                y0 = b.y
            elif b.y - y0 > 160:
                break
            brand_parts.append(t)
            confs.append(b.confidence or 0.6)
            if len(brand_parts) >= 3:
                break
        if brand_parts:
            name = _flat(" ".join(brand_parts))
            return name[:80], round(max(0.55, min(0.92, sum(confs) / len(confs))), 2)

    for line in raw_text.splitlines():
        line = line.strip()
        if len(line) >= 3 and not stop.search(line):
            return line[:80], 0.55
    return None, 0.0


def coverage_hint(raw_text: str, declarations: list[ExtractedDeclaration]) -> str | None:
    """Advise user when statutory panel text is missing from the photo."""
    text = (raw_text or "").lower()
    has_mrp = "mrp" in text or "maximum retail" in text
    has_qty = bool(re.search(r"net\s*(qty|quantity|wt|weight)|\b\d+\s*(ml|g|kg|l)\b", text))
    has_mfg = bool(re.search(r"manufactur|mfd|packed by|imported by|pkd", text))
    has_care = bool(re.search(r"customer care|consumer care|helpline|1800|@", text))

    missing_core = [
        d.field_key
        for d in declarations
        if d.field_key in {"mrp", "net_quantity", "consumer_care", "manufacturing_information"}
        and not d.found
    ]
    if len(missing_core) >= 3 and not (has_mrp and has_qty and has_mfg):
        return (
            "Is photo mein Legal Metrology declarations (MRP / Net Qty / Manufacturer / Consumer Care) "
            "kaafi kam dikh rahe hain. Brand/front side ke bajay package ke BACK ya SIDE label ki "
            "clear photo upload karein jahan MRP, Net Quantity aur address printed ho."
        )
    if not has_mrp and not has_qty and not has_care:
        return (
            "OCR ne mainly branding text padha. Statutory panel (MRP, Net Qty, Mfd/Pkd, Care) "
            "wali clear label photo try karein — usually bottle/pack ke peeche."
        )
    return None


def extract_declarations(ocr: OCRResult | str) -> list[ExtractedDeclaration]:
    if isinstance(ocr, str):
        raw_text = _normalize(ocr)
        boxes: list[BoundingBox] = []
        readability = {
            "status": "WARNING",
            "value": "Manual verification required",
            "confidence": 0.0,
            "message": "OCR boxes unavailable.",
            "label": "Readability Screening",
        }
    else:
        raw_text = _normalize(ocr.raw_text or "")
        boxes = list(ocr.boxes or [])
        readability = analyze_readability(ocr)

    results: list[ExtractedDeclaration] = []
    optional_keys = {s["field_key"] for s in FIELD_SPECS if s.get("optional_entity")}

    for spec in FIELD_SPECS:
        if spec.get("special") == "product_name":
            value, conf = _extract_product_name(raw_text, boxes)
        else:
            value, conf = _search_with_boxes(
                raw_text,
                boxes,
                spec.get("patterns", []),
                spec.get("keywords"),
            )

        if value:
            status = "DETECTED" if conf >= 0.55 else "LOW_CONFIDENCE"
            found = True
        else:
            value = None
            conf = 0.0
            found = False
            # Optional entity fields should not look like hard failures in the table
            status = "NOT_APPLICABLE" if spec["field_key"] in optional_keys else "NOT_DETECTED"

        results.append(
            ExtractedDeclaration(
                field_key=spec["field_key"],
                field_label=spec["field_label"],
                value=value,
                confidence=conf,
                found=found,
                status=status,
            )
        )

    known_vals = {d.value.lower() for d in results if d.value}
    extras: list[str] = []
    for line in raw_text.splitlines():
        ln = line.strip()
        if len(ln) < 4:
            continue
        if ln.lower() in known_vals:
            continue
        if re.search(
            r"(?i)best\s*before|expiry|use\s*by|batch|lot\s*no|fssai|veg|non[\-\s]?veg|anti[\-\s]?dandruff",
            ln,
        ):
            extras.append(ln)
    results.append(
        ExtractedDeclaration(
            field_key="other_relevant_declarations",
            field_label="Other Relevant Declarations",
            value="; ".join(extras[:5]) if extras else None,
            confidence=0.7 if extras else 0.0,
            found=bool(extras),
            status="DETECTED" if extras else "NOT_APPLICABLE",
        )
    )

    results.append(
        ExtractedDeclaration(
            field_key="_readability",
            field_label=readability.get("label", "Readability Screening"),
            value=readability.get("value"),
            confidence=float(readability.get("confidence") or 0),
            found=True,
            status=readability.get("status", "WARNING"),
        )
    )

    return results


def declarations_to_map(
    declarations: list[ExtractedDeclaration],
) -> dict[str, ExtractedDeclaration]:
    return {d.field_key: d for d in declarations}
