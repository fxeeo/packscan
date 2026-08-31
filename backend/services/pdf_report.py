"""PDF inspection report generator using ReportLab (current scan data only)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from database import REPORT_DIR

DISCLAIMER = (
    "This system provides automated compliance screening assistance. "
    "Final legal/enforcement decisions require verification by an authorized officer. "
    "This report is generated from the current scan's real OCR/extraction/rule results "
    "and is not a legal certificate. Readability screening is heuristic and does not "
    "constitute legal font-size determination without physical scale calibration."
)


def generate_pdf_report(
    *,
    scan_id: int,
    product_name: str | None,
    created_at: datetime,
    image_path: str,
    screening_score: float | None,
    status: str,
    passed_count: int,
    warning_count: int,
    failed_count: int,
    extracted_fields: list[dict],
    violations: list[dict],
    evidence_image_path: str | None = None,
    ocr_engine: str | None = None,
    not_detected_count: int = 0,
) -> Path:
    REPORT_DIR.mkdir(exist_ok=True)
    out_path = REPORT_DIR / f"packscan_report_{scan_id}.pdf"

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"PackScan Inspection Report #{scan_id}",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "PackTitle",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=colors.HexColor("#0B3A6E"),
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    subtitle = ParagraphStyle(
        "PackSub",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#334155"),
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    h2 = ParagraphStyle(
        "PackH2",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=colors.HexColor("#0B3A6E"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body = ParagraphStyle(
        "PackBody",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1e293b"),
    )
    small = ParagraphStyle(
        "PackSmall",
        parent=styles["Normal"],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#475569"),
        alignment=TA_JUSTIFY,
    )

    story: list = []
    story.append(Paragraph("PackScan", title_style))
    story.append(
        Paragraph(
            "Automated Packaged Commodity Compliance Screening Report<br/>"
            "SIH26034 — Legal Metrology (Packaged Commodities) Rules, 2011 (Prototype)",
            subtitle,
        )
    )

    meta = [
        ["Scan ID", str(scan_id)],
        ["Scan Date/Time", created_at.strftime("%Y-%m-%d %H:%M:%S UTC")],
        ["Product", product_name or "Not detected"],
        ["OCR Engine", ocr_engine or "n/a"],
        ["Automated Screening Score", f"{int(screening_score or 0)} / 100"],
        ["Status", status],
        [
            "Passed / Warnings / Failed / Not Detected",
            f"{passed_count} / {warning_count} / {failed_count} / {not_detected_count}",
        ],
    ]
    meta_table = Table(meta, colWidths=[60 * mm, 110 * mm])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8F1FB")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("Product Image", h2))
    img_file = Path(image_path)
    if img_file.exists():
        try:
            img = Image(str(img_file))
            img._restrictSize(120 * mm, 70 * mm)
            story.append(img)
        except Exception:
            story.append(Paragraph("Image could not be embedded.", body))
    else:
        story.append(Paragraph("Image file not found.", body))

    evidence = Path(evidence_image_path) if evidence_image_path else None
    if evidence and evidence.exists() and evidence.resolve() != img_file.resolve():
        story.append(Paragraph("OCR Evidence (annotated)", h2))
        try:
            eimg = Image(str(evidence))
            eimg._restrictSize(120 * mm, 70 * mm)
            story.append(eimg)
        except Exception:
            story.append(Paragraph("Annotated evidence could not be embedded.", body))

    story.append(Paragraph("Extracted Declarations", h2))
    field_rows = [["Field", "Value", "Confidence", "Status"]]
    for f in extracted_fields:
        field_rows.append(
            [
                f.get("field_label", ""),
                Paragraph(str(f.get("value") or "—"), body),
                f"{int((f.get('confidence') or 0) * 100)}%",
                f.get("status", ""),
            ]
        )
    fields_table = Table(field_rows, colWidths=[45 * mm, 75 * mm, 25 * mm, 25 * mm])
    fields_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3A6E")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(fields_table)

    warns = [v for v in violations if v.get("status") == "WARNING"]
    fails = [v for v in violations if v.get("status") in ("FAIL", "NOT_DETECTED")]
    na = [v for v in violations if v.get("status") == "NOT_APPLICABLE"]

    story.append(Paragraph("Warnings", h2))
    if warns:
        for w in warns:
            story.append(
                Paragraph(
                    f"<b>[{w.get('severity')}] {w.get('rule_id')}</b> — {w.get('message')}",
                    body,
                )
            )
            story.append(Paragraph(f"Recommendation: {w.get('recommendation')}", small))
            story.append(Spacer(1, 3))
    else:
        story.append(Paragraph("No warnings recorded.", body))

    story.append(Paragraph("Violations / Not Detected", h2))
    if fails:
        for v in fails:
            story.append(
                Paragraph(
                    f"<b>[{v.get('severity')}] {v.get('rule_id')}</b> — {v.get('message')}",
                    body,
                )
            )
            story.append(Paragraph(f"Recommendation: {v.get('recommendation')}", small))
            story.append(Spacer(1, 3))
    else:
        story.append(Paragraph("No failed / not-detected mandatory checks recorded.", body))

    if na:
        story.append(Paragraph("Not Applicable / Needs Applicability Check", h2))
        for v in na:
            story.append(Paragraph(f"{v.get('rule_id')}: {v.get('message')}", body))

    story.append(Paragraph("Recommendations Summary", h2))
    recs = [v for v in violations if v.get("status") in ("FAIL", "WARNING", "NOT_DETECTED")]
    if recs:
        for i, r in enumerate(recs, 1):
            story.append(Paragraph(f"{i}. {r.get('recommendation')}", body))
    else:
        story.append(Paragraph("No corrective actions suggested by automated screening.", body))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Disclaimer", h2))
    story.append(Paragraph(DISCLAIMER, small))

    doc.build(story)
    return out_path
