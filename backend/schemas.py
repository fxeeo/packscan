from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExtractedFieldOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    field_key: str
    field_label: str
    value: str | None
    confidence: float
    status: str


class ViolationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rule_id: str
    severity: str
    status: str
    message: str
    recommendation: str


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scan_id: int
    file_path: str
    created_at: datetime
    download_url: str | None = None


class ScanSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_name: str | None
    image_path: str
    status: str
    screening_score: float | None
    passed_count: int
    warning_count: int
    failed_count: int
    not_detected_count: int = 0
    created_at: datetime
    violation_count: int = 0
    ocr_engine: str | None = None
    barcode_value: str | None = None
    barcode_format: str | None = None


class ScanDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_name: str | None
    image_path: str
    image_url: str | None = None
    annotated_image_url: str | None = None
    status: str
    screening_score: float | None
    passed_count: int
    warning_count: int
    failed_count: int
    not_detected_count: int = 0
    not_applicable_count: int = 0
    raw_ocr_text: str | None
    ocr_engine: str | None = None
    ocr_mean_confidence: float | None = None
    error_message: str | None = None
    barcode_value: str | None = None
    barcode_format: str | None = None
    barcode_checksum_valid: bool | None = None
    barcode_gtin: str | None = None
    barcode_raw: str | None = None
    barcode_source: str | None = None
    barcode_product: dict[str, Any] | None = None
    barcode_lookup_source: str | None = None
    barcode_lookup_found: bool = False
    created_at: datetime
    extracted_fields: list[ExtractedFieldOut] = Field(default_factory=list)
    violations: list[ViolationOut] = Field(default_factory=list)
    report: ReportOut | None = None


class BarcodeUpdate(BaseModel):
    barcode_value: str = Field(min_length=1, max_length=64)
    barcode_format: str = Field(min_length=1, max_length=32)
    barcode_checksum_valid: bool | None = None
    barcode_gtin: str | None = Field(default=None, max_length=14)
    barcode_raw: str = Field(default="", max_length=128)
    barcode_source: str = Field(default="image", max_length=20)
    lookup: bool = True


class ProductLookupOut(BaseModel):
    found: bool
    code: str
    source: str | None = None
    name: str | None = None
    brand: str | None = None
    quantity: str | None = None
    countries: str | None = None
    categories: str | None = None
    packaging: str | None = None
    image_url: str | None = None
    images: dict[str, str | None] = Field(default_factory=dict)
    ingredients: str | None = None
    allergens: str | None = None
    traces: str | None = None
    labels: str | None = None
    nova_group: str | None = None
    nutriscore_grade: str | None = None
    ecoscore_grade: str | None = None
    details: list[dict[str, str]] = Field(default_factory=list)
    nutrition: list[dict[str, str]] = Field(default_factory=list)
    fields: dict[str, str] = Field(default_factory=dict)
    message: str
    missing_legal_metrology_note: str | None = None


class DashboardStats(BaseModel):
    total_scans: int
    compliant: int
    partially_compliant: int
    non_compliant: int
    compliance_distribution: list[dict[str, Any]]
    recent_trend: list[dict[str, Any]]
    common_violations: list[dict[str, Any]]


class AnalyzeResponse(BaseModel):
    scan: ScanDetail
    message: str
