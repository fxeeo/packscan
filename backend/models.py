from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    annotated_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    processed_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    screening_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    passed_count: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    not_detected_count: Mapped[int] = mapped_column(Integer, default=0)
    not_applicable_count: Mapped[int] = mapped_column(Integer, default=0)
    raw_ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_engine: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ocr_mean_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ocr_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    barcode_value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    barcode_format: Mapped[str | None] = mapped_column(String(32), nullable=True)
    barcode_checksum_valid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    barcode_gtin: Mapped[str | None] = mapped_column(String(14), nullable=True)
    barcode_raw: Mapped[str | None] = mapped_column(String(128), nullable=True)
    barcode_source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    barcode_product_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    barcode_lookup_source: Mapped[str | None] = mapped_column(String(40), nullable=True)
    barcode_lookup_found: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    extracted_fields = relationship(
        "ExtractedField", back_populates="scan", cascade="all, delete-orphan"
    )
    violations = relationship(
        "Violation", back_populates="scan", cascade="all, delete-orphan"
    )
    report = relationship(
        "Report", back_populates="scan", uselist=False, cascade="all, delete-orphan"
    )


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("scans.id"), nullable=False)
    field_key: Mapped[str] = mapped_column(String(100), nullable=False)
    field_label: Mapped[str] = mapped_column(String(150), nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(30), default="NOT_DETECTED")

    scan = relationship("Scan", back_populates="extracted_fields")


class Violation(Base):
    __tablename__ = "violations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("scans.id"), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)

    scan = relationship("Scan", back_populates="violations")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("scans.id"), unique=True, nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    scan = relationship("Scan", back_populates="report")
