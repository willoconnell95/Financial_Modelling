"""
claude_api.py
-------------
Calls the Anthropic Claude API to produce a structured HTML deal summary
from combined document text.
"""

import logging
import os

import anthropic

logger = logging.getLogger(__name__)

MODEL = "claude-3-5-sonnet-20241022"

# The 15 required fields in the exact display order
SUMMARY_FIELDS = [
    "Company Name",
    "Founder(s)",
    "Date of Meeting",
    "Sector / Category",
    "Business Summary",
    "Stage",
    "Current Metrics",
    "Traction Highlights",
    "Round Details",
    "Use of Funds",
    "Why Now",
    "Competitive Landscape",
    "Risks / Open Questions",
    "Your Read on the Founder",
    "Next Steps",
]

SYSTEM_PROMPT = """You are a senior investment analyst at an early-stage venture capital and growth / \
late-stage private equity firm. You are given raw text extracted from a startup's data room \
(pitch decks, financial models, investor memos, product overviews, etc.).

Your task is to produce a concise but information-rich HTML deal summary table for use in \
internal investment memos. Be analytical and direct. Where information is present, synthesise \
it clearly. Where it is absent, write exactly "Not found".

Return ONLY valid HTML — nothing before or after the HTML block. Do not include markdown \
code fences or any prose outside the HTML. The output must begin with <table and end with </table>.
"""

USER_TEMPLATE = """Analyse the document content below and produce an HTML summary table.

The table must have exactly these rows, in this order, with a left column for the field name \
and a right column for the extracted / inferred value:

{fields}

Formatting rules:
- Use a <table> element with inline styles for clean rendering in email clients.
- The table should have a full-width border, alternating row colours, and clear header styling.
- Field names (left column) should be bold.
- Multi-point answers should use <ul><li> lists inside the table cell.
- Numbers and dates should be formatted clearly.
- Do not truncate information — include all material details found.

--- DOCUMENT CONTENT BELOW ---

{document_text}
"""


def generate_deal_summary(combined_text: str) -> str:
    """
    Send *combined_text* to Claude and return an HTML table string.

    Raises
    ------
    RuntimeError
        If the API key is not set or the API returns an error.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. "
            "Add it to your .env file or set it as an environment variable."
        )

    client = anthropic.Anthropic(api_key=api_key)

    fields_list = "\n".join(f"- {f}" for f in SUMMARY_FIELDS)
    user_content = USER_TEMPLATE.format(
        fields=fields_list,
        document_text=combined_text,
    )

    logger.info("Sending %d characters to Claude (%s)…", len(combined_text), MODEL)

    message = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    raw = message.content[0].text.strip()
    logger.info("Received response from Claude (%d chars)", len(raw))

    # Ensure we hand back valid HTML — strip any accidental markdown fences
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(
            line for line in lines if not line.startswith("```")
        ).strip()

    return _wrap_table_html(raw)


def _wrap_table_html(table_html: str) -> str:
    """
    Wrap the bare <table> element in a minimal HTML document suitable for
    both inline rendering in the UI and email delivery.
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Deal Summary</title>
<style>
  body {{ font-family: Arial, Helvetica, sans-serif; font-size: 14px; color: #1a1a1a; }}
  table {{ border-collapse: collapse; width: 100%; max-width: 900px; }}
  td, th {{ border: 1px solid #cccccc; padding: 10px 14px; vertical-align: top; }}
  tr:nth-child(even) td {{ background-color: #f7f7f7; }}
  td:first-child {{ font-weight: bold; width: 22%; white-space: nowrap; color: #2c3e50; }}
  ul {{ margin: 4px 0; padding-left: 18px; }}
  li {{ margin-bottom: 3px; }}
</style>
</head>
<body>
{table_html}
</body>
</html>"""
