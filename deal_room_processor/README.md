# Deal Room Processor

A self-contained web application for Athletic VC that:

1. Accepts bulk drag-and-drop upload of deal room documents (PDF, DOCX, XLSX, TXT, PPTX, CSV)
2. Extracts text from every file using best-in-class parsing libraries
3. Sends the combined content to Claude 3.5 Sonnet to generate a structured 15-field deal memo
4. Emails the formatted HTML summary to `will@athletic.vc` via SMTP

---

## Requirements

- **Python 3.10 or later** — [python.org/downloads](https://www.python.org/downloads/)
- An **Anthropic API key** — [console.anthropic.com](https://console.anthropic.com/)
- SMTP credentials for an email account (Gmail, Outlook, etc.)

---

## Installation

### 1. Clone / navigate to the project folder

```
cd deal_room_processor
```

### 2. Create and activate a virtual environment

**Windows (Command Prompt):**
```
python -m venv venv
venv\Scripts\activate
```

**Windows (PowerShell):**
```
python -m venv venv
.\venv\Scripts\Activate.ps1
```

*If PowerShell blocks the script, run:*
```
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

**macOS / Linux:**
```
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the template and fill in your values:

```
copy .env.example .env        # Windows
cp .env.example .env          # macOS / Linux
```

Open `.env` in a text editor and set:

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key (`sk-ant-...`) |
| `SMTP_HOST` | Yes | SMTP server hostname |
| `SMTP_PORT` | Yes | `587` (STARTTLS) or `465` (SSL) |
| `SMTP_USERNAME` | Yes | Your email login / address |
| `SMTP_PASSWORD` | Yes | Your email password or App Password |
| `SMTP_FROM` | No | Sender address (defaults to `SMTP_USERNAME`) |
| `EMAIL_RECIPIENT` | No | Recipient address (defaults to `will@athletic.vc`) |
| `PORT` | No | Web server port (default `5000`) |
| `FLASK_DEBUG` | No | Set `true` for development reload (default `false`) |

#### Gmail setup (recommended)

Gmail requires an **App Password** — your regular Gmail password will not work:

1. Enable 2-Step Verification on your Google Account
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Create a new App Password (select "Mail" and "Windows Computer")
4. Use the 16-character password as `SMTP_PASSWORD`

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-address@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
SMTP_FROM=your-address@gmail.com
```

---

## Running the Application

```
python run.py
```

Then open your browser to: **http://127.0.0.1:5000**

---

## Usage

1. Open the app in your browser
2. Drag and drop or click **Browse Files** to select up to 20 documents
3. Click **Process & Send Summary**
4. Wait 20–60 seconds while the app:
   - Extracts text from each document
   - Calls Claude 3.5 Sonnet to generate the structured summary
   - Sends the HTML deal memo to `will@athletic.vc`
5. The results page shows the summary table and email delivery status

---

## Supported File Types

| Extension | Library Used |
|---|---|
| `.pdf` | pdfplumber (+ PyPDF2 fallback) |
| `.docx`, `.doc` | python-docx |
| `.xlsx`, `.xls` | openpyxl |
| `.pptx` | python-pptx |
| `.csv` | Python standard csv module |
| `.txt`, `.md` | Native Python (multi-encoding) |

---

## Deal Summary Fields

The Claude-generated summary always includes these 15 fields:

1. Company Name
2. Founder(s)
3. Date of Meeting
4. Sector / Category
5. Business Summary
6. Stage
7. Current Metrics
8. Traction Highlights
9. Round Details
10. Use of Funds
11. Why Now
12. Competitive Landscape
13. Risks / Open Questions
14. Your Read on the Founder
15. Next Steps

Fields where information could not be found in the documents are marked *Not found*.

---

## Error Handling

All errors are surfaced in the UI — there are no silent failures:

- **Unsupported file types** are skipped and listed as warnings on the results page
- **Extraction failures** (e.g., password-protected PDFs, corrupt files) are shown per-file
- **Claude API errors** (bad key, rate limits, network issues) display the specific error message
- **SMTP errors** (bad credentials, unreachable server) display actionable guidance

---

## File Structure

```
deal_room_processor/
├── run.py                      # Entry point
├── requirements.txt
├── .env.example                # Environment variable template
├── README.md
├── uploads/                    # Temporary file storage (auto-created, auto-cleaned)
└── app/
    ├── __init__.py             # Flask app factory
    ├── routes.py               # Route handlers (upload, process, health)
    ├── document_processor.py   # Text extraction for all supported formats
    ├── claude_client.py        # Anthropic API integration
    ├── email_sender.py         # SMTP delivery
    └── templates/
        ├── index.html          # Upload interface
        └── result.html         # Summary display page
```

---

## Security Notes

- Uploaded files are saved to a per-request UUID subdirectory and **deleted immediately** after processing
- The `.env` file is listed in `.gitignore` — never commit it
- No data is stored persistently — each submission is stateless

---

## Troubleshooting

**`ModuleNotFoundError`** — Make sure your virtual environment is activated and you've run `pip install -r requirements.txt`.

**`ANTHROPIC_API_KEY is not set`** — Check that your `.env` file exists in the `deal_room_processor/` directory and contains the correct key.

**Gmail `SMTPAuthenticationError`** — Use an App Password, not your regular Gmail password. See the Gmail setup section above.

**PDF shows "no extractable text"** — The PDF is likely a scanned image. You would need OCR software (e.g., Adobe Acrobat) to convert it to a text-searchable PDF first.

**Port already in use** — Change `PORT=5001` (or any free port) in your `.env` file.
