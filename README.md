# Financial Modelling Platform

A production-ready application for uploading financial documents, automatically extracting structured financial data, and building dynamic financial models through natural-language commands.

---

## Architecture

```
Financial_Modelling/
├── backend/                   # FastAPI Python backend
│   ├── app/
│   │   ├── main.py            # App entry point, CORS, lifespan
│   │   ├── config.py          # Settings via pydantic-settings
│   │   ├── database.py        # SQLAlchemy async engine + Base
│   │   ├── models/            # ORM models (Document, FinancialRecord, ModelState, etc.)
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── api/               # FastAPI routers
│   │   │   ├── documents.py   # Upload, list, delete, extraction status
│   │   │   ├── financial_data.py  # Records, periods, summary pivot
│   │   │   ├── modelling.py   # Models, commands, scenarios, sensitivity
│   │   │   └── export.py      # Excel + CSV downloads
│   │   ├── services/
│   │   │   ├── document_parser.py   # Dispatcher to format-specific parsers
│   │   │   ├── pdf_parser.py        # pdfplumber + PyMuPDF
│   │   │   ├── excel_parser.py      # openpyxl + pandas
│   │   │   ├── csv_parser.py        # pandas + chardet
│   │   │   ├── docx_parser.py       # python-docx
│   │   │   ├── image_parser.py      # Tesseract OCR
│   │   │   ├── data_normalizer.py   # Map tables → FinancialRecord
│   │   │   ├── nlp_command_parser.py # Regex-based NL command parser
│   │   │   └── modelling_engine.py  # FinancialModel, CAGR, scenarios, CF
│   │   └── utils/
│   │       ├── financial_utils.py   # classify_line_item, parse_numeric_value, etc.
│   │       └── file_utils.py        # MIME detection, unique filenames
│   └── tests/
│       ├── test_parsers.py
│       ├── test_modelling.py
│       └── test_api.py
│
├── frontend/                  # React + TypeScript + Vite
│   └── src/
│       ├── pages/
│       │   ├── DataRoom.tsx   # File upload + document library
│       │   ├── ExtractedData.tsx  # Pivoted financial data viewer
│       │   └── ModelView.tsx  # Console + charts + tables + scenarios
│       ├── components/
│       │   ├── FileUpload.tsx        # Dropzone + progress tracking
│       │   ├── InstructionConsole.tsx # NL command terminal
│       │   ├── FinancialTable.tsx    # Collapsible data table
│       │   ├── Charts.tsx            # Recharts bar/line/area charts
│       │   ├── ScenarioSelector.tsx  # Scenario picker + creator
│       │   ├── ExportButtons.tsx     # Excel/CSV download menu
│       │   ├── DocumentList.tsx      # Document library with status
│       │   └── ModelSetup.tsx        # Model creation form
│       ├── services/api.ts    # Axios API client
│       ├── store/appStore.ts  # Zustand global state
│       └── types/index.ts     # TypeScript types
│
├── docker-compose.yml
└── README.md
```

---

## Quick Start

### Option A — Docker (recommended)

```bash
# 1. Clone / enter the project
cd Financial_Modelling

# 2. Copy environment config
cp backend/.env.example backend/.env

# 3. Build and start both services
docker compose up --build

# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API docs:    http://localhost:8000/docs
```

### Option B — Local development

#### Backend

```bash
cd backend

# Create virtualenv
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# (Optional) Install Tesseract OCR for image parsing
# macOS:   brew install tesseract
# Ubuntu:  sudo apt-get install tesseract-ocr
# Windows: https://github.com/UB-Mannheim/tesseract/wiki

# Copy environment config
cp .env.example .env

# Run the server
uvicorn app.main:app --reload --port 8000
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run dev server (proxies /api to localhost:8000)
npm run dev
# → http://localhost:3000
```

---

## API Reference

Base URL: `http://localhost:8000/api/v1`

Interactive docs: `http://localhost:8000/docs`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/documents/upload` | Upload a document (multipart/form-data) |
| `GET` | `/documents` | List all documents |
| `GET` | `/documents/{id}` | Get document detail + tables |
| `GET` | `/documents/{id}/extraction-status` | Poll extraction progress |
| `DELETE` | `/documents/{id}` | Delete document |
| `GET` | `/financial-data/summary` | Pivoted income statement / BS / CF / KPIs |
| `GET` | `/financial-data/records` | Raw financial records |
| `GET` | `/financial-data/periods` | List all periods |
| `GET` | `/models` | List financial models |
| `POST` | `/models` | Create a new model |
| `GET` | `/models/{id}/output` | Get model output (tables + charts) |
| `POST` | `/models/command` | Execute a NL modelling command |
| `GET` | `/models/{id}/scenarios` | List scenarios |
| `POST` | `/models/{id}/scenarios` | Create a scenario |
| `POST` | `/models/sensitivity` | Run sensitivity analysis |
| `GET` | `/export/excel/{id}` | Download Excel workbook |
| `GET` | `/export/csv/{id}` | Download CSV (section param) |

---

## Modelling Commands

The instruction console accepts natural-language commands. Examples:

```
# Revenue
Model revenue using a 3-year CAGR from historicals
Apply a 10% growth rate to revenue over 3 years

# Costs
Apply a 15% staff cost increase from FY25
Apply a 5% cost growth

# Cashflow
Build a monthly cashflow forecast for 36 months
Build a 12-month cashflow forecast

# Scenarios
Add a scenario where churn increases by 20%
Add a Bear Case scenario

# Sensitivity
Run sensitivity analysis on revenue
Run sensitivity analysis on churn rate

# Assumptions
Set tax rate to 25%
Set discount rate to 12%
```

---

## Running Tests

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

---

## Database

- Default: **SQLite** (stored at `./financial_model.db`)
- To use **PostgreSQL**, update `.env`:
  ```
  DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/finmodel
  ```
  And install: `pip install asyncpg`

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2 (async), Pydantic v2 |
| Database | SQLite (default) / PostgreSQL |
| Document parsing | pdfplumber, PyMuPDF, openpyxl, pandas, python-docx, pytesseract |
| Modelling | Custom pandas-backed engine with NLP command parser |
| Export | xlsxwriter (Excel), csv (stdlib) |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| State | Zustand + TanStack Query |
| Charts | Recharts |
| Containerisation | Docker + Docker Compose |

---

## Next Steps (Roadmap)

- [ ] LLM-powered command parsing (OpenAI / Anthropic fallback)
- [ ] DCF / valuation module
- [ ] Cap table modelling
- [ ] Collaborative model sharing
- [ ] Version history / audit trail
- [ ] PostgreSQL production setup
- [ ] Auth (JWT / OAuth2)
- [ ] AI-generated commentary on outputs
