"""Unit tests for the modelling engine and NLP command parser."""
import pytest
from app.services.modelling_engine import ModellingEngine
from app.services.nlp_command_parser import NLPCommandParser


@pytest.fixture
def engine():
    return ModellingEngine()


@pytest.fixture
def base_state(engine):
    """Minimal base state for testing."""
    line_items = [
        {"normalized_name": "revenue", "period": "FY2022", "value": 1_000_000, "category": "income_statement"},
        {"normalized_name": "revenue", "period": "FY2023", "value": 1_200_000, "category": "income_statement"},
        {"normalized_name": "cogs", "period": "FY2022", "value": 400_000, "category": "income_statement"},
        {"normalized_name": "cogs", "period": "FY2023", "value": 480_000, "category": "income_statement"},
        {"normalized_name": "operating_expenses", "period": "FY2022", "value": 300_000, "category": "income_statement"},
        {"normalized_name": "operating_expenses", "period": "FY2023", "value": 360_000, "category": "income_statement"},
    ]
    state = engine.build_from_extracted(line_items, period_type="annual", forecast_periods=3)
    return state


# ── ModellingEngine tests ─────────────────────────────────────────────────────

class TestModellingEngine:

    def test_build_from_extracted(self, engine, base_state):
        assert "revenue" in base_state["line_items"]
        assert "FY2022" in base_state["line_items"]["revenue"]
        assert base_state["line_items"]["revenue"]["FY2022"] == 1_000_000

    def test_forecast_periods_generated(self, engine, base_state):
        forecast = base_state["time_config"]["forecast_periods"]
        assert len(forecast) == 3
        assert forecast[0] == "FY2024"
        assert forecast[2] == "FY2026"

    def test_gross_profit_derived(self, engine, base_state):
        # gross_profit = revenue - cogs should be auto-calculated
        gp = base_state["line_items"].get("gross_profit", {})
        assert gp.get("FY2023") == pytest.approx(720_000, rel=0.01)

    def test_apply_cagr(self, engine, base_state):
        state = engine.apply_cagr(base_state, metric="revenue", cagr_rate=0.20)
        fc = state["line_items"]["revenue"]
        # FY2024 = FY2023 * 1.20
        assert fc.get("FY2024") == pytest.approx(1_440_000, rel=0.01)
        # FY2025 = FY2023 * 1.20^2
        assert fc.get("FY2025") == pytest.approx(1_728_000, rel=0.01)

    def test_apply_growth_rate(self, engine, base_state):
        state = engine.apply_growth_rate(base_state, metric="revenue", rate=0.10)
        rev = state["line_items"]["revenue"]
        # Should grow 10% from last historical (FY2023 = 1.2M)
        assert rev.get("FY2024") == pytest.approx(1_320_000, rel=0.01)

    def test_set_margin(self, engine, base_state):
        # First apply CAGR to revenue so forecast periods have values
        state = engine.apply_cagr(base_state, "revenue", 0.15)
        state = engine.set_margin(state, metric="cogs", margin=0.35)
        rev_fy24 = state["line_items"]["revenue"]["FY2024"]
        cogs_fy24 = state["line_items"]["cogs"]["FY2024"]
        assert cogs_fy24 == pytest.approx(rev_fy24 * 0.35, rel=0.01)

    def test_scenario_creation(self, engine, base_state):
        upside = engine.create_scenario(base_state, "upside")
        assert upside["scenario"] == "upside"
        # Must be independent (deep copy)
        upside["line_items"]["revenue"]["FY2022"] = 999
        assert base_state["line_items"]["revenue"]["FY2022"] == 1_000_000

    def test_sensitivity_analysis(self, engine, base_state):
        # Ensure revenue has forecast values
        state = engine.apply_cagr(base_state, "revenue", 0.15)
        results = engine.sensitivity_analysis(
            state, variable="revenue_growth_rate",
            output_metric="ebitda", range_pct=0.1, steps=3
        )
        assert len(results) == 3
        assert results[0]["change_pct"] < 0
        assert results[-1]["change_pct"] > 0

    def test_build_cashflow(self, engine, base_state):
        state = engine.apply_cagr(base_state, "revenue", 0.15)
        state = engine.build_cashflow(state, period_type="monthly", periods=12)
        assert state["time_config"]["period_type"] == "monthly"
        assert len(state["time_config"]["forecast_periods"]) == 12

    def test_get_summary_table(self, engine, base_state):
        summary = engine.get_summary_table(base_state)
        assert "periods" in summary
        assert "sections" in summary
        sections_names = [s["name"] for s in summary["sections"]]
        assert "Income Statement" in sections_names

    def test_recalculate_derived_ebitda(self, engine, base_state):
        state = engine.apply_cagr(base_state, "revenue", 0.15)
        state["line_items"]["operating_expenses"]["FY2024"] = 450_000
        state = engine.recalculate_derived(state)
        gp = state["line_items"]["gross_profit"]["FY2024"]
        opex = state["line_items"]["operating_expenses"]["FY2024"]
        ebitda = state["line_items"]["ebitda"]["FY2024"]
        assert ebitda == pytest.approx(gp - opex, rel=0.01)


# ── NLP Parser tests ───────────────────────────────────────────────────────────

class TestNLPCommandParser:
    @pytest.fixture
    def parser(self):
        return NLPCommandParser()

    def test_cagr_command(self, parser):
        cmd = parser.parse("Model revenue using a 15% CAGR")
        assert cmd.operation == "apply_cagr"
        assert cmd.params["metric"] == "revenue"
        assert abs(cmd.params["cagr_rate"] - 0.15) < 0.001

    def test_cagr_with_years(self, parser):
        cmd = parser.parse("Model revenue using a 3-year CAGR of 20%")
        assert cmd.operation == "apply_cagr"
        assert abs(cmd.params["cagr_rate"] - 0.20) < 0.001

    def test_growth_rate_command(self, parser):
        cmd = parser.parse("Grow operating expenses at 8% per year")
        assert cmd.operation == "apply_growth_rate"
        assert cmd.params["metric"] == "operating_expenses"
        assert abs(cmd.params["rate"] - 0.08) < 0.001

    def test_apply_increase(self, parser):
        cmd = parser.parse("Apply a 15% staff cost increase from FY25")
        assert cmd.operation == "apply_growth_rate"
        assert cmd.params["metric"] == "staff_cost"
        assert abs(cmd.params["rate"] - 0.15) < 0.001

    def test_reduce_command(self, parser):
        cmd = parser.parse("Reduce churn by 20%")
        assert cmd.operation == "apply_growth_rate"
        assert cmd.params["metric"] == "churn_rate"
        assert cmd.params["rate"] < 0

    def test_add_scenario(self, parser):
        cmd = parser.parse("Add a scenario where revenue grows at 25%")
        assert cmd.operation == "add_scenario"
        assert "scenario_name" in cmd.params

    def test_build_cashflow(self, parser):
        cmd = parser.parse("Build a monthly cashflow forecast for 36 months")
        assert cmd.operation == "build_cashflow"
        assert cmd.params["period_type"] == "monthly"
        assert cmd.params["periods"] == 36

    def test_set_assumption(self, parser):
        cmd = parser.parse("Set tax rate to 25%")
        assert cmd.operation == "set_assumption"
        assert "tax_rate" in cmd.params["key"]
        assert abs(cmd.params["value"] - 0.25) < 0.001

    def test_set_margin(self, parser):
        cmd = parser.parse("Set gross margin to 65%")
        assert cmd.operation == "set_margin"
        # margin for COGS = 1 - 0.65 = 0.35
        assert cmd.params["metric"] == "cogs"
        assert abs(cmd.params["margin"] - 0.35) < 0.001

    def test_sensitivity(self, parser):
        cmd = parser.parse("Run a sensitivity analysis on revenue growth vs EBITDA")
        assert cmd.operation == "sensitivity_analysis"

    def test_unknown_command(self, parser):
        cmd = parser.parse("Please make the numbers bigger somehow")
        assert cmd.operation == "unknown"
        assert cmd.confidence == 0.0

    def test_headcount_command(self, parser):
        cmd = parser.parse("Set headcount to 50 with average salary of 80000")
        assert cmd.operation == "set_headcount"
        assert cmd.params["headcount"] == 50
        assert cmd.params["avg_salary"] == 80000.0
