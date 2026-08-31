# PackScan — SIH26034
# Smart Packaged Commodity Compliance (Legal Metrology screening prototype)

ZIP extract → `setup.bat` → `start.bat` → browser me open.

---

## Quick start (Windows — recommended)

### 0) Pehle PC pe install karo (one-time, system level)

| Requirement | Version | Notes |
|-------------|---------|--------|
| **Python** | **3.10 – 3.12** (x64) | 3.13+ pe PaddleOCR unreliable ho sakta hai. Installer me **Add Python to PATH** tick karo. |
| **Node.js** | **20 LTS+** | https://nodejs.org |
| **Git** | optional | ZIP se nahi chahiye |
| **Microsoft Visual C++ Redistributable** | latest x64 | PaddlePaddle ke liye recommended |
| **RAM** | 8 GB+ | OCR models ke liye |
| **Internet** | pehli setup + barcode lookup | `pip` / `npm` download + Open*Facts |

Optional (sirf agar `PACKSCAN_OCR_ENGINE=tesseract` use karoge):
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) Windows installer + PATH

### 1) ZIP extract

Folder structure aisi honi chahiye:

```text
packscan/
  setup.bat
  start.bat
  setup.ps1
  start.ps1
  .env.example
  README.md
  backend/
  frontend/
```

### 2) Setup (dependencies install)

Double-click **`setup.bat`**
ya PowerShell:

```powershell
cd path\to\packscan
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

Ye kya karega:
1. `.env.example` → `.env` copy
2. `backend/.venv` banayega
3. `pip install -r backend/requirements.txt` (PaddleOCR pehli baar **5–20 min** + large download)
4. SQLite DB / `uploads` / `reports` init
5. `frontend` me `npm install`

### 3) Run

Double-click **`start.bat`**
ya:

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

Do windows khulenge (API + UI).

| Service | URL |
|---------|-----|
| **UI** | http://127.0.0.1:5173/ |
| **API docs** | http://127.0.0.1:8000/docs |

Band karne ke liye dono terminal windows close kar do.

---

## Portable ZIP khud banana (share karne se pehle)

Is machine pe:

```powershell
cd path\to\packscan
powershell -ExecutionPolicy Bypass -File .\create-portable-zip.ps1
```

ZIP parent folder me banegi: `PackScan-portable-YYYYMMDD-HHMM.zip`
**Exclude** hota hai: `.venv`, `node_modules`, `*.db`, uploads/reports content, `.env`

---

## Environment variables

Root file: **`.env`** (`.env.example` se copy).

| Variable | Default | Meaning |
|----------|---------|---------|
| `PACKSCAN_API_HOST` | `127.0.0.1` | API bind host |
| `PACKSCAN_API_PORT` | `8000` | API port (Vite proxy isi pe point karta hai) |
| `PACKSCAN_OCR_ENGINE` | `paddle` | `paddle` / `tesseract` / `auto` |
| `PACKSCAN_DB_NAME` | `packscan_v2.db` | SQLite file (`backend/` ke andar) |
| `PACKSCAN_CORS_ORIGINS` | `*` | CORS |
| `VITE_API_PROXY_TARGET` | `http://127.0.0.1:8000` | Frontend → backend proxy |
| `VITE_DEV_PORT` | `5173` | UI port |

Frontend API calls relative `/api`, `/uploads`, `/reports` use karti hain — **hardcoded product data nahi**. Proxy Vite se backend tak jati hai.

---

## Project layout (important parts)

```text
packscan/
  .env.example
  setup.bat / setup.ps1
  start.bat / start.ps1
  create-portable-zip.ps1
  backend/
    main.py                 # FastAPI
    config.py               # env settings
    database.py             # SQLite + uploads/reports paths
    requirements.txt
    scripts/init_db.py
    rules/legal_metrology_rules.json
    services/               # OCR, extraction, compliance, barcode lookup, PDF
    uploads/                # runtime (empty in ZIP)
    reports/                # runtime (empty in ZIP)
    test_images/            # optional sample images
  frontend/
    package.json
    vite.config.ts          # proxy + allowedHosts
    src/                    # React UI (Scan, Barcode, History, Dashboard)
```

---

## Database / storage

| Item | Behavior |
|------|----------|
| **DB** | SQLite `backend/packscan_v2.db` — pehli run / `init_db.py` pe auto-create |
| **Seed** | **Koi fake compliance seed nahi** (real OCR flow) |
| **Uploads** | `backend/uploads/` — scan images |
| **Reports** | `backend/reports/` — generated PDFs |
| **Rules** | `backend/rules/legal_metrology_rules.json` |

Dusre PC pe pehli run clean DB se start hoti hai — purani history ZIP me nahi aati (by design).

---

## Dependencies summary

### Frontend (`frontend/package.json`)
- React 19 + Vite 8 + TypeScript + Tailwind 4
- `react-router-dom`, `lucide-react`, `recharts`
- Barcode: `@zxing/browser`, `@zxing/library`
- Install: `npm install` (Node ≥ 20)

### Backend (`backend/requirements.txt`)
- FastAPI, Uvicorn, SQLAlchemy, Pydantic, ReportLab, Pillow, OpenCV
- **OCR:** `paddlepaddle` + `paddleocr` (primary)
- Optional: `pytesseract` (+ OS Tesseract binary)
- `python-dotenv`, `pydantic-settings`

### System-level
- Python 3.10–3.12 x64
- Node.js 20+
- VC++ Redistributable (Windows)
- Camera permission (browser) for live barcode
- Network: Open Food/Beauty/Products Facts barcode lookup ke liye

---

## Manual setup (scripts ke bina)

```powershell
# Backend
cd packscan
copy .env.example .env
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\init_db.py
$env:PACKSCAN_OCR_ENGINE="paddle"
uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# Frontend (naya terminal)
cd packscan\frontend
npm install
copy .env.example .env
npm run dev -- --host 0.0.0.0 --port 5173
```

---

## Verify

1. http://127.0.0.1:5173/ → Home dikhe
2. **Barcode** → camera/image/manual digits → Open*Facts lookup (internet)
3. **Scan Product** → label photo → **Analyze** → OCR + compliance score
4. **Generate PDF** → download
5. **Dashboard / History** → local SQLite records

OCR smoke test:

```powershell
cd packscan\backend
.\.venv\Scripts\python.exe -m services.ocr test_images\01_complete_biscuit.png
```

---

## Common issues

| Problem | Fix |
|---------|-----|
| `Python not found` | PATH me Python 3.10–3.12 add karo / reinstall |
| `paddle` / DLL errors | VC++ Redistributable; Python 3.13 mat use karo |
| `npm` fail | Node 20+ LTS; antivirus temporarily allow |
| UI open, API fail | Port **8000** free hai? `VITE_API_PROXY_TARGET` backend se match kare |
| Port busy | `.env` me `PACKSCAN_API_PORT` / `VITE_DEV_PORT` badlo (dono sync rakho) |
| Barcode “not in Open*Facts” | Scanner OK — kai Indian SKUs catalog me nahi hote; label OCR continue karo |
| Phone se LAN link nahi | Firewall / Vite `allowedHosts` — ya Cloudflare tunnel; pehle PC pe `start` chalu rakho |
| Blank history | Normal — ZIP me purana DB share nahi hota |

---

## Security / honesty notes

- Local prototype — koi login/JWT nahi
- Paid commercial barcode DB nahi (Open*Facts free APIs)
- Compliance output **screening assistance** hai; final enforcement officer verify kare
- MRP / mfg date / consumer care aksar catalog me nahi → package label OCR zaroori

---

## License / SIH

SIH26034 Packaged Commodity Compliance screening prototype — local demo / evaluation use.
