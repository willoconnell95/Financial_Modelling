# Financial Modelling Platform

An AI-powered platform for extracting financial data from documents and building dynamic financial models via natural-language instructions.

## Features

- **Document Ingestion** – Upload PDF, Excel, CSV, DOCX, and image files
- **Automatic Extraction** – Structured financial data extracted and normalised
- **Natural-Language Modelling** – Type instructions like "Model revenue using 15% CAGR"
- **Dynamic Tables & Charts** – Live-updating financial model with P&L, cash flow, and KPIs
- **Scenario Analysis** – Create and compare Base/Upside/Downside scenarios
- **Sensitivity Analysis** – Tornado charts for assumption sensitivity
- **Export** – Download to Excel (formatted workbook) or CSV

---

## Architecture

```
Financial_Modelling/
├── backend/              # Python FastAPI backend
│   ├── app/
│   │   ├── main.py       # FastAPI entry point
│   │   ├── config.py     # Settings (env vars)
│   │   ├── database.py   # SQLAlchemy setup
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── api/          # Route handlers
│   │   ├── services/     # Business logic
│   │   └── utils/        # Normaliser, validators
│   └── tests/            # Pytest test suite
├── frontend/             # React + Vite + TypeScript
│   └── src/
│       ├── components/   # UI components
│       ├── pages/        # Dashboard page
│       ├── services/     # API client
│       └── types/        # TypeScript types
├── docker-compose.yml
└── .env.example
```

**Stack:**
- Backend: Python 3.11, FastAPI, SQLAlchemy, SQLite
- Parsing: pdfplumber, PyMuPDF, pandas, openpyxl, python-docx, Tesseract OCR
- Frontend: React 18, Vite, TypeScript, Tailwind CSS, Recharts
- Export: XlsxWriter

---

## Quick Start (Docker — Recommended)

### 1. Prerequisites
- Docker & Docker Compose installed

### 2. Configure
```bash
cp .env.example .env
# Optionally set OPENAI_API_KEY for enhanced NLP
```

### 3. Build & Run
```bash
docker-compose up --build
```

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## Local Development (without Docker)

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate          # Linux/macOS
# venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Install Tesseract (for OCR)
# macOS:  brew install tesseract
# Ubuntu: apt-get install tesseract-ocr
# Windows: https://github.com/UB-Mannheim/tesseract/wiki

# Create .env
cp ../.env.example .env

# Run database migrations
python -c "from app.database import init_db; init_db()"

# Start backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend

npm install
npm run dev
```

Frontend at http://localhost:5173 — proxied to backend on port 8000.

---

## Running Tests

```bash
cd backend
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## Usage Guide

### 1. Upload Documents
Drag & drop financial documents (PDF, Excel, CSV, DOCX, images) into the upload area.
The platform automatically parses and extracts structured financial data.

### 2. Initialise Model
Click **Initialise Model** after uploading documents. Choose period type (annual/quarterly/monthly)
and number of forecast periods.

### 3. Issue Instructions
Type natural-language commands in the **Instruction Console**:

| Command | Effect |
|---------|--------|
| `Model revenue using a 15% CAGR` | Apply 15% CAGR to revenue forecasts |
| `Apply a 10% staff cost increase from FY25` | Increase staff costs 10% from FY25 |
| `Set gross margin to 65%` | Set COGS = 35% of revenue |
| `Build a monthly cashflow forecast for 36 months` | Extend model to monthly CF |
| `Add a scenario where churn increases by 20%` | Create new scenario with 20% higher churn |
| `Set tax rate to 25%` | Update tax rate assumption |
| `Run a sensitivity analysis on revenue growth vs EBITDA` | Generate tornado chart |

### 4. Scenarios
Create scenario branches (Base / Upside / Downside / Custom) and switch between them.

### 5. Export
Download the model as a formatted **Excel workbook** or **CSV**.

---

## API Reference

Full interactive docs at http://localhost:8000/docs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/documents/upload` | POST | Upload documents |
| `/api/documents` | GET | List documents |
| `/api/extraction/line-items` | GET | Extracted financial data |
| `/api/extraction/line-items/summary` | GET | Pivot summary |
| `/api/modelling/init` | POST | Initialise model |
| `/api/modelling/command` | POST | Execute NL command |
| `/api/modelling/summary` | GET | Formatted model table |
| `/api/modelling/chart-data` | GET | Chart-ready time series |
| `/api/modelling/scenarios` | GET/POST | Manage scenarios |
| `/api/modelling/sensitivity` | POST | Sensitivity analysis |
| `/api/export/excel` | GET | Download Excel |
| `/api/export/csv` | GET | Download CSV |

---

## Configuration

All configuration is via environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/financial_modelling.db` | Database connection |
| `UPLOAD_DIR` | `./uploads` | File upload directory |
| `MAX_FILE_SIZE_MB` | `50` | Max file size |
| `OPENAI_API_KEY` | _(empty)_ | Enable AI-enhanced NLP |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model |

---

## Supported Financial Data

The extraction engine recognises and normalises:

**Income Statement:** Revenue, COGS, Gross Profit, R&D, S&M, G&A, OPEX, EBITDA, EBIT, Interest, Tax, Net Income

**Balance Sheet:** Cash, Accounts Receivable, Inventory, Total Assets, Accounts Payable, Liabilities, Equity

**Cash Flow:** Operating CF, Capex, Investing CF, Financing CF, Free Cash Flow

**KPIs:** ARR, MRR, Headcount, Churn Rate, NRR, GRR, Customers, ARPU, CAC, LTV

---

## Extending the Platform

- **Add new line-item synonyms**: Edit `backend/app/utils/normalizer.py → FINANCIAL_SYNONYMS`
- **Add new NL commands**: Edit `backend/app/services/nlp_command_parser.py → _parse_rules()`
- **Add new modelling operations**: Edit `backend/app/services/modelling_engine.py`
- **Switch to PostgreSQL**: Set `DATABASE_URL=postgresql://...` in `.env`
- **Enable AI parsing**: Set `OPENAI_API_KEY` in `.env`
