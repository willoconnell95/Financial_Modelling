"""
Core financial modelling engine.
Operates on ModelState + ModelVariable records to produce P&L, Balance Sheet,
Cashflow, and KPI outputs. Handles scenario analysis and sensitivity.
"""
import logging
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from typing import Optional, Any
import numpy as np

from app.services.nlp_command_parser import ParsedCommand
from app.utils.financial_utils import calculate_cagr, apply_growth_rate

logger = logging.getLogger(__name__)


# ─── Period generation ─────────────────────────────────────────────────────────

def generate_periods(
    start: str,
    end: str,
    frequency: str = "annual",
) -> list[str]:
    """
    Generate a list of period labels from start to end.
    start/end formats: 'FY2023', '2023', 'Jan-2023', 'Q1-2024'
    """
    try:
        start_dt = _parse_period_start(start)
        end_dt = _parse_period_start(end)
    except Exception:
        # Fallback: generate 5 annual periods from current year
        year = datetime.now().year
        return [f"FY{year + i}" for i in range(5)]

    periods = []
    current = start_dt
    delta_map = {
        "monthly": relativedelta(months=1),
        "quarterly": relativedelta(months=3),
        "annual": relativedelta(years=1),
    }
    delta = delta_map.get(frequency, relativedelta(years=1))

    while current <= end_dt:
        if frequency == "monthly":
            periods.append(current.strftime("%b-%Y"))
        elif frequency == "quarterly":
            q = (current.month - 1) // 3 + 1
            periods.append(f"Q{q} {current.year}")
        else:
            periods.append(f"FY{current.year}")
        current += delta

    return periods


def _parse_period_start(label: str) -> datetime:
    import re
    # FY2023 or FY23
    m = re.match(r"FY(\d{2,4})", label, re.IGNORECASE)
    if m:
        year = int(m.group(1))
        if year < 100:
            year += 2000
        return datetime(year, 1, 1)
    # Plain year
    m = re.match(r"^(\d{4})$", label)
    if m:
        return datetime(int(m.group(1)), 1, 1)
    # Attempt dateutil parse
    from dateutil import parser as dp
    return dp.parse(label)


# ─── Model computation ─────────────────────────────────────────────────────────

class FinancialModel:
    """
    In-memory financial model.
    variables: {key: {period: value}}
    assumptions: {key: scalar value or dict}
    """

    def __init__(self, periods: list[str], currency: str = "USD", unit_scale: str = "thousands"):
        self.periods = periods
        self.currency = currency
        self.unit_scale = unit_scale
        # Main data store: variable_key -> {period -> float}
        self.data: dict[str, dict[str, Optional[float]]] = {}
        self.assumptions: dict[str, Any] = {}
        self.metadata: dict[str, Any] = {}

    # ── Setters ────────────────────────────────────────────────────────────────

    def set_series(self, key: str, values: dict[str, Optional[float]]):
        self.data[key] = values

    def set_assumption(self, key: str, value: Any):
        self.assumptions[key] = value

    def set_value(self, key: str, period: str, value: Optional[float]):
        if key not in self.data:
            self.data[key] = {}
        self.data[key][period] = value

    def get_series(self, key: str) -> dict[str, Optional[float]]:
        return self.data.get(key, {p: None for p in self.periods})

    def get_value(self, key: str, period: str) -> Optional[float]:
        return self.data.get(key, {}).get(period)

    # ── Revenue modelling ───────────────────────────────────────────────────────

    def model_revenue_cagr(
        self,
        historical_values: dict[str, float],
        forecast_periods: list[str],
        cagr_years: int = 3,
        override_cagr: Optional[float] = None,
    ) -> dict[str, Optional[float]]:
        """Apply CAGR-based revenue projection from historicals."""
        hist_vals = [v for v in historical_values.values() if v is not None and v > 0]
        if not hist_vals:
            return {p: None for p in forecast_periods}

        if override_cagr is not None:
            cagr = override_cagr
        elif len(hist_vals) >= 2:
            cagr = calculate_cagr(hist_vals[0], hist_vals[-1], len(hist_vals) - 1)
        else:
            cagr = 0.10  # default 10%

        cagr = cagr or 0.10
        base = hist_vals[-1]
        projected = apply_growth_rate(base, cagr, len(forecast_periods))

        result = {p: round(v, 2) for p, v in zip(forecast_periods, projected)}
        self.assumptions["revenue_cagr"] = round(cagr * 100, 2)
        return result

    def apply_growth_to_series(
        self,
        key: str,
        growth_rate: float,
        from_period: Optional[str] = None,
    ) -> dict[str, Optional[float]]:
        """Apply a fixed growth rate to a series starting from a given period."""
        series = self.get_series(key)
        new_series = dict(series)

        start_applying = from_period is None
        prev_value = None

        for period in self.periods:
            if from_period and period == from_period:
                start_applying = True

            if start_applying and prev_value is not None:
                new_series[period] = round(prev_value * (1 + growth_rate), 4)

            val = new_series.get(period)
            if val is not None:
                prev_value = val

        self.data[key] = new_series
        return new_series

    # ── Cost modelling ──────────────────────────────────────────────────────────

    def compute_gross_profit(self) -> dict[str, Optional[float]]:
        gp = {}
        for p in self.periods:
            rev = self.get_value("revenue", p)
            cogs = self.get_value("cogs", p)
            if rev is not None and cogs is not None:
                gp[p] = round(rev - cogs, 4)
            elif rev is not None:
                gp[p] = rev
            else:
                gp[p] = None
        self.data["gross_profit"] = gp
        return gp

    def compute_ebitda(self) -> dict[str, Optional[float]]:
        ebitda = {}
        for p in self.periods:
            gp = self.get_value("gross_profit", p)
            opex = self.get_value("opex", p)
            if gp is not None:
                ebitda[p] = round(gp - (opex or 0), 4)
            else:
                ebitda[p] = None
        self.data["ebitda"] = ebitda
        return ebitda

    def compute_net_income(self) -> dict[str, Optional[float]]:
        ni = {}
        for p in self.periods:
            ebitda = self.get_value("ebitda", p)
            da = self.get_value("depreciation_amortization", p) or 0
            interest = self.get_value("interest", p) or 0
            tax_rate = self.assumptions.get("tax_rate", 0.20)

            if ebitda is not None:
                ebit = ebitda - da
                pbt = ebit - interest
                ni[p] = round(pbt * (1 - tax_rate), 4)
            else:
                ni[p] = None
        self.data["net_income"] = ni
        return ni

    # ── Cashflow modelling ─────────────────────────────────────────────────────

    def build_cashflow_forecast(self) -> dict[str, dict]:
        cf = {}
        for p in self.periods:
            ni = self.get_value("net_income", p)
            da = self.get_value("depreciation_amortization", p) or 0
            capex = self.get_value("capex", p) or 0
            wc_change = self.get_value("working_capital_change", p) or 0

            operating_cf = (ni or 0) + da - wc_change
            investing_cf = -capex
            financing_cf = self.get_value("financing_cf", p) or 0
            net_cf = operating_cf + investing_cf + financing_cf

            cf[p] = {
                "operating_cf": round(operating_cf, 4),
                "investing_cf": round(investing_cf, 4),
                "financing_cf": round(financing_cf, 4),
                "net_cf": round(net_cf, 4),
            }
            self.set_value("operating_cf", p, cf[p]["operating_cf"])
            self.set_value("net_cf", p, net_cf)

        return cf

    # ── Scenario management ────────────────────────────────────────────────────

    def apply_scenario_overrides(self, overrides: dict) -> "FinancialModel":
        """Return a new model with overrides applied."""
        import copy
        new_model = copy.deepcopy(self)
        for key, series_or_scalar in overrides.items():
            if isinstance(series_or_scalar, dict):
                for period, val in series_or_scalar.items():
                    new_model.set_value(key, period, val)
            else:
                new_model.assumptions[key] = series_or_scalar
        return new_model

    # ── Sensitivity analysis ───────────────────────────────────────────────────

    def sensitivity_analysis(
        self,
        variable_key: str,
        output_metric: str,
        range_pct: float = 0.20,
        steps: int = 5,
    ) -> list[dict]:
        import copy

        base_value = self.assumptions.get(
            variable_key,
            self.get_value(variable_key, self.periods[-1] if self.periods else "") or 0,
        )
        if base_value == 0:
            return []

        results = []
        step_size = (2 * range_pct) / (steps - 1) if steps > 1 else 0

        for i in range(steps):
            pct_change = -range_pct + i * step_size
            new_value = base_value * (1 + pct_change)

            test_model = copy.deepcopy(self)
            if variable_key in test_model.assumptions:
                test_model.assumptions[variable_key] = new_value
            else:
                for p in test_model.periods:
                    existing = test_model.get_value(variable_key, p)
                    if existing is not None:
                        test_model.set_value(variable_key, p, existing * (1 + pct_change))

            # Recompute derived metrics
            test_model.compute_gross_profit()
            test_model.compute_ebitda()
            test_model.compute_net_income()

            output_vals = [
                v for v in test_model.get_series(output_metric).values() if v is not None
            ]
            output_value = sum(output_vals) / len(output_vals) if output_vals else 0

            results.append(
                {
                    "input_pct_change": round(pct_change * 100, 1),
                    "input_value": round(new_value, 4),
                    "output_value": round(output_value, 4),
                }
            )

        return results

    # ── Output serialisation ───────────────────────────────────────────────────

    def to_output(self) -> dict:
        """Serialise model state to a JSON-friendly dict."""
        return {
            "periods": self.periods,
            "currency": self.currency,
            "unit_scale": self.unit_scale,
            "income_statement": self._section(
                ["revenue", "cogs", "gross_profit", "opex", "ebitda", "ebit",
                 "interest", "tax", "net_income"]
            ),
            "balance_sheet": self._section(
                ["cash", "receivables", "inventory", "fixed_assets", "total_assets",
                 "payables", "debt", "equity", "total_liabilities"]
            ),
            "cashflow": self._section(
                ["operating_cf", "investing_cf", "financing_cf", "net_cf", "capex"]
            ),
            "kpis": self._section(
                ["headcount", "arr", "mrr", "churn_rate", "cac", "ltv",
                 "gross_margin_pct", "ebitda_margin_pct"]
            ),
            "assumptions": self.assumptions,
        }

    def _section(self, keys: list) -> dict:
        section = {}
        for key in keys:
            if key in self.data:
                section[key] = self.data[key]
        return section

    def compute_margins(self):
        """Derive margin percentages."""
        for p in self.periods:
            rev = self.get_value("revenue", p)
            if rev and rev != 0:
                gp = self.get_value("gross_profit", p)
                if gp is not None:
                    self.set_value("gross_margin_pct", p, round(gp / rev * 100, 2))
                ebitda = self.get_value("ebitda", p)
                if ebitda is not None:
                    self.set_value("ebitda_margin_pct", p, round(ebitda / rev * 100, 2))


# ─── Command executor ──────────────────────────────────────────────────────────

def execute_command(
    cmd: ParsedCommand,
    model: FinancialModel,
    financial_records: list[dict],
) -> tuple[FinancialModel, list[str]]:
    """
    Execute a parsed command against a FinancialModel.
    Returns the updated model and a list of operation descriptions.
    """
    operations: list[str] = []

    if cmd.intent == "apply_cagr":
        target = cmd.target or "revenue"
        historical = {
            rec["period_label"]: rec["value"]
            for rec in financial_records
            if rec.get("category") == target and rec.get("value") is not None
        }
        forecast_periods = [p for p in model.periods if p not in historical]
        if not forecast_periods:
            forecast_periods = model.periods

        projected = model.model_revenue_cagr(
            historical,
            forecast_periods,
            cagr_years=cmd.periods or 3,
        )
        for p, v in projected.items():
            model.set_value(target, p, v)
        # Keep historical
        for p, v in historical.items():
            model.set_value(target, p, v)

        model.compute_gross_profit()
        model.compute_ebitda()
        model.compute_net_income()
        model.compute_margins()
        operations.append(f"Applied CAGR model to {target}")

    elif cmd.intent == "apply_growth":
        target_key = _map_target_to_key(cmd.target or "revenue")
        rate = cmd.value or 0.10
        model.apply_growth_to_series(target_key, rate)
        model.compute_gross_profit()
        model.compute_ebitda()
        model.compute_net_income()
        model.compute_margins()
        operations.append(f"Applied {rate*100:.1f}% growth to {target_key}")

    elif cmd.intent == "apply_staff_increase":
        rate = cmd.value or 0.15
        year_label = cmd.extra.get("year")
        model.apply_growth_to_series("staff_costs", rate, from_period=year_label)
        # Update opex if staff_costs is component
        for p in model.periods:
            sc = model.get_value("staff_costs", p) or 0
            other = model.get_value("other_opex", p) or 0
            model.set_value("opex", p, sc + other)
        model.compute_ebitda()
        model.compute_net_income()
        model.compute_margins()
        operations.append(f"Applied {rate*100:.1f}% staff cost increase")

    elif cmd.intent == "adjust_churn":
        rate = cmd.value or 0.05
        direction = cmd.extra.get("direction", "increase")
        multiplier = 1 + rate if direction == "increase" else 1 - rate
        for p in model.periods:
            existing = model.get_value("churn_rate", p)
            if existing is not None:
                model.set_value("churn_rate", p, round(existing * multiplier, 4))
        operations.append(f"{direction.capitalize()} churn rate by {rate*100:.1f}%")

    elif cmd.intent == "apply_cost_growth":
        rate = cmd.value or 0.05
        for cost_key in ["cogs", "opex", "staff_costs"]:
            series = model.get_series(cost_key)
            if any(v is not None for v in series.values()):
                model.apply_growth_to_series(cost_key, rate)
        model.compute_gross_profit()
        model.compute_ebitda()
        model.compute_net_income()
        model.compute_margins()
        operations.append(f"Applied {rate*100:.1f}% cost growth")

    elif cmd.intent == "build_cashflow_forecast":
        model.compute_gross_profit()
        model.compute_ebitda()
        model.compute_net_income()
        model.build_cashflow_forecast()
        model.compute_margins()
        operations.append(f"Built {cmd.periods or len(model.periods)}-period cashflow forecast")

    elif cmd.intent == "set_assumption":
        if cmd.target and cmd.value is not None:
            model.set_assumption(cmd.target, cmd.value)
            operations.append(f"Set assumption: {cmd.target} = {cmd.value}")

    elif cmd.intent in ("model_revenue", "display"):
        # Just recompute outputs
        model.compute_gross_profit()
        model.compute_ebitda()
        model.compute_net_income()
        model.compute_margins()
        operations.append("Recomputed model output")

    return model, operations


def _map_target_to_key(target: str) -> str:
    mapping = {
        "revenue": "revenue",
        "sales": "revenue",
        "cogs": "cogs",
        "cost of goods": "cogs",
        "opex": "opex",
        "operating expenses": "opex",
        "staff": "staff_costs",
        "staff costs": "staff_costs",
        "headcount": "headcount",
        "capex": "capex",
        "churn": "churn_rate",
        "arr": "arr",
        "mrr": "mrr",
    }
    return mapping.get(target.lower().strip(), target.lower().replace(" ", "_"))


def build_model_from_records(
    records: list[dict],
    periods: list[str],
    currency: str = "USD",
    unit_scale: str = "thousands",
) -> FinancialModel:
    """Seed a FinancialModel from extracted FinancialRecord dicts."""
    model = FinancialModel(periods=periods, currency=currency, unit_scale=unit_scale)

    for rec in records:
        cat = rec.get("category", "other")
        period = rec.get("period_label")
        value = rec.get("value")
        if period and value is not None:
            model.set_value(cat, period, value)

    # Set defaults
    model.set_assumption("tax_rate", 0.20)
    model.set_assumption("discount_rate", 0.10)

    # Compute derived lines
    model.compute_gross_profit()
    model.compute_ebitda()
    model.compute_net_income()
    model.compute_margins()

    return model
