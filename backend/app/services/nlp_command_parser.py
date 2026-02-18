"""
Natural-language command parser.
Maps user instructions to modelling operations without requiring a live LLM.
Falls back to a local rule-based parser; optionally calls OpenAI/Anthropic.
"""
import re
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ParsedCommand:
    raw: str
    intent: str           # e.g. "apply_growth", "add_scenario", "build_forecast", etc.
    target: Optional[str] = None   # e.g. "revenue", "staff_costs"
    value: Optional[float] = None  # e.g. 0.15 for 15%
    periods: Optional[int] = None  # e.g. 36
    frequency: Optional[str] = None  # monthly, quarterly, annual
    scenario_name: Optional[str] = None
    extra: dict = field(default_factory=dict)
    confidence: float = 0.8
    interpreted_as: str = ""


# ─── Rule-based intent patterns ────────────────────────────────────────────────

INTENT_PATTERNS = [
    # Growth rate application
    (
        r"(?:apply|use|set|assume)\s+(?:a\s+)?(\d+(?:\.\d+)?)\s*%\s+(?:growth|increase|rise|uplift)(?:\s+(?:to|for|on|in))?\s*([\w\s]+?)(?:\s+from|\s+in|\s+for|\s*$)",
        "apply_growth",
    ),
    # CAGR modelling
    (
        r"(?:model|use|apply|calculate)\s+(?:a\s+)?(\d+)[\s-]+year\s+(?:cagr|compound annual growth|growth rate)(?:\s+(?:for|on|to))?\s*([\w\s]+)",
        "apply_cagr",
    ),
    # Revenue model
    (
        r"(?:model|build|create|forecast)\s+revenue\s+(?:using|with|via|based on)?\s*([\w\s]+)",
        "model_revenue",
    ),
    # Staff / headcount cost
    (
        r"(?:apply|add|increase|set)\s+(?:a\s+)?(\d+(?:\.\d+)?)\s*%\s+(?:staff|headcount|salary|pay|wage|people|employee)\s+(?:cost|increase|rise|uplift|change)",
        "apply_staff_increase",
    ),
    # Add scenario
    (
        r"add\s+(?:a\s+)?(?:new\s+)?scenario\s+(?:where|with|called|named)?\s*(.*)",
        "add_scenario",
    ),
    # Churn adjustment
    (
        r"(?:increase|decrease|change|set)\s+churn(?:\s+rate)?\s+(?:by|to)?\s+(\d+(?:\.\d+)?)\s*%",
        "adjust_churn",
    ),
    # Cashflow forecast
    (
        r"build\s+(?:a\s+)?(\d+)[\s-]+month\s+(?:monthly\s+)?cashflow\s+forecast",
        "build_cashflow_forecast",
    ),
    # Sensitivity analysis
    (
        r"(?:run|perform|do|create)\s+(?:a\s+)?sensitivity\s+(?:analysis|test|on)?\s*([\w\s]*)",
        "sensitivity_analysis",
    ),
    # Cost modelling
    (
        r"(?:model|apply|set|use|assume)\s+(?:a\s+)?(\d+(?:\.\d+)?)\s*%\s+(?:cost|opex|expense|cogs)\s+(?:increase|growth|margin|ratio)",
        "apply_cost_growth",
    ),
    # Set assumption
    (
        r"(?:set|assume|use)\s+([\w\s]+)\s+(?:to|at|of|=)\s+(\d+(?:\.\d+)?)\s*(%?)",
        "set_assumption",
    ),
    # Export
    (
        r"(?:export|download|generate)\s+(?:as\s+|to\s+)?(excel|csv|pdf)",
        "export",
    ),
    # Show / display
    (
        r"(?:show|display|give me|present)\s+([\w\s]+)",
        "display",
    ),
]


def parse_command(raw_command: str) -> ParsedCommand:
    """
    Parse a natural-language command into a structured ParsedCommand.
    Uses rule-based regex matching; returns best match or a fallback.
    """
    text = raw_command.strip().lower()
    cmd = ParsedCommand(raw=raw_command, intent="unknown")

    for pattern, intent in INTENT_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            cmd.intent = intent
            cmd = _enrich_from_match(cmd, intent, m, text)
            break

    if cmd.intent == "unknown":
        cmd = _fallback_parse(cmd, text)

    cmd.interpreted_as = _describe_command(cmd)
    return cmd


def _enrich_from_match(cmd: ParsedCommand, intent: str, m: re.Match, text: str) -> ParsedCommand:
    groups = m.groups()

    if intent == "apply_growth":
        cmd.value = float(groups[0]) / 100
        cmd.target = groups[1].strip() if len(groups) > 1 else None
        cmd.periods = _extract_years(text)

    elif intent == "apply_cagr":
        cmd.periods = int(groups[0])
        cmd.target = groups[1].strip() if len(groups) > 1 else "revenue"

    elif intent == "model_revenue":
        cmd.target = "revenue"
        cmd.extra["method"] = groups[0].strip() if groups else "cagr"

    elif intent == "apply_staff_increase":
        cmd.value = float(groups[0]) / 100
        cmd.target = "staff_costs"
        cmd.extra["year"] = _extract_year_label(text)

    elif intent == "add_scenario":
        desc = groups[0].strip() if groups else ""
        cmd.scenario_name = _extract_scenario_name(desc)
        cmd.extra["description"] = desc

    elif intent == "adjust_churn":
        cmd.value = float(groups[0]) / 100
        cmd.target = "churn_rate"
        cmd.extra["direction"] = "increase" if "increase" in text else "decrease"

    elif intent == "build_cashflow_forecast":
        cmd.periods = int(groups[0])
        cmd.frequency = "monthly"
        cmd.target = "cashflow"

    elif intent == "sensitivity_analysis":
        cmd.target = groups[0].strip() if groups else "revenue"

    elif intent == "apply_cost_growth":
        cmd.value = float(groups[0]) / 100
        cmd.target = "costs"

    elif intent == "set_assumption":
        cmd.target = groups[0].strip()
        raw_val = float(groups[1])
        cmd.value = raw_val / 100 if groups[2] == "%" else raw_val

    elif intent == "export":
        cmd.extra["format"] = groups[0] if groups else "excel"

    return cmd


def _fallback_parse(cmd: ParsedCommand, text: str) -> ParsedCommand:
    """Catch-all heuristic for commands that didn't match any pattern."""
    if any(w in text for w in ["revenue", "sales", "income"]):
        cmd.intent = "model_revenue"
        cmd.target = "revenue"
    elif any(w in text for w in ["cost", "expense", "opex", "cogs"]):
        cmd.intent = "apply_cost_growth"
        cmd.target = "costs"
    elif any(w in text for w in ["forecast", "project", "model"]):
        cmd.intent = "build_cashflow_forecast"
        cmd.target = "cashflow"
        cmd.periods = _extract_periods(text) or 12
    elif any(w in text for w in ["scenario", "case", "upside", "downside", "bear", "bull"]):
        cmd.intent = "add_scenario"
        cmd.scenario_name = _extract_scenario_name(text)
    else:
        cmd.intent = "display"
        cmd.target = text[:50]
    cmd.confidence = 0.4
    return cmd


def _extract_years(text: str) -> Optional[int]:
    m = re.search(r"(\d+)\s*(?:year|yr)", text, re.IGNORECASE)
    return int(m.group(1)) if m else 3


def _extract_year_label(text: str) -> Optional[str]:
    m = re.search(r"(FY\d{2,4}|\d{4})", text, re.IGNORECASE)
    return m.group(1) if m else None


def _extract_periods(text: str) -> Optional[int]:
    m = re.search(r"(\d+)\s*(?:month|quarter|year|period)", text, re.IGNORECASE)
    return int(m.group(1)) if m else None


def _extract_scenario_name(text: str) -> str:
    for name in ["bear", "bull", "base", "upside", "downside", "optimistic", "pessimistic", "worst", "best"]:
        if name in text.lower():
            return name.capitalize() + " Case"
    # Try to capture "called X" or "named X"
    m = re.search(r"(?:called|named)\s+(['\"]?\w+['\"]?)", text, re.IGNORECASE)
    if m:
        return m.group(1).strip("'\"").title()
    return "Custom Scenario"


def _describe_command(cmd: ParsedCommand) -> str:
    descriptions = {
        "apply_growth": f"Apply {cmd.value*100:.1f}% growth to {cmd.target or 'target'} over {cmd.periods or 3} years",
        "apply_cagr": f"Model {cmd.target or 'revenue'} using {cmd.periods}-year CAGR from historicals",
        "model_revenue": f"Build revenue model for {cmd.target or 'revenue'}",
        "apply_staff_increase": f"Apply {(cmd.value or 0)*100:.1f}% staff cost increase",
        "add_scenario": f"Add scenario: {cmd.scenario_name or 'Custom'}",
        "adjust_churn": f"Adjust churn rate by {(cmd.value or 0)*100:.1f}%",
        "build_cashflow_forecast": f"Build {cmd.periods or 36}-month cashflow forecast",
        "sensitivity_analysis": f"Run sensitivity analysis on {cmd.target or 'key variables'}",
        "apply_cost_growth": f"Apply {(cmd.value or 0)*100:.1f}% cost growth",
        "set_assumption": f"Set {cmd.target} to {cmd.value}",
        "export": f"Export to {cmd.extra.get('format', 'excel').upper()}",
        "display": f"Display {cmd.target or 'model output'}",
        "unknown": f"Unrecognised command: {cmd.raw[:60]}",
    }
    return descriptions.get(cmd.intent, cmd.raw[:80])
