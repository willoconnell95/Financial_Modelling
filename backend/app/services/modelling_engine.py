"""
Financial Modelling Engine.

Stores all financial variables in a structured format and supports:
  - Revenue modelling (CAGR, growth rates, drivers)
  - Cost modelling (fixed/variable, % of revenue)
  - Headcount modelling (by dept, salary)
  - Cashflow modelling
  - Scenario analysis
  - Sensitivity analysis

The model state is a dict of {line_item: {period: value}}.
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from typing import Any, Optional

from loguru import logger


# ---------------------------------------------------------------------------
# Period helpers
# ---------------------------------------------------------------------------

def _generate_periods(start: str, end: str, period_type: str) -> list[str]:
    """Generate a list of period labels between start and end (inclusive)."""
    if period_type == "monthly":
        fmt_in = "%Y-%m"
        delta = relativedelta(months=1)
        fmt_out = "%Y-%m"
    elif period_type == "quarterly":
        # We'll use custom logic for quarters
        return _generate_quarters(start, end)
    else:  # annual
        return _generate_annual(start, end)

    try:
        cur = datetime.strptime(start, fmt_in)
        end_dt = datetime.strptime(end, fmt_in)
    except ValueError:
        return []

    periods = []
    while cur <= end_dt:
        periods.append(cur.strftime(fmt_out))
        cur += delta
    return periods


def _generate_quarters(start: str, end: str) -> list[str]:
    # Format: YYYY-QN
    import re
    def parse_q(s):
        m = re.match(r"(\d{4})-Q([1-4])", s)
        if not m:
            return None, None
        return int(m.group(1)), int(m.group(2))

    sy, sq = parse_q(start)
    ey, eq = parse_q(end)
    if sy is None:
        return []

    periods = []
    y, q = sy, sq
    while (y, q) <= (ey, eq):
        periods.append(f"{y}-Q{q}")
        q += 1
        if q > 4:
            q = 1
            y += 1
    return periods


def _generate_annual(start: str, end: str) -> list[str]:
    import re
    def parse_fy(s):
        m = re.match(r"FY?(\d{4})", s)
        return int(m.group(1)) if m else None

    sy = parse_fy(start)
    ey = parse_fy(end)
    if sy is None or ey is None:
        try:
            sy, ey = int(start), int(end)
        except ValueError:
            return []
    return [f"FY{y}" for y in range(sy, ey + 1)]


def _period_index(period: str, periods: list[str]) -> int:
    try:
        return periods.index(period)
    except ValueError:
        return -1


# ---------------------------------------------------------------------------
# Model operations (dataclass commands)
# ---------------------------------------------------------------------------

@dataclass
class ModelOperation:
    operation: str          # e.g. "apply_cagr", "set_assumption", "add_scenario"
    params: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Modelling Engine
# ---------------------------------------------------------------------------

class ModellingEngine:
    """
    Stateless engine that operates on a model_state dict.
    All mutation methods return a NEW (deep-copied) state.
    """

    # Standard P&L formula cascade
    DERIVED_FORMULAS = [
        ("gross_profit",        "revenue - cogs"),
        ("operating_expenses",  "sales_and_marketing + general_and_admin + research_and_development"),
        ("ebitda",              "gross_profit - operating_expenses"),
        ("ebit",                "ebitda - depreciation_amortization"),
        ("net_income",          "ebit - interest_expense - tax"),
        ("free_cash_flow",      "operating_cashflow - capex"),
        ("gross_margin_pct",    "gross_profit / revenue * 100"),
        ("ebitda_margin_pct",   "ebitda / revenue * 100"),
        ("net_margin_pct",      "net_income / revenue * 100"),
    ]

    # ------------------------------------------------------------------ #
    # Initialise a blank model from database line items
    # ------------------------------------------------------------------ #

    def build_from_extracted(
        self,
        line_items: list[dict],
        period_type: str = "annual",
        forecast_periods: int = 3,
    ) -> dict:
        """
        Construct an initial model state from extracted FinancialLineItems.
        Returns model_state dict.
        """
        # Group by (normalized_name, period)
        data: dict[str, dict[str, float]] = {}
        periods_seen: set[str] = set()

        for item in line_items:
            name = item.get("normalized_name")
            period = item.get("period")
            value = item.get("value")
            if name and period and value is not None:
                if name not in data:
                    data[name] = {}
                data[name][period] = value
                periods_seen.add(period)

        # Sort historical periods
        historical_periods = sorted(periods_seen)

        # Determine forecast periods
        forecast_ps = self._compute_forecast_periods(
            historical_periods, period_type, forecast_periods
        )
        all_periods = historical_periods + forecast_ps

        time_config = {
            "period_type": period_type,
            "historical_periods": historical_periods,
            "forecast_periods": forecast_ps,
            "all_periods": all_periods,
            "forecast_start": forecast_ps[0] if forecast_ps else None,
        }

        assumptions = {
            "revenue_growth_rate": 0.10,
            "gross_margin": None,  # derived from historicals if possible
            "opex_growth_rate": 0.08,
            "staff_cost_increase": 0.05,
            "tax_rate": 0.25,
            "capex_pct_revenue": 0.03,
            "churn_rate": None,
        }

        # Infer gross margin from historicals
        if "revenue" in data and "gross_profit" in data:
            revs = [v for p, v in data["revenue"].items() if v]
            gps = [v for p, v in data["gross_profit"].items() if v]
            if revs and gps and len(revs) == len(gps):
                assumptions["gross_margin"] = round(
                    sum(g / r for g, r in zip(gps, revs)) / len(revs), 4
                )

        return {
            "line_items": data,
            "assumptions": assumptions,
            "time_config": time_config,
            "formulas": dict(self.DERIVED_FORMULAS),
            "scenario": "base",
        }

    def _compute_forecast_periods(
        self, historical: list[str], period_type: str, n: int
    ) -> list[str]:
        if not historical:
            if period_type == "monthly":
                start = datetime.now().strftime("%Y-%m")
            elif period_type == "quarterly":
                q = (datetime.now().month - 1) // 3 + 1
                start = f"{datetime.now().year}-Q{q}"
            else:
                start = f"FY{datetime.now().year}"
            last = start
        else:
            last = historical[-1]

        result = []
        cur = last
        for _ in range(n):
            cur = self._next_period(cur, period_type)
            result.append(cur)
        return result

    def _next_period(self, period: str, period_type: str) -> str:
        import re
        if period_type == "monthly":
            dt = datetime.strptime(period, "%Y-%m")
            dt += relativedelta(months=1)
            return dt.strftime("%Y-%m")
        elif period_type == "quarterly":
            m = re.match(r"(\d{4})-Q([1-4])", period)
            if m:
                y, q = int(m.group(1)), int(m.group(2))
                q += 1
                if q > 4:
                    q = 1; y += 1
                return f"{y}-Q{q}"
        else:  # annual
            m = re.match(r"FY(\d{4})", period)
            if m:
                return f"FY{int(m.group(1)) + 1}"
        return period

    # ------------------------------------------------------------------ #
    # Core modelling operations
    # ------------------------------------------------------------------ #

    def apply_cagr(
        self,
        state: dict,
        metric: str,
        cagr_rate: float,
        from_period: Optional[str] = None,
    ) -> dict:
        """
        Apply CAGR growth to a metric over all forecast periods.
        Uses the last historical value as the base.
        """
        state = copy.deepcopy(state)
        line_items = state["line_items"]
        time_cfg = state["time_config"]
        hist = time_cfg.get("historical_periods", [])
        forecast = time_cfg.get("forecast_periods", [])
        all_periods = time_cfg.get("all_periods", [])

        if metric not in line_items:
            line_items[metric] = {}

        # Find base value
        base_period = from_period or (hist[-1] if hist else None)
        if base_period is None:
            logger.warning(f"No base period for CAGR on {metric}")
            return state

        base_val = line_items[metric].get(base_period)
        if base_val is None:
            # Try last available
            for p in reversed(hist):
                if p in line_items[metric]:
                    base_val = line_items[metric][p]
                    base_period = p
                    break

        if base_val is None:
            logger.warning(f"No base value found for {metric}")
            return state

        base_idx = _period_index(base_period, all_periods)

        for fp in forecast:
            fp_idx = _period_index(fp, all_periods)
            n = fp_idx - base_idx
            if n <= 0:
                continue
            line_items[metric][fp] = round(base_val * (1 + cagr_rate) ** n, 2)

        state["line_items"] = line_items
        return self.recalculate_derived(state)

    def apply_growth_rate(
        self,
        state: dict,
        metric: str,
        rate: float,
        start_period: Optional[str] = None,
    ) -> dict:
        """
        Apply a period-on-period growth rate from start_period onwards.
        """
        state = copy.deepcopy(state)
        line_items = state["line_items"]
        time_cfg = state["time_config"]
        forecast = time_cfg.get("forecast_periods", [])
        hist = time_cfg.get("historical_periods", [])
        all_periods = time_cfg.get("all_periods", [])

        if metric not in line_items:
            line_items[metric] = {}

        effective_start = start_period or (forecast[0] if forecast else None)
        if effective_start is None:
            return state

        start_idx = _period_index(effective_start, all_periods)
        if start_idx <= 0:
            # Get last historical value
            prev_val = None
            for p in reversed(hist):
                if p in line_items[metric]:
                    prev_val = line_items[metric][p]
                    break
        else:
            prev_val = line_items[metric].get(all_periods[start_idx - 1])

        if prev_val is None:
            prev_val = 0.0

        for p in all_periods[start_idx:]:
            if p in hist and start_period is None:
                prev_val = line_items[metric].get(p, prev_val)
                continue
            new_val = round(prev_val * (1 + rate), 2)
            line_items[metric][p] = new_val
            prev_val = new_val

        state["line_items"] = line_items
        return self.recalculate_derived(state)

    def apply_fixed_increase(
        self,
        state: dict,
        metric: str,
        increase: float,
        start_period: Optional[str] = None,
    ) -> dict:
        """Add a fixed amount each period from start_period."""
        state = copy.deepcopy(state)
        line_items = state["line_items"]
        time_cfg = state["time_config"]
        all_periods = time_cfg.get("all_periods", [])
        hist = time_cfg.get("historical_periods", [])
        forecast = time_cfg.get("forecast_periods", [])

        if metric not in line_items:
            line_items[metric] = {}

        effective_start = start_period or (forecast[0] if forecast else None)
        if not effective_start:
            return state

        start_idx = _period_index(effective_start, all_periods)

        for p in all_periods[start_idx:]:
            current = line_items[metric].get(p, 0)
            line_items[metric][p] = round(current + increase, 2)

        state["line_items"] = line_items
        return self.recalculate_derived(state)

    def set_margin(self, state: dict, metric: str, margin: float) -> dict:
        """
        Set a cost line as a fixed margin of revenue.
        e.g. set_margin("cogs", 0.35) => COGS = 35% of Revenue.
        """
        state = copy.deepcopy(state)
        line_items = state["line_items"]
        time_cfg = state["time_config"]

        revenues = line_items.get("revenue", {})
        if not revenues:
            logger.warning("No revenue data to compute margin from")
            return state

        if metric not in line_items:
            line_items[metric] = {}

        for p, rev in revenues.items():
            if rev is not None:
                line_items[metric][p] = round(rev * margin, 2)

        state["line_items"] = line_items
        return self.recalculate_derived(state)

    def set_headcount(
        self,
        state: dict,
        headcount: int,
        avg_salary: float,
        growth_rate: float = 0.0,
        department: Optional[str] = None,
    ) -> dict:
        """Build a headcount-driven staff cost model."""
        state = copy.deepcopy(state)
        line_items = state["line_items"]
        time_cfg = state["time_config"]
        all_periods = time_cfg.get("all_periods", [])
        forecast = time_cfg.get("forecast_periods", [])
        hist = time_cfg.get("historical_periods", [])

        staff_key = f"staff_cost_{department}" if department else "staff_cost"
        hc_key = f"headcount_{department}" if department else "headcount"

        if staff_key not in line_items:
            line_items[staff_key] = {}
        if hc_key not in line_items:
            line_items[hc_key] = {}

        cur_hc = headcount
        cur_salary = avg_salary

        for p in all_periods:
            if p in hist:
                # Don't overwrite historical data if present
                if p not in line_items[hc_key]:
                    line_items[hc_key][p] = cur_hc
                if p not in line_items[staff_key]:
                    line_items[staff_key][p] = round(cur_hc * cur_salary, 2)
            else:
                cur_hc = int(cur_hc * (1 + growth_rate)) if growth_rate > 0 else cur_hc
                cur_salary = round(cur_salary * (1 + state["assumptions"].get("staff_cost_increase", 0.05)), 2)
                line_items[hc_key][p] = cur_hc
                line_items[staff_key][p] = round(cur_hc * cur_salary, 2)

        state["line_items"] = line_items
        return self.recalculate_derived(state)

    def build_cashflow(
        self,
        state: dict,
        period_type: str = "monthly",
        periods: int = 36,
    ) -> dict:
        """
        Build a full cashflow statement. Derives operating CF from EBITDA,
        capex from assumption, and net CF as the sum.
        """
        state = copy.deepcopy(state)
        time_cfg = state["time_config"]
        line_items = state["line_items"]
        assumptions = state["assumptions"]

        # Update time config if switching period type
        hist = time_cfg.get("historical_periods", [])
        forecast = self._compute_forecast_periods(hist, period_type, periods)
        all_periods = hist + forecast
        time_cfg.update({
            "period_type": period_type,
            "forecast_periods": forecast,
            "all_periods": all_periods,
            "forecast_start": forecast[0] if forecast else None,
        })

        revenues = line_items.get("revenue", {})
        ebitdas = line_items.get("ebitda", {})
        capex_pct = assumptions.get("capex_pct_revenue", 0.03)

        for p in forecast:
            rev = revenues.get(p, 0) or 0
            ebitda = ebitdas.get(p, 0) or 0

            # Operating CF ≈ EBITDA (simplified; no working capital delta)
            if "operating_cashflow" not in line_items:
                line_items["operating_cashflow"] = {}
            line_items["operating_cashflow"][p] = round(ebitda * 0.9, 2)  # 10% WC drag

            if "capex" not in line_items:
                line_items["capex"] = {}
            line_items["capex"][p] = round(-rev * capex_pct, 2)

            if "financing_cashflow" not in line_items:
                line_items["financing_cashflow"] = {}
            line_items["financing_cashflow"].setdefault(p, 0.0)

            if "investing_cashflow" not in line_items:
                line_items["investing_cashflow"] = {}
            line_items["investing_cashflow"][p] = line_items["capex"][p]

        state["time_config"] = time_cfg
        state["line_items"] = line_items
        return self.recalculate_derived(state)

    # ------------------------------------------------------------------ #
    # Scenario management
    # ------------------------------------------------------------------ #

    def create_scenario(self, base_state: dict, scenario_name: str) -> dict:
        """Clone a base scenario into a new named scenario."""
        new_state = copy.deepcopy(base_state)
        new_state["scenario"] = scenario_name
        return new_state

    def modify_scenario(
        self,
        state: dict,
        modifications: list[dict],
    ) -> dict:
        """
        Apply a list of modifications to a scenario state.
        Each modification: {"operation": "...", "params": {...}}
        """
        for mod in modifications:
            op = mod.get("operation")
            params = mod.get("params", {})
            state = self.apply_operation(state, ModelOperation(operation=op, params=params))
        return state

    def apply_operation(self, state: dict, op: ModelOperation) -> dict:
        """Dispatch a ModelOperation to the correct method."""
        ops = {
            "apply_cagr": lambda s, p: self.apply_cagr(s, **p),
            "apply_growth_rate": lambda s, p: self.apply_growth_rate(s, **p),
            "apply_fixed_increase": lambda s, p: self.apply_fixed_increase(s, **p),
            "set_margin": lambda s, p: self.set_margin(s, **p),
            "set_headcount": lambda s, p: self.set_headcount(s, **p),
            "build_cashflow": lambda s, p: self.build_cashflow(s, **p),
            "set_assumption": lambda s, p: self._set_assumption(s, **p),
        }
        fn = ops.get(op.operation)
        if fn:
            return fn(state, op.params)
        logger.warning(f"Unknown operation: {op.operation}")
        return state

    def _set_assumption(self, state: dict, key: str, value: Any) -> dict:
        state = copy.deepcopy(state)
        state["assumptions"][key] = value
        return self.recalculate_derived(state)

    # ------------------------------------------------------------------ #
    # Derived metric recalculation
    # ------------------------------------------------------------------ #

    def recalculate_derived(self, state: dict) -> dict:
        """Recompute all formula-based line items."""
        line_items = state["line_items"]
        all_periods = state["time_config"].get("all_periods", [])
        formulas = state.get("formulas", {})

        for derived, formula in formulas.items():
            if derived not in line_items:
                line_items[derived] = {}

            for p in all_periods:
                try:
                    val = self._eval_formula(formula, line_items, p)
                    if val is not None:
                        line_items[derived][p] = round(val, 2)
                except Exception:
                    pass

        state["line_items"] = line_items
        return state

    def _eval_formula(
        self, formula: str, line_items: dict, period: str
    ) -> Optional[float]:
        """
        Safely evaluate a simple formula like "revenue - cogs" or "gross_profit / revenue * 100".
        """
        import re

        tokens = re.split(r"([\+\-\*/\(\)])", formula)
        expr_parts = []
        for token in tokens:
            token = token.strip()
            if not token:
                continue
            if token in {"+", "-", "*", "/", "(", ")"}:
                expr_parts.append(token)
            elif re.match(r"^\d+\.?\d*$", token):
                expr_parts.append(token)
            else:
                val = line_items.get(token, {}).get(period)
                if val is None:
                    return None
                expr_parts.append(str(val))

        expr = " ".join(expr_parts)
        try:
            result = eval(expr, {"__builtins__": {}}, {})  # restricted eval
            if isinstance(result, (int, float)) and not math.isnan(result) and not math.isinf(result):
                return float(result)
        except ZeroDivisionError:
            return None
        except Exception:
            return None
        return None

    # ------------------------------------------------------------------ #
    # Sensitivity analysis
    # ------------------------------------------------------------------ #

    def sensitivity_analysis(
        self,
        state: dict,
        variable: str,
        output_metric: str,
        range_pct: float = 0.2,
        steps: int = 5,
    ) -> list[dict]:
        """
        Vary `variable` assumption from -range_pct to +range_pct and
        return the effect on `output_metric`.
        """
        base_val = state["assumptions"].get(variable)
        if base_val is None:
            return []

        results = []
        step_size = (range_pct * 2) / (steps - 1) if steps > 1 else 0

        for i in range(steps):
            multiplier = 1 - range_pct + i * step_size
            test_state = copy.deepcopy(state)
            test_state["assumptions"][variable] = round(base_val * multiplier, 6)
            test_state = self.recalculate_derived(test_state)

            forecast = test_state["time_config"].get("forecast_periods", [])
            output_vals = {
                p: test_state["line_items"].get(output_metric, {}).get(p)
                for p in forecast
            }

            results.append({
                "assumption": variable,
                "assumption_value": test_state["assumptions"][variable],
                "change_pct": round((multiplier - 1) * 100, 1),
                "output_metric": output_metric,
                "output_values": output_vals,
            })

        return results

    # ------------------------------------------------------------------ #
    # Outputs
    # ------------------------------------------------------------------ #

    def get_summary_table(self, state: dict) -> dict:
        """
        Return a structured summary for the frontend table component.
        {
          "periods": [...],
          "sections": [
            { "name": "Income Statement", "rows": [{"label": "Revenue", "values": {...}}] }
          ]
        }
        """
        all_periods = state["time_config"].get("all_periods", [])
        line_items = state["line_items"]

        SECTIONS = [
            ("Income Statement", [
                ("revenue", "Revenue"),
                ("cogs", "Cost of Goods Sold"),
                ("gross_profit", "Gross Profit"),
                ("gross_margin_pct", "Gross Margin %"),
                ("sales_and_marketing", "Sales & Marketing"),
                ("general_and_admin", "G&A"),
                ("research_and_development", "R&D"),
                ("operating_expenses", "Operating Expenses"),
                ("ebitda", "EBITDA"),
                ("ebitda_margin_pct", "EBITDA Margin %"),
                ("depreciation_amortization", "D&A"),
                ("ebit", "EBIT"),
                ("interest_expense", "Interest Expense"),
                ("tax", "Tax"),
                ("net_income", "Net Income"),
                ("net_margin_pct", "Net Margin %"),
            ]),
            ("Cash Flow", [
                ("operating_cashflow", "Operating Cash Flow"),
                ("capex", "Capex"),
                ("investing_cashflow", "Investing Cash Flow"),
                ("financing_cashflow", "Financing Cash Flow"),
                ("free_cash_flow", "Free Cash Flow"),
            ]),
            ("Balance Sheet", [
                ("cash", "Cash & Equivalents"),
                ("accounts_receivable", "Accounts Receivable"),
                ("total_current_assets", "Total Current Assets"),
                ("total_assets", "Total Assets"),
                ("accounts_payable", "Accounts Payable"),
                ("total_current_liabilities", "Total Current Liabilities"),
                ("total_liabilities", "Total Liabilities"),
                ("equity", "Equity"),
            ]),
            ("KPIs", [
                ("arr", "ARR"),
                ("mrr", "MRR"),
                ("headcount", "Headcount"),
                ("churn_rate", "Churn Rate"),
                ("customers", "Customers"),
                ("average_revenue_per_user", "ARPU"),
            ]),
        ]

        sections = []
        for section_name, items in SECTIONS:
            rows = []
            for key, label in items:
                if key in line_items and line_items[key]:
                    rows.append({
                        "key": key,
                        "label": label,
                        "values": {p: line_items[key].get(p) for p in all_periods},
                        "is_percentage": key.endswith("_pct") or key.endswith("_rate"),
                    })
            if rows:
                sections.append({"name": section_name, "rows": rows})

        return {
            "periods": all_periods,
            "forecast_start": state["time_config"].get("forecast_start"),
            "sections": sections,
            "assumptions": state.get("assumptions", {}),
            "scenario": state.get("scenario", "base"),
        }

    def get_chart_data(self, state: dict, metrics: list[str]) -> list[dict]:
        """
        Return chart-ready data for the specified metrics.
        [{period, metric1, metric2, ...}]
        """
        all_periods = state["time_config"].get("all_periods", [])
        line_items = state["line_items"]

        rows = []
        for p in all_periods:
            row = {"period": p}
            for m in metrics:
                row[m] = line_items.get(m, {}).get(p)
            rows.append(row)
        return rows
