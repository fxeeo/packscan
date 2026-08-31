# FILE: backend/app/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship
import datetime

Base = declarative_base()

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    manufacturer = Column(String)
    category = Column(String)
    inspections = relationship("Inspection", back_populates="product")

class Inspection(Base):
    __tablename__ = "inspections"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    scan_date = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String) # COMPLIANT, NON_COMPLIANT, NEEDS_REVIEW
    score = Column(Float)
    product = relationship("Product", back_populates="inspections")
    violations = relationship("Violation", back_populates="inspection")

class Violation(Base):
    __tablename__ = "violations"
    id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"))
    rule_reference = Column(String)
    severity = Column(String) # CRITICAL, MAJOR, MINOR
    evidence = Column(String)
    confidence = Column(Float)
    inspection = relationship("Inspection", back_populates="violations")

# FILE: backend/app/services/compliance.py
import random

class MockOCRService:
    @staticmethod
    def extract_text(image_bytes: bytes) -> dict:
        # Simulates OCR extraction with bounding boxes
        return {
            "raw_text": "Premium Rice 5 kg MRP 150 Manufacturer: XYZ Corp",
            "entities": {
                "product_name": "Premium Rice",
                "net_quantity": "5 kg",
                "mrp": "150",
                "manufacturer": "XYZ Corp",
                "consumer_care": None # Intentionally missing for demo
            },
            "confidence": 0.92
        }

class ComplianceEngine:
    @staticmethod
    def analyze_product(ocr_data: dict) -> dict:
        violations = []
        score = 100
        
        entities = ocr_data.get("entities", {})
        
        # Rule 1: Net Quantity (Rule 2(m))
        if not entities.get("net_quantity"):
            violations.append({
                "rule": "Net Quantity Missing (Rule 6(1)(c))",
                "severity": "CRITICAL",
                "evidence": "No valid metric quantity detected on principal display panel."
            })
            score -= 30
            
        # Rule 2: Consumer Care (Rule 6(1)(g))
        if not entities.get("consumer_care"):
            violations.append({
                "rule": "Consumer Care Details Missing",
                "severity": "MAJOR",
                "evidence": "Phone number or email not detected."
            })
            score -= 20

        return {
            "status": "COMPLIANT" if score == 100 else "NON_COMPLIANT",
            "score": max(0, score),
            "violations": violations
        }