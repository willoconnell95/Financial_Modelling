"""Tests for the modelling engine and NLP command parser."""
import pytest
from app.services.nlp_command_parser import parse_command
from app.services.modelling_engine import (
    FinancialModel,
    generate_periods,
    execute_command,
    build_model_from_records,
)


# ── NLP command parser tests ─────────────────────────────────────────────────

class TestParseCommand:
    def test_cagr_command(self):
        cmd = parse_command("Model revenue using a 3-year CAGR from historicals")
        assert cmd.intent == "apply_cagr"
        assert cmd.periods == 3

    def test_growth_rate_command(self):
        cmd = parse_command("Apply a 15% growth to revenue over 3 years")
        assert cmd.intent == "apply_growth"
        assert pytest.approx(cmd.value, 0.001) == 0.15

    def test_staff_increase_command(self):
        cmd = parse_command("Apply a 15% staff cost increase from FY25")
        assert cmd.intent == "apply_staff_increase"
        assert pytest.approx(cmd.value, 0.001) == 0.15

    def test_scenario_command(self):
        cmd = parse_command("Add a scenario where churn increases by 20%")
        # Could match add_scenario or adjust_churn depending on order
        assert cmd.intent in ("add_scenario", "adjust_churn")

    def test_cashflow_forecast(self):
        cmd = parse_command("Build a 36-month cashflow forecast")
        assert cmd.intent == "build_cashflow_forecast"
        assert cmd.periods == 36

    def test_sensitivity_command(self):
        cmd = parse_command("Run sensitivity analysis on revenue")
        assert cmd.intent == "sensitivity_analysis"

    def test_churn_adjustment(self):
        cmd = parse_command("Increase churn rate by 20%")
        assert cmd.intent == "adjust_churn"
        assert pytest.approx(cmd.value, 0.001) == 0.20

    def test_set_assumption(self):
        cmd = parse_command("Set tax rate to 25%")
        assert cmd.intent == "set_assumption"

    def test_unknown_falls_back(self):
        cmd = parse_command("Do something completely unknown xyz")
        assert cmd.intent != "apply_cagr"  # shouldn't match as cagr
        assert cmd.confidence <= 0.5  # low confidence for fallback


# ── Modelling engine tests ───────────────────────────────────────────────────

class TestGeneratePeriods:
    def test_annual_periods(self):
        periods = generate_periods("FY2022", "FY2025", "annual")
        assert "FY2022" in periods
        assert "FY2025" in periods
        assert len(periods) == 4

    def test_fallback_on_bad_input(self):
        periods = generate_periods("bad", "input", "annual")
        assert len(periods) == 5  # default fallback


class TestFinancialModel:
    def setup_method(self):
        self.periods = ["FY2022", "FY2023", "FY2024"]
        self.model = FinancialModel(periods=self.periods)

    def test_set_and_get_series(self):
        series = {"FY2022": 1000.0, "FY2023": 1100.0, "FY2024": 1210.0}
        self.model.set_series("revenue", series)
        result = self.model.get_series("revenue")
        assert result["FY2022"] == 1000.0

    def test_compute_gross_profit(self):
        self.model.set_series("revenue", {"FY2022": 1000, "FY2023": 1100, "FY2024": 1200})
        self.model.set_series("cogs", {"FY2022": 600, "FY2023": 650, "FY2024": 700})
        gp = self.model.compute_gross_profit()
        assert gp["FY2022"] == 400
        assert gp["FY2023"] == 450

    def test_compute_ebitda(self):
        self.model.set_series("gross_profit", {"FY2022": 400, "FY2023": 450, "FY2024": 500})
        self.model.set_series("opex", {"FY2022": 200, "FY2023": 220, "FY2024": 240})
        ebitda = self.model.compute_ebitda()
        assert ebitda["FY2022"] == 200
        assert ebitda["FY2023"] == 230

    def test_compute_net_income(self):
        self.model.set_series("ebitda", {"FY2022": 200, "FY2023": 230, "FY2024": 260})
        self.model.set_assumption("tax_rate", 0.20)
        ni = self.model.compute_net_income()
        assert pytest.approx(ni["FY2022"], 0.01) == 160.0  # 200 * (1 - 0.20)

    def test_revenue_cagr_projection(self):
        historical = {"FY2020": 100, "FY2021": 110, "FY2022": 121}
        projected = self.model.model_revenue_cagr(historical, ["FY2023", "FY2024"], cagr_years=3)
        assert "FY2023" in projected
        # CAGR from 100 → 121 over 2 years ≈ 10%
        assert projected["FY2023"] is not None
        assert projected["FY2023"] > 121  # should grow

    def test_apply_growth_to_series(self):
        self.model.set_series("revenue", {"FY2022": 1000, "FY2023": None, "FY2024": None})
        result = self.model.apply_growth_to_series("revenue", 0.10)
        assert result["FY2023"] == pytest.approx(1100.0, 0.01)
        assert result["FY2024"] == pytest.approx(1210.0, 0.01)

    def test_sensitivity_analysis(self):
        self.model.set_series("revenue", {"FY2022": 1000, "FY2023": 1100, "FY2024": 1200})
        self.model.set_series("cogs", {"FY2022": 600, "FY2023": 660, "FY2024": 720})
        self.model.compute_gross_profit()
        self.model.compute_ebitda()
        self.model.compute_net_income()
        results = self.model.sensitivity_analysis("revenue", "net_income", 0.20, 5)
        assert len(results) == 5
        # Higher revenue should lead to higher net income
        outputs = [r["output_value"] for r in results]
        assert outputs[-1] >= outputs[0]

    def test_scenario_overrides(self):
        self.model.set_series("revenue", {"FY2022": 1000, "FY2023": 1100, "FY2024": 1200})
        overrides = {"revenue": {"FY2022": 800, "FY2023": 900, "FY2024": 1000}}
        new_model = self.model.apply_scenario_overrides(overrides)
        assert new_model.get_value("revenue", "FY2022") == 800
        # Original unchanged
        assert self.model.get_value("revenue", "FY2022") == 1000

    def test_to_output(self):
        self.model.set_series("revenue", {"FY2022": 1000, "FY2023": 1100, "FY2024": 1200})
        output = self.model.to_output()
        assert "periods" in output
        assert "income_statement" in output
        assert "revenue" in output["income_statement"]


class TestBuildModelFromRecords:
    def test_builds_from_records(self):
        records = [
            {"category": "revenue", "period_label": "FY2022", "value": 1000, "line_item": "Revenue"},
            {"category": "cogs", "period_label": "FY2022", "value": 600, "line_item": "COGS"},
        ]
        periods = ["FY2022", "FY2023"]
        model = build_model_from_records(records, periods)
        assert model.get_value("revenue", "FY2022") == 1000
        assert model.get_value("cogs", "FY2022") == 600
        assert model.get_value("gross_profit", "FY2022") == 400


class TestExecuteCommand:
    def setup_method(self):
        self.periods = ["FY2022", "FY2023", "FY2024"]
        self.model = FinancialModel(periods=self.periods)
        self.model.set_series("revenue", {"FY2022": 1000, "FY2023": 1100, "FY2024": 1200})
        self.model.set_series("cogs", {"FY2022": 600, "FY2023": 660, "FY2024": 720})
        self.model.compute_gross_profit()
        self.model.compute_ebitda()
        self.model.compute_net_income()
        self.records = [
            {"category": "revenue", "period_label": "FY2022", "value": 1000, "line_item": "Revenue"},
        ]

    def test_apply_growth_command(self):
        from app.services.nlp_command_parser import parse_command
        cmd = parse_command("Apply a 10% growth to revenue")
        updated, ops = execute_command(cmd, self.model, self.records)
        assert len(ops) > 0

    def test_build_cashflow_command(self):
        from app.services.nlp_command_parser import parse_command
        self.model.set_series("net_income", {"FY2022": 160, "FY2023": 184, "FY2024": 208})
        cmd = parse_command("Build a 36-month cashflow forecast")
        updated, ops = execute_command(cmd, self.model, self.records)
        assert len(ops) > 0
