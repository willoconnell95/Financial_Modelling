# Athletic VC — Deal Processor

A self-contained web application that:

1. Accepts bulk drag-and-drop uploads of deal documents (PDF, DOCX, TXT, XLSX, CSV)
2. Extracts all text and sends it to Claude for a structured 15-field investment summary
3. Displays the summary in the browser and automatically emails it to `will@athletic.vc`

---

## File Structure

```
deal_processor/
├── app.py                   # Flask entry point & route handlers
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variable template
├── README.md                # This file
├── templates/
│   └── index.html           # Main UI (drag-and-drop + results)
├── static/
│   ├── css/style.css        # Styling
│   └── js/app.js            # Frontend logic
├── utils/
│   ├── __init__.py
│   ├── document_parser.py   # PDF / DOCX / XLSX / CSV / TXT extraction
│   ├── claude_api.py        # Anthropic API call & prompt
│   └── email_sender.py      # SMTP delivery
└── uploads/                 # Temporary file storage (auto-created, gitignored)
```

---

## Prerequisites

- **Python 3.9 or later** — [python.org/downloads](https://www.python.org/downloads/)
- An **Anthropic API key** — [console.anthropic.com](https://console.anthropic.com)
- An SMTP-enabled email account (Gmail or Outlook recommended)

---

## Installation

### 1. Open a terminal in the `deal_processor/` folder

```bash
cd deal_processor
```

### 2. Create and activate a virtual environment

**Windows (Command Prompt)**
```cmd
python -m venv venv
venv\Scripts\activate
```

**Windows (PowerShell)**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux
```

Edit `.env` and fill in:

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `SMTP_HOST` | SMTP server (e.g. `smtp.gmail.com`) |
| `SMTP_PORT` | `587` (STARTTLS) or `465` (SSL) |
| `SMTP_USERNAME` | Your email address |
| `SMTP_PASSWORD` | Your email password or App Password |
| `SMTP_SENDER` | From address (defaults to `SMTP_USERNAME`) |

**Gmail users:** You must use an [App Password](https://support.google.com/accounts/answer/185833), not your regular Gmail password. Enable 2-Step Verification first, then create the App Password under your Google Account security settings.

---

## Running the App

```bash
python app.py
```

Then open your browser and navigate to:

```
http://localhost:5000
```

---

## Usage

1. **Drag and drop** your deal documents into the upload area, or click to browse.
   Supported formats: PDF, DOCX, DOC, XLSX, XLS, CSV, TXT, MD
2. Click **"Process & Email Summary"**.
3. The app will:
   - Extract text from every uploaded file
   - Send the combined content to Claude (`claude-3-5-sonnet`) for analysis
   - Display the structured HTML summary in the browser
   - Automatically email the summary to `will@athletic.vc`
4. Use **Print / PDF** to save the summary locally, or **Copy HTML** to paste it elsewhere.

---

## Summary Fields

The generated table includes these 15 fields in order:

| # | Field |
|---|---|
| 1 | Company Name |
| 2 | Founder(s) |
| 3 | Date of Meeting |
| 4 | Sector / Category |
| 5 | Business Summary |
| 6 | Stage |
| 7 | Current Metrics |
| 8 | Traction Highlights |
| 9 | Round Details |
| 10 | Use of Funds |
| 11 | Why Now |
| 12 | Competitive Landscape |
| 13 | Risks / Open Questions |
| 14 | Your Read on the Founder |
| 15 | Next Steps |

Fields that cannot be inferred from the documents are marked **"Not found"**.

---

## Error Handling

All errors surface visibly in the UI — there are no silent failures:

- **Extraction errors** — shown as warnings; processing continues with successfully extracted files
- **Claude API errors** — shown as a full error banner with the server's message
- **SMTP errors** — the summary is still shown in the browser; the email error is shown separately
- **Missing credentials** — clear message directing you to the `.env` file

---

## Troubleshooting

**`ANTHROPIC_API_KEY is not set`**
→ Make sure your `.env` file is in the `deal_processor/` directory (same folder as `app.py`).

**`SMTP authentication failed`**
→ For Gmail, ensure you are using an App Password (not your normal password) and that 2FA is enabled.
→ For Outlook, check that SMTP AUTH is enabled on the account.

**`PDF extracted no text`**
→ The PDF may be scanned (image-only). Consider running it through an OCR tool first.

**Port 5000 already in use**
→ Set `PORT=5001` (or any free port) in your `.env` file and restart.

---

## Security Notes

- Never commit your `.env` file — it is listed in `.gitignore`
- The `uploads/` directory stores files only for the duration of a single request; they are deleted immediately after processing
- The app is designed for local/trusted-network use only; do not expose it to the public internet without adding authentication
