"""
Claude API client for structured deal summarization.

Sends combined document text to claude-3-5-sonnet and returns an HTML table
populated with the 15 standard VC deal-memo fields.
"""
import os
from typing import Optional

import anthropic

MODEL = "claude-3-5-sonnet-20241022"

SYSTEM_PROMPT = """You are an expert venture capital analyst with deep experience evaluating
early-stage startups, growth-stage companies, and late-stage private equity deals.

Your job is to read raw deal room documents (pitch decks, financial models, memos, data room exports)
and produce a structured deal summary in HTML table format.

Rules:
- Extract information ONLY from the provided documents. Do not invent facts.
- For fields where information is not present, write exactly: <em>Not found</em>
- Be concise but substantive — each field should contain enough detail to be actionable.
- For "Your Read on the Founder", synthesize tone, credibility, domain expertise, and any
  observable strengths/weaknesses from the way the founder presents the business.
- For "Risks / Open Questions", identify both explicit risks mentioned and implicit ones
  you notice from gaps or inconsistencies in the materials.
- Return ONLY the HTML table — no preamble, no markdown fences, no extra text."""

FIELD_DESCRIPTIONS = [
    ("Company Name", "Legal or operating name of the company"),
    ("Founder(s)", "Names and roles of the founding team"),
    ("Date of Meeting", "Date the meeting occurred or the pitch deck was dated"),
    ("Sector / Category", "Industry vertical, sub-sector, and technology category"),
    ("Business Summary", "2–4 sentence plain-English description of what the company does and how it makes money"),
    ("Stage", "Current company stage: Pre-seed, Seed, Series A/B/C, Growth, PE, etc."),
    ("Current Metrics", "Key financial and operational KPIs: ARR/MRR, revenue, burn rate, headcount, customers, etc."),
    ("Traction Highlights", "The most compelling evidence of product-market fit or business momentum"),
    ("Round Details", "Raise amount, instrument (SAFE, priced round, etc.), valuation cap / pre-money, lead investor if known"),
    ("Use of Funds", "How the capital will be deployed across hiring, product, sales, etc."),
    ("Why Now", "Market timing argument — regulatory changes, technology shifts, behavioral trends"),
    ("Competitive Landscape", "Named competitors and differentiation; how the company positions itself"),
    ("Risks / Open Questions", "Top 3–5 risks or diligence questions the investment team should pursue"),
    ("Your Read on the Founder", "Qualitative assessment of founder quality, domain expertise, coachability, and red flags if any"),
    ("Next Steps", "Recommended follow-up actions: second meeting, intro calls, diligence requests, pass"),
]


def _build_user_prompt(document_text: str) -> str:
    fields_block = "\n".join(
        f"  <tr><th>{name}</th><td><!-- {hint} --></td></tr>"
        for name, hint in FIELD_DESCRIPTIONS
    )
    return f"""Below are the contents of one or more documents from a startup deal room.
Analyze them carefully and populate every field in the HTML table template below.

---DOCUMENT CONTENT START---
{document_text}
---DOCUMENT CONTENT END---

Return a complete HTML table using exactly this structure (replace the comments with your analysis):

<table border="1" cellpadding="10" cellspacing="0" style="border-collapse:collapse; width:100%; font-family:Arial,sans-serif;">
  <colgroup>
    <col style="width:22%; background:#f0f4f8; font-weight:bold;">
    <col style="width:78%;">
  </colgroup>
  <tbody>
{fields_block}
  </tbody>
</table>

Important: return ONLY the <table>…</table> HTML. No other text."""


class ClaudeAPIError(Exception):
    """Raised when the Claude API call fails."""


def summarize_documents(document_text: str, api_key: Optional[str] = None) -> str:
    """
    Send combined document text to Claude and return an HTML table string.

    Args:
        document_text: Combined plain-text extracted from all uploaded files.
        api_key: Anthropic API key. Defaults to ANTHROPIC_API_KEY env var.

    Returns:
        HTML string containing the deal summary table.

    Raises:
        ClaudeAPIError: on any API or network failure.
        ValueError: if no API key is available.
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise ValueError(
            "ANTHROPIC_API_KEY is not set. "
            "Add it to your .env file or set it as an environment variable."
        )

    if not document_text.strip():
        raise ValueError("No document text was extracted — cannot generate a summary.")

    client = anthropic.Anthropic(api_key=key)

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": _build_user_prompt(document_text)}
            ],
        )
    except anthropic.AuthenticationError as exc:
        raise ClaudeAPIError(
            "Invalid Anthropic API key. Check your ANTHROPIC_API_KEY value."
        ) from exc
    except anthropic.RateLimitError as exc:
        raise ClaudeAPIError(
            "Anthropic API rate limit exceeded. Please wait a moment and try again."
        ) from exc
    except anthropic.APIConnectionError as exc:
        raise ClaudeAPIError(
            f"Could not connect to the Anthropic API. Check your internet connection. ({exc})"
        ) from exc
    except anthropic.APIStatusError as exc:
        raise ClaudeAPIError(
            f"Anthropic API returned an error (HTTP {exc.status_code}): {exc.message}"
        ) from exc
    except Exception as exc:
        raise ClaudeAPIError(f"Unexpected error calling Claude API: {exc}") from exc

    # Extract text from the response
    if not message.content:
        raise ClaudeAPIError("Claude returned an empty response.")

    html = message.content[0].text.strip()

    # Sanity-check: the response should contain a table
    if "<table" not in html.lower():
        raise ClaudeAPIError(
            f"Claude response did not contain an HTML table. "
            f"Raw response (first 500 chars): {html[:500]}"
        )

    return html
