"""
Natural-language command parser.

Parses user instructions like:
  "Model revenue using a 3-year CAGR of 15% from historicals"
  "Apply a 15% staff cost increase from FY25"
  "Add a scenario where churn increases by 20%"
  "Build a monthly cashflow forecast for 36 months"
  "Set tax rate to 25%"
  "Run a sensitivity analysis on revenue growth vs EBITDA"

Falls back to OpenAI if OPENAI_API_KEY is set.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from loguru import logger

from app.config import settings
from app.services.modelling_engine import ModelOperation


@dataclass
class ParsedCommand:
    operation: str
    params: dict = field(default_factory=dict)
    confidence: float = 1.0
    raw_command: str = ""
    explanation: str = ""


class NLPCommandParser:
    """
    Rule-based NLP parser with optional OpenAI fallback.
    """

    # Metric aliases
    METRIC_ALIASES: dict[str, str] = {
        "revenue": "revenue", "sales": "revenue", "turnover": "revenue",
        "cogs": "cogs", "cost of goods sold": "cogs", "cost of sales": "cogs",
        "gross profit": "gross_profit",
        "opex": "operating_expenses", "operating expenses": "operating_expenses",
        "ebitda": "ebitda",
        "ebit": "ebit",
        "net income": "net_income", "net profit": "net_income",
        "arr": "arr", "annual recurring revenue": "arr",
        "mrr": "mrr", "monthly recurring revenue": "mrr",
        "headcount": "headcount", "staff": "headcount", "employees": "headcount",
        "staff cost": "staff_cost", "staff costs": "staff_cost",
        "payroll": "staff_cost", "salaries": "staff_cost",
        "churn": "churn_rate", "churn rate": "churn_rate",
        "capex": "capex", "capital expenditure": "capex",
        "free cash flow": "free_cash_flow", "fcf": "free_cash_flow",
        "gross margin": "gross_margin_pct",
        "tax": "tax", "tax rate": "tax_rate",
        "interest": "interest_expense",
    }

    PERIOD_ALIASES: dict[str, str] = {
        "this year": None,  # resolved at runtime
        "next year": None,
        "fy24": "FY2024", "fy25": "FY2025", "fy26": "FY2026",
        "fy2024": "FY2024", "fy2025": "FY2025", "fy2026": "FY2026",
        "2024": "FY2024", "2025": "FY2025", "2026": "FY2026",
    }

    def parse(self, command: str) -> ParsedCommand:
        """Parse a natural language command into a structured ModelOperation."""
        raw = command.strip()

        # Try OpenAI first if key is configured
        if settings.OPENAI_API_KEY:
            try:
                result = self._parse_openai(raw)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"OpenAI parse failed, falling back to rules: {e}")

        return self._parse_rules(raw)

    def _parse_rules(self, command: str) -> ParsedCommand:
        """Rule-based parsing using regex patterns."""
        cmd_lower = command.lower().strip()

        # ── Revenue / metric CAGR modelling ──────────────────────────────
        m = re.search(
            r"model\s+([\w\s]+?)\s+using\s+a?\s*(\d+(?:\.\d+)?)\s*(?:-year|-yr)?\s*cagr\s*(?:of\s*)?(?:(\d+(?:\.\d+)?)\s*%)?",
            cmd_lower,
        )
        if m:
            metric = self._resolve_metric(m.group(1).strip())
            # If third group has the rate
            rate_pct_str = m.group(3) or m.group(2)
            # If only one number, it might be the rate or the years
            try:
                rate = float(rate_pct_str) / 100
            except (TypeError, ValueError):
                rate = 0.10
            return ParsedCommand(
                operation="apply_cagr",
                params={"metric": metric, "cagr_rate": rate},
                explanation=f"Apply {rate*100:.1f}% CAGR to {metric}",
                raw_command=command,
            )

        # Generic CAGR: "apply X% CAGR to revenue"
        m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*cagr\s+(?:to\s+)?([\w\s]+)", cmd_lower)
        if m:
            rate = float(m.group(1)) / 100
            metric = self._resolve_metric(m.group(2).strip())
            return ParsedCommand(
                operation="apply_cagr",
                params={"metric": metric, "cagr_rate": rate},
                explanation=f"Apply {m.group(1)}% CAGR to {metric}",
                raw_command=command,
            )

        # ── Growth rate: "grow revenue at 15% per year" ──────────────────
        m = re.search(
            r"grow\s+([\w\s]+?)\s+(?:at|by)\s+(\d+(?:\.\d+)?)\s*%",
            cmd_lower,
        )
        if m:
            metric = self._resolve_metric(m.group(1).strip())
            rate = float(m.group(2)) / 100
            return ParsedCommand(
                operation="apply_growth_rate",
                params={"metric": metric, "rate": rate},
                explanation=f"Grow {metric} at {m.group(2)}% per period",
                raw_command=command,
            )

        # ── Percentage increase: "apply 15% staff cost increase from FY25" ─
        m = re.search(
            r"apply\s+(?:a\s+)?(\d+(?:\.\d+)?)\s*%\s+([\w\s]+?)\s+(?:increase|raise|uplift|growth)"
            r"(?:\s+from\s+([\w\s\d]+))?",
            cmd_lower,
        )
        if m:
            pct = float(m.group(1)) / 100
            metric = self._resolve_metric(m.group(2).strip())
            start_period = self._resolve_period(m.group(3).strip()) if m.group(3) else None
            params = {"metric": metric, "rate": pct}
            if start_period:
                params["start_period"] = start_period
            return ParsedCommand(
                operation="apply_growth_rate",
                params=params,
                explanation=f"Apply {m.group(1)}% increase to {metric}" + (f" from {start_period}" if start_period else ""),
                raw_command=command,
            )

        # ── Percentage decrease: "reduce churn by 20%" ──────────────────
        m = re.search(
            r"(?:reduce|decrease|cut|lower)\s+([\w\s]+?)\s+by\s+(\d+(?:\.\d+)?)\s*%",
            cmd_lower,
        )
        if m:
            metric = self._resolve_metric(m.group(1).strip())
            pct = -float(m.group(2)) / 100
            return ParsedCommand(
                operation="apply_growth_rate",
                params={"metric": metric, "rate": pct},
                explanation=f"Reduce {metric} by {m.group(2)}%",
                raw_command=command,
            )

        # ── Add scenario ─────────────────────────────────────────────────
        m = re.search(
            r"add\s+(?:a\s+)?scenario\s+(?:where|with|that)?\s+(.*)",
            cmd_lower,
        )
        if m:
            description = m.group(1).strip()
            modifications = self._parse_scenario_description(description)
            scenario_name = f"scenario_{description[:20].replace(' ', '_')}"
            return ParsedCommand(
                operation="add_scenario",
                params={
                    "scenario_name": scenario_name,
                    "description": description,
                    "modifications": modifications,
                },
                explanation=f"Create new scenario: {description}",
                raw_command=command,
            )

        # ── Build cashflow ────────────────────────────────────────────────
        m = re.search(
            r"build\s+(?:a\s+)?(monthly|quarterly|annual)?\s*(?:cash\s*flow|cashflow)\s*(?:forecast|model)?"
            r"(?:\s+for\s+(\d+)\s+(?:months?|quarters?|years?))?",
            cmd_lower,
        )
        if m:
            period_type = m.group(1) or "monthly"
            n = int(m.group(2)) if m.group(2) else 36
            return ParsedCommand(
                operation="build_cashflow",
                params={"period_type": period_type, "periods": n},
                explanation=f"Build {period_type} cashflow for {n} periods",
                raw_command=command,
            )

        # ── Set assumption ────────────────────────────────────────────────
        m = re.search(
            r"set\s+([\w\s]+?)\s+(?:to|at|=)\s+(\d+(?:\.\d+)?)\s*%?",
            cmd_lower,
        )
        if m:
            key = self._resolve_assumption_key(m.group(1).strip())
            raw_val = m.group(2)
            val = float(raw_val)
            # If it looks like a percentage
            if "%" in command or val > 1:
                if val > 1:
                    val = val / 100
            return ParsedCommand(
                operation="set_assumption",
                params={"key": key, "value": val},
                explanation=f"Set {key} to {raw_val}",
                raw_command=command,
            )

        # ── Sensitivity analysis ──────────────────────────────────────────
        m = re.search(
            r"sensitivity\s+(?:analysis\s+)?(?:on\s+)?([\w\s]+?)\s+(?:vs|versus|against|on)\s+([\w\s]+)",
            cmd_lower,
        )
        if m:
            variable = self._resolve_assumption_key(m.group(1).strip())
            output = self._resolve_metric(m.group(2).strip())
            return ParsedCommand(
                operation="sensitivity_analysis",
                params={"variable": variable, "output_metric": output},
                explanation=f"Sensitivity: {variable} vs {output}",
                raw_command=command,
            )

        # ── Margin setting ────────────────────────────────────────────────
        m = re.search(
            r"set\s+([\w\s]+?)\s+margin\s+(?:to|at|=)\s+(\d+(?:\.\d+)?)\s*%",
            cmd_lower,
        )
        if m:
            metric_str = m.group(1).strip()
            margin_pct = float(m.group(2)) / 100
            # Infer cost line from margin type
            if "gross" in metric_str:
                metric = "cogs"
                margin = 1 - margin_pct  # COGS = 1 - gross_margin
            else:
                metric = self._resolve_metric(metric_str)
                margin = margin_pct
            return ParsedCommand(
                operation="set_margin",
                params={"metric": metric, "margin": margin},
                explanation=f"Set {metric_str} margin to {m.group(2)}%",
                raw_command=command,
            )

        # ── Headcount / hiring plan ───────────────────────────────────────
        m = re.search(
            r"(?:set|add|model)\s+(?:total\s+)?headcount\s+(?:to|of|at)?\s+(\d+)"
            r"(?:\s+with\s+(?:an?\s+)?(?:average\s+)?salary\s+(?:of\s+)?([\d,]+))?",
            cmd_lower,
        )
        if m:
            hc = int(m.group(1))
            salary_raw = m.group(2) or "60000"
            salary = float(salary_raw.replace(",", ""))
            return ParsedCommand(
                operation="set_headcount",
                params={"headcount": hc, "avg_salary": salary},
                explanation=f"Set headcount to {hc} with avg salary {salary:,.0f}",
                raw_command=command,
            )

        # ── Forecast extension ────────────────────────────────────────────
        m = re.search(
            r"(?:extend|forecast|project)\s+(?:for\s+)?(\d+)\s+(months?|quarters?|years?)",
            cmd_lower,
        )
        if m:
            n = int(m.group(1))
            unit = m.group(2).lower()
            if "month" in unit:
                period_type = "monthly"
            elif "quarter" in unit:
                period_type = "quarterly"
            else:
                period_type = "annual"
            return ParsedCommand(
                operation="build_cashflow",
                params={"period_type": period_type, "periods": n},
                explanation=f"Extend forecast for {n} {unit}",
                raw_command=command,
            )

        # ── Fallback ──────────────────────────────────────────────────────
        return ParsedCommand(
            operation="unknown",
            params={"raw": command},
            confidence=0.0,
            explanation="Command not understood. Try: 'Model revenue using 15% CAGR', 'Set gross margin to 65%', etc.",
            raw_command=command,
        )

    def _resolve_metric(self, raw: str) -> str:
        clean = raw.lower().strip()
        for alias, canonical in self.METRIC_ALIASES.items():
            if alias in clean:
                return canonical
        # Return normalised snake_case as best guess
        return re.sub(r"\s+", "_", clean)

    def _resolve_period(self, raw: Optional[str]) -> Optional[str]:
        if not raw:
            return None
        clean = raw.lower().strip()
        for alias, canonical in self.PERIOD_ALIASES.items():
            if alias in clean:
                return canonical
        # Try to match FY pattern
        m = re.match(r"fy\s*(\d{2,4})", clean, re.IGNORECASE)
        if m:
            yr = int(m.group(1))
            if yr < 100:
                yr += 2000
            return f"FY{yr}"
        return raw.upper()

    def _resolve_assumption_key(self, raw: str) -> str:
        key_map = {
            "revenue growth": "revenue_growth_rate",
            "revenue growth rate": "revenue_growth_rate",
            "growth rate": "revenue_growth_rate",
            "gross margin": "gross_margin",
            "tax rate": "tax_rate",
            "tax": "tax_rate",
            "opex growth": "opex_growth_rate",
            "staff cost increase": "staff_cost_increase",
            "salary increase": "staff_cost_increase",
            "churn": "churn_rate",
            "churn rate": "churn_rate",
            "capex": "capex_pct_revenue",
            "discount rate": "discount_rate",
            "wacc": "wacc",
        }
        clean = raw.lower().strip()
        for k, v in key_map.items():
            if k in clean:
                return v
        return re.sub(r"\s+", "_", clean)

    def _parse_scenario_description(self, description: str) -> list[dict]:
        """Extract modifications from a scenario description."""
        modifications = []
        cmd = self._parse_rules(description)
        if cmd.operation != "unknown":
            modifications.append({"operation": cmd.operation, "params": cmd.params})
        return modifications

    # ------------------------------------------------------------------
    # OpenAI fallback
    # ------------------------------------------------------------------
    def _parse_openai(self, command: str) -> Optional[ParsedCommand]:
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        system_prompt = """You are a financial modelling assistant. Parse user commands into structured operations.

Return a JSON object with:
{
  "operation": "<one of: apply_cagr | apply_growth_rate | apply_fixed_increase | set_margin | set_headcount | build_cashflow | set_assumption | add_scenario | sensitivity_analysis>",
  "params": { ... operation-specific params ... },
  "explanation": "<one sentence explaining what will happen>"
}

Available operations and their params:
- apply_cagr: {metric: str, cagr_rate: float (as decimal), from_period: optional str}
- apply_growth_rate: {metric: str, rate: float (as decimal), start_period: optional str}
- apply_fixed_increase: {metric: str, increase: float, start_period: optional str}
- set_margin: {metric: str, margin: float (as decimal)}
- set_headcount: {headcount: int, avg_salary: float, growth_rate: optional float}
- build_cashflow: {period_type: "monthly"|"quarterly"|"annual", periods: int}
- set_assumption: {key: str, value: float}
- add_scenario: {scenario_name: str, modifications: list[{operation, params}]}
- sensitivity_analysis: {variable: str, output_metric: str, range_pct: optional float}

Metric names: revenue, cogs, gross_profit, operating_expenses, ebitda, ebit, net_income,
              arr, mrr, headcount, staff_cost, churn_rate, capex, free_cash_flow

Return only valid JSON, no markdown."""

        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": command},
            ],
            temperature=0,
            max_tokens=500,
        )

        content = response.choices[0].message.content.strip()
        parsed = json.loads(content)

        return ParsedCommand(
            operation=parsed["operation"],
            params=parsed.get("params", {}),
            confidence=0.95,
            explanation=parsed.get("explanation", ""),
            raw_command=command,
        )
