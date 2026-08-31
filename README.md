# PackScan — SIH26034 Real OCR Prototype

**No mock data. No hardcoded results. Real image → Real OCR → Real compliance screening.**

## Architecture

```
Next.js Frontend (port 3000)
        ↓ REST API
FastAPI Backend (port 8000)
        ↓
OpenCV Preprocessing → PaddleOCR / Tesseract → Declaration Extraction
        ↓
JSON Rule Engine → SQLite → ReportLab PDF
```

## Setup

### 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

**Tesseract (fallback OCR):** Install from https://github.com/UB-Mannheim/tesseract/wiki and ensure `tesseract` is in PATH.

**PaddleOCR:** Installed via pip. First run downloads models (~100MB).

Delete old database if upgrading:
```bash
del packscan.db
```

Start backend:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**

## Test OCR Independently

```bash
cd backend
python test_ocr.py path/to/product_image.jpg
```

## Test With New Product Image

1. Open http://localhost:3000/scan
2. Upload any packaged product photo (JPG/PNG)
3. Click **Analyze**
4. View real results at `/result/{id}`
5. Check **History** — scan saved in SQLite
6. Click **Generate PDF Report**

## Key Files

| Purpose | File |
|---------|------|
| Real OCR | `backend/services/ocr.py` |
| OpenCV preprocessing | `backend/services/image_processing.py` |
| Declaration extraction | `backend/services/extraction.py` |
| JSON rules | `backend/rules/legal_metrology_rules.json` |
| Rule engine | `backend/services/compliance.py` |
| Full pipeline | `backend/services/pipeline.py` |
| Readability screening | `backend/services/readability.py` |

## What Was Removed

- Mock OCR sample texts
- Hardcoded seed/demo scan data
- Predetermined compliance scores
- Fake loading → fake results flow

## Known Limitations

- OCR accuracy depends on image quality, lighting, and label language
- Pixel-based readability screening does NOT determine legal font-size compliance
- Country of origin rule marked as optional — manual verification for imports
- PaddleOCR first run requires internet to download models
- Blurry or low-resolution images may return "No readable text detected"
