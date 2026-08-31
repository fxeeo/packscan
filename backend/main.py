"""
PackScan FastAPI — real OCR pipeline (no mock/hardcoded compliance results).
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

# Load portable .env before OCR/config reads process env
_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = Path(__file__).resolve().parent
load_dotenv(_ROOT / ".env")
load_dotenv(_BACKEND / ".env")

from config import settings
from database import REPORT_DIR, UPLOAD_DIR, Base, engine, get_db
from models import ExtractedField, Report, Scan, Violation
from schemas import (
    AnalyzeResponse,
    BarcodeUpdate,
    DashboardStats,
    ProductLookupOut,
    ReportOut,
    ScanDetail,
    ScanSummary,
)
from services.compliance import (
    compute_screening_score,
    evaluate_compliance,
    field_status_from_rules,
)
from services.extraction import extract_declarations, coverage_hint
from services.ocr import OCRError, result_to_dict, run_ocr
from services.pdf_report import generate_pdf_report
from services.product_lookup import lookup_product_by_barcode, merge_lookup_into_declarations

# Ensure OCR engine env is visible even if only set via Settings defaults
os.environ.setdefault("PACKSCAN_OCR_ENGINE", settings.packscan_ocr_engine)

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAX_UPLOAD_BYTES = 12 * 1024 * 1024  # 12 MB

app = FastAPI(
    title="PackScan API",
    description="SIH26034 — Real OCR packaged commodity compliance screening prototype",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/reports", StaticFiles(directory=str(REPORT_DIR)), name="reports")


@app.on_event("startup")
def on_startup():
    # Recreate schema for new columns in prototype (safe for local demo DB)
    Base.metadata.create_all(bind=engine)
    # Ensure new columns exist on older SQLite files
    with engine.connect() as conn:
        cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(scans)").fetchall()}
        alters = []
        if "annotated_image_path" not in cols:
            alters.append("ALTER TABLE scans ADD COLUMN annotated_image_path VARCHAR(500)")
        if "processed_image_path" not in cols:
            alters.append("ALTER TABLE scans ADD COLUMN processed_image_path VARCHAR(500)")
        if "not_detected_count" not in cols:
            alters.append("ALTER TABLE scans ADD COLUMN not_detected_count INTEGER DEFAULT 0")
        if "not_applicable_count" not in cols:
            alters.append("ALTER TABLE scans ADD COLUMN not_applicable_count INTEGER DEFAULT 0")
        if "ocr_engine" not in cols:
            alters.append("ALTER TABLE scans ADD COLUMN ocr_engine VARCHAR(50)")
        if "ocr_mean_confidence" not in cols:
            alters.append("ALTER TABLE scans ADD COLUMN ocr_mean_confidence FLOAT")
        if "ocr_json" not in cols:
            alters.append("ALTER TABLE scans ADD COLUMN ocr_json TEXT")
        if "error_message" not in cols:
            alters.append("ALTER TABLE scans ADD COLUMN error_message TEXT")
        if "barcode_value" not in cols:
            alters.append("ALTER TABLE scans ADD COLUMN barcode_value VARCHAR(64)")
        if "barcode_format" not in cols:
            alters.append("ALTER TABLE scans ADD COLUMN barcode_format VARCHAR(32)")
        if "barcode_checksum_valid" not in cols:
            alters.append("ALTER TABLE scans ADD COLUMN barcode_checksum_valid INTEGER")
        if "barcode_gtin" not in cols:
            alters.append("ALTER TABLE scans ADD COLUMN barcode_gtin VARCHAR(14)")
        if "barcode_raw" not in cols:
            alters.append("ALTER TABLE scans ADD COLUMN barcode_raw VARCHAR(128)")
        if "barcode_source" not in cols:
            alters.append("ALTER TABLE scans ADD COLUMN barcode_source VARCHAR(20)")
        if "barcode_product_json" not in cols:
            alters.append("ALTER TABLE scans ADD COLUMN barcode_product_json TEXT")
        if "barcode_lookup_source" not in cols:
            alters.append("ALTER TABLE scans ADD COLUMN barcode_lookup_source VARCHAR(40)")
        if "barcode_lookup_found" not in cols:
            alters.append("ALTER TABLE scans ADD COLUMN barcode_lookup_found INTEGER DEFAULT 0")
        for sql in alters:
            conn.exec_driver_sql(sql)
        conn.commit()


def _public_url(path: str | None) -> str | None:
    if not path:
        return None
    name = Path(path).name
    return f"/uploads/{name}"


def _parse_barcode_product(scan: Scan) -> dict | None:
    raw = getattr(scan, "barcode_product_json", None)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _checksum_bool(scan: Scan) -> bool | None:
    raw = getattr(scan, "barcode_checksum_valid", None)
    if raw is None:
        return None
    return bool(raw)


def _scan_to_detail(scan: Scan) -> ScanDetail:
    report = None
    if scan.report:
        report = ReportOut(
            id=scan.report.id,
            scan_id=scan.report.scan_id,
            file_path=scan.report.file_path,
            created_at=scan.report.created_at,
            download_url=f"/api/reports/{scan.id}",
        )
    return ScanDetail(
        id=scan.id,
        product_name=scan.product_name,
        image_path=scan.image_path,
        image_url=_public_url(scan.image_path),
        annotated_image_url=_public_url(scan.annotated_image_path),
        status=scan.status,
        screening_score=scan.screening_score,
        passed_count=scan.passed_count or 0,
        warning_count=scan.warning_count or 0,
        failed_count=scan.failed_count or 0,
        not_detected_count=getattr(scan, "not_detected_count", 0) or 0,
        not_applicable_count=getattr(scan, "not_applicable_count", 0) or 0,
        raw_ocr_text=scan.raw_ocr_text,
        ocr_engine=getattr(scan, "ocr_engine", None),
        ocr_mean_confidence=getattr(scan, "ocr_mean_confidence", None),
        error_message=getattr(scan, "error_message", None),
        barcode_value=getattr(scan, "barcode_value", None),
        barcode_format=getattr(scan, "barcode_format", None),
        barcode_checksum_valid=_checksum_bool(scan),
        barcode_gtin=getattr(scan, "barcode_gtin", None),
        barcode_raw=getattr(scan, "barcode_raw", None),
        barcode_source=getattr(scan, "barcode_source", None),
        barcode_product=_parse_barcode_product(scan),
        barcode_lookup_source=getattr(scan, "barcode_lookup_source", None),
        barcode_lookup_found=bool(getattr(scan, "barcode_lookup_found", 0) or 0),
        created_at=scan.created_at,
        extracted_fields=scan.extracted_fields,
        violations=scan.violations,
        report=report,
    )


def _scan_summary(scan: Scan) -> ScanSummary:
    return ScanSummary(
        id=scan.id,
        product_name=scan.product_name,
        image_path=scan.image_path,
        status=scan.status,
        screening_score=scan.screening_score,
        passed_count=scan.passed_count or 0,
        warning_count=scan.warning_count or 0,
        failed_count=scan.failed_count or 0,
        not_detected_count=getattr(scan, "not_detected_count", 0) or 0,
        created_at=scan.created_at,
        violation_count=len(
            [v for v in scan.violations if v.status in ("FAIL", "NOT_DETECTED")]
        ),
        ocr_engine=getattr(scan, "ocr_engine", None),
        barcode_value=getattr(scan, "barcode_value", None),
        barcode_format=getattr(scan, "barcode_format", None),
    )


@app.get("/api/health")
def health():
    engine_name = "unknown"
    try:
        from services.ocr import detect_available_engine

        engine_name = detect_available_engine()
    except Exception as exc:
        engine_name = f"unavailable: {exc}"
    return {
        "status": "ok",
        "service": "PackScan",
        "version": "2.0.0",
        "ocr_engine": engine_name,
        "mock_ocr": False,
    }


@app.post("/api/scans", response_model=ScanDetail)
async def create_scan(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            status_code=400,
            detail="Unsupported image. Upload JPG, JPEG, PNG or WEBP only.",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 12 MB).")

    filename = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOAD_DIR / filename
    dest.write_bytes(data)

    scan = Scan(product_name=None, image_path=str(dest), status="uploaded")
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return _scan_to_detail(scan)


@app.get("/api/scans", response_model=list[ScanSummary])
def list_scans(db: Session = Depends(get_db)):
    scans = db.query(Scan).order_by(Scan.created_at.desc()).all()
    return [_scan_summary(s) for s in scans]


@app.get("/api/scans/{scan_id}", response_model=ScanDetail)
def get_scan(scan_id: int, db: Session = Depends(get_db)):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return _scan_to_detail(scan)


@app.get("/api/products/lookup", response_model=ProductLookupOut)
def products_lookup(code: str = Query(..., min_length=8, description="EAN/UPC/GTIN barcode")):
    """Real Open*Facts product lookup by barcode / GTIN (no invented values)."""
    result = lookup_product_by_barcode(code)
    return ProductLookupOut(
        found=bool(result.get("found")),
        code=str(result.get("code") or code),
        source=result.get("source"),
        name=result.get("name"),
        brand=result.get("brand"),
        quantity=result.get("quantity"),
        countries=result.get("countries"),
        categories=result.get("categories"),
        packaging=result.get("packaging"),
        image_url=result.get("image_url"),
        images=result.get("images") or {},
        ingredients=result.get("ingredients"),
        allergens=result.get("allergens"),
        traces=result.get("traces"),
        labels=result.get("labels"),
        nova_group=result.get("nova_group"),
        nutriscore_grade=result.get("nutriscore_grade"),
        ecoscore_grade=result.get("ecoscore_grade"),
        details=result.get("details") or [],
        nutrition=result.get("nutrition") or [],
        fields=result.get("fields") or {},
        message=str(result.get("message") or ""),
        missing_legal_metrology_note=result.get("missing_legal_metrology_note"),
    )


@app.put("/api/scans/{scan_id}/barcode", response_model=ScanDetail)
def update_scan_barcode(scan_id: int, body: BarcodeUpdate, db: Session = Depends(get_db)):
    """
    Persist a client-detected barcode (from ZXing camera/image) onto an existing scan,
    then optionally look up catalog product info from free Open*Facts APIs.
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    allowed = {
        "EAN_13",
        "GTIN_13",
        "EAN_8",
        "UPC_A",
        "UPC_E",
        "CODE_128",
        "CODE_39",
        "ITF",
        "CODABAR",
        "RSS_14",
    }
    fmt = body.barcode_format.strip().upper()
    if fmt not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported barcode format. Allowed: {', '.join(sorted(allowed))}",
        )
    if body.barcode_source not in {"camera", "image"}:
        raise HTTPException(status_code=400, detail="barcode_source must be camera or image")

    scan.barcode_value = body.barcode_value.strip()
    scan.barcode_format = fmt
    if body.barcode_checksum_valid is None:
        scan.barcode_checksum_valid = None
    else:
        scan.barcode_checksum_valid = 1 if body.barcode_checksum_valid else 0
    scan.barcode_gtin = body.barcode_gtin or None
    scan.barcode_raw = (body.barcode_raw or body.barcode_value).strip()
    scan.barcode_source = body.barcode_source

    if body.lookup:
        lookup = lookup_product_by_barcode(scan.barcode_gtin or scan.barcode_value)
        scan.barcode_product_json = json.dumps(lookup, ensure_ascii=False)
        scan.barcode_lookup_found = 1 if lookup.get("found") else 0
        scan.barcode_lookup_source = lookup.get("source")
        # Prefer catalog name before OCR if still empty
        if lookup.get("found") and lookup.get("name") and not scan.product_name:
            scan.product_name = lookup["name"]
    else:
        scan.barcode_product_json = None
        scan.barcode_lookup_found = 0
        scan.barcode_lookup_source = None

    db.commit()
    db.refresh(scan)
    return _scan_to_detail(scan)


@app.post("/api/analyze/{scan_id}", response_model=AnalyzeResponse)
def analyze_scan(scan_id: int, db: Session = Depends(get_db)):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if not Path(scan.image_path).exists():
        raise HTTPException(status_code=400, detail="Scan image missing on disk")

    # Clear previous analysis
    db.query(ExtractedField).filter(ExtractedField.scan_id == scan.id).delete()
    db.query(Violation).filter(Violation.scan_id == scan.id).delete()
    if scan.report:
        old = Path(scan.report.file_path)
        db.delete(scan.report)
        db.flush()
        if old.exists():
            old.unlink(missing_ok=True)

    try:
        ocr = run_ocr(scan.image_path)
    except OCRError as exc:
        scan.status = "OCR Failed"
        scan.error_message = str(exc)
        scan.raw_ocr_text = None
        scan.screening_score = None
        db.commit()
        db.refresh(scan)
        raise HTTPException(
            status_code=422,
            detail=f"OCR failed: {exc}. Please upload a clearer product label image.",
        ) from exc
    except Exception as exc:
        scan.status = "OCR Failed"
        scan.error_message = str(exc)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Server OCR error: {exc}") from exc

    if not ocr.success or not (ocr.raw_text or "").strip():
        scan.status = "No Text Detected"
        scan.error_message = (
            "No readable declarations detected. Please upload a clearer image."
        )
        scan.raw_ocr_text = ocr.raw_text or ""
        scan.ocr_engine = ocr.engine_name
        scan.ocr_mean_confidence = ocr.mean_confidence
        scan.ocr_json = json.dumps(result_to_dict(ocr))
        scan.annotated_image_path = ocr.annotated_image_path
        scan.processed_image_path = ocr.processed_image_path
        scan.screening_score = None
        scan.passed_count = 0
        scan.warning_count = 0
        scan.failed_count = 0
        scan.not_detected_count = 0
        db.commit()
        db.refresh(scan)
        raise HTTPException(
            status_code=422,
            detail="No readable declarations detected. Please upload a clearer image.",
        )

    declarations = extract_declarations(ocr)

    # Enrich empty OCR fields from real barcode catalog lookup (Open*Facts)
    lookup = _parse_barcode_product(scan)
    if (not lookup or not lookup.get("found")) and (scan.barcode_value or scan.barcode_gtin):
        lookup = lookup_product_by_barcode(scan.barcode_gtin or scan.barcode_value or "")
        scan.barcode_product_json = json.dumps(lookup, ensure_ascii=False)
        scan.barcode_lookup_found = 1 if lookup.get("found") else 0
        scan.barcode_lookup_source = lookup.get("source")

    catalog = (lookup or {}).get("fields") or {}
    for decl in declarations:
        if decl.field_key in catalog and not decl.found:
            decl.value = catalog[decl.field_key]
            decl.found = True
            decl.confidence = max(decl.confidence, 0.72)
            decl.status = "DETECTED"

    rule_results = evaluate_compliance(declarations)
    score_info = compute_screening_score(rule_results)
    field_rows = field_status_from_rules(declarations, rule_results)

    product = next(
        (d.value for d in declarations if d.field_key == "product_name" and d.value),
        None,
    )
    if lookup and lookup.get("found") and lookup.get("name"):
        if not product or len(product) < 5:
            product = lookup["name"]

    for row in field_rows:
        db.add(
            ExtractedField(
                scan_id=scan.id,
                field_key=row["field_key"],
                field_label=row["field_label"],
                value=row["value"],
                confidence=row["confidence"],
                status=row["status"],
            )
        )

    for rr in rule_results:
        if rr.status == "PASS":
            continue
        db.add(
            Violation(
                scan_id=scan.id,
                rule_id=rr.rule_id,
                severity=rr.severity,
                status=rr.status,
                message=rr.message,
                recommendation=rr.recommendation,
            )
        )

    hint = coverage_hint(ocr.raw_text or "", declarations)
    if lookup and lookup.get("found"):
        note = lookup.get("missing_legal_metrology_note")
        if note:
            hint = f"{hint + ' ' if hint else ''}{note}".strip()
    elif scan.barcode_value and lookup and not lookup.get("found"):
        hint = (
            f"{hint + ' ' if hint else ''}"
            f"Barcode {scan.barcode_value} saved, but no catalog product match. "
            "Label OCR still required for Legal Metrology declarations."
        ).strip()

    scan.product_name = product
    scan.raw_ocr_text = ocr.raw_text
    scan.ocr_engine = ocr.engine_name
    scan.ocr_mean_confidence = ocr.mean_confidence
    scan.ocr_json = json.dumps(result_to_dict(ocr))
    scan.annotated_image_path = ocr.annotated_image_path
    scan.processed_image_path = ocr.processed_image_path
    scan.error_message = hint or None
    scan.screening_score = score_info["screening_score"]
    scan.passed_count = score_info["passed_count"]
    scan.warning_count = score_info["warning_count"]
    scan.failed_count = score_info["failed_count"]
    scan.not_detected_count = score_info["not_detected_count"]
    scan.not_applicable_count = score_info["not_applicable_count"]
    scan.status = score_info["status"]

    db.commit()
    db.refresh(scan)

    msg = f"Analysis complete using real OCR engine: {ocr.engine_name}"
    if lookup and lookup.get("found"):
        msg += f" + barcode catalog ({lookup.get('source')})"

    return AnalyzeResponse(
        scan=_scan_to_detail(scan),
        message=msg,
    )


@app.get("/api/dashboard", response_model=DashboardStats)
def dashboard(db: Session = Depends(get_db)):
    scans = (
        db.query(Scan)
        .filter(Scan.status.notin_(["uploaded", "pending", "OCR Failed", "No Text Detected"]))
        .all()
    )
    total = len(scans)
    compliant = sum(1 for s in scans if s.status == "Compliant")
    partial = sum(1 for s in scans if s.status == "Partially Compliant")
    non = sum(1 for s in scans if s.status == "Non-Compliant")

    distribution = [
        {"name": "Compliant", "value": compliant},
        {"name": "Partially Compliant", "value": partial},
        {"name": "Non-Compliant", "value": non},
    ]

    today = datetime.utcnow().date()
    buckets: dict[str, int] = defaultdict(int)
    for i in range(6, -1, -1):
        buckets[(today - timedelta(days=i)).isoformat()] = 0
    for s in scans:
        d = s.created_at.date().isoformat()
        if d in buckets:
            buckets[d] += 1
    recent_trend = [{"date": k, "scans": v} for k, v in buckets.items()]

    counter: Counter[str] = Counter()
    for s in scans:
        for v in s.violations:
            if v.status in ("FAIL", "WARNING", "NOT_DETECTED"):
                counter[v.message] += 1
    common = [{"message": msg, "count": c} for msg, c in counter.most_common(6)]

    return DashboardStats(
        total_scans=total,
        compliant=compliant,
        partially_compliant=partial,
        non_compliant=non,
        compliance_distribution=distribution,
        recent_trend=recent_trend,
        common_violations=common,
    )


@app.post("/api/reports/{scan_id}", response_model=ReportOut)
def create_report(scan_id: int, db: Session = Depends(get_db)):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if scan.status in ("uploaded", "pending", "OCR Failed", "No Text Detected"):
        raise HTTPException(
            status_code=400,
            detail="Analyze a readable scan successfully before generating a report.",
        )

    extracted = [
        {
            "field_label": f.field_label,
            "value": f.value,
            "confidence": f.confidence,
            "status": f.status,
        }
        for f in scan.extracted_fields
    ]
    violations = [
        {
            "rule_id": v.rule_id,
            "severity": v.severity,
            "status": v.status,
            "message": v.message,
            "recommendation": v.recommendation,
        }
        for v in scan.violations
    ]

    evidence = scan.annotated_image_path or scan.image_path
    pdf_path = generate_pdf_report(
        scan_id=scan.id,
        product_name=scan.product_name,
        created_at=scan.created_at,
        image_path=scan.image_path,
        screening_score=scan.screening_score,
        status=scan.status,
        passed_count=scan.passed_count,
        warning_count=scan.warning_count,
        failed_count=scan.failed_count,
        extracted_fields=extracted,
        violations=violations,
        evidence_image_path=evidence,
        ocr_engine=scan.ocr_engine,
        not_detected_count=scan.not_detected_count,
    )

    if scan.report:
        scan.report.file_path = str(pdf_path)
        scan.report.created_at = datetime.utcnow()
        db.commit()
        db.refresh(scan.report)
        report = scan.report
    else:
        report = Report(scan_id=scan.id, file_path=str(pdf_path))
        db.add(report)
        db.commit()
        db.refresh(report)

    return ReportOut(
        id=report.id,
        scan_id=report.scan_id,
        file_path=report.file_path,
        created_at=report.created_at,
        download_url=f"/api/reports/{scan.id}",
    )


@app.get("/api/reports/{scan_id}")
def download_report(scan_id: int, db: Session = Depends(get_db)):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if not scan.report:
        create_report(scan_id, db)
        db.refresh(scan)
    path = Path(scan.report.file_path)
    if not path.exists():
        create_report(scan_id, db)
        db.refresh(scan)
        path = Path(scan.report.file_path)
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"PackScan_Report_{scan_id}.pdf",
    )
