"""
Export service: generates Excel and CSV files from model state.
"""
from __future__ import annotations

import io
import os
import tempfile
from typing import Optional

import pandas as pd
from loguru import logger


class ExportService:

    def export_excel(self, model_summary: dict, scenarios: Optional[list[dict]] = None) -> bytes:
        """
        Generate an Excel workbook from model summary.
        Returns raw bytes.
        """
        buf = io.BytesIO()

        with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
            workbook = writer.book

            # Formats
            header_fmt = workbook.add_format({
                "bold": True, "bg_color": "#1e3a5f", "font_color": "white",
                "border": 1, "align": "center",
            })
            section_fmt = workbook.add_format({
                "bold": True, "bg_color": "#d4e6f1", "border": 1,
            })
            number_fmt = workbook.add_format({"num_format": "#,##0", "border": 1})
            pct_fmt = workbook.add_format({"num_format": "0.0%", "border": 1})
            label_fmt = workbook.add_format({"border": 1, "indent": 1})
            forecast_fmt = workbook.add_format({
                "num_format": "#,##0", "border": 1, "font_color": "#0066cc",
            })

            periods = model_summary.get("periods", [])
            forecast_start = model_summary.get("forecast_start")

            # ── Model Sheet ──────────────────────────────────────────────
            ws = workbook.add_worksheet("Financial Model")
            writer.sheets["Financial Model"] = ws

            ws.set_column(0, 0, 35)
            ws.set_column(1, len(periods) + 1, 14)

            # Header row
            ws.write(0, 0, "Line Item", header_fmt)
            for col, p in enumerate(periods, start=1):
                ws.write(0, col, p, header_fmt)

            row = 1
            for section in model_summary.get("sections", []):
                # Section header
                ws.write(row, 0, section["name"], section_fmt)
                for col in range(1, len(periods) + 1):
                    ws.write(row, col, "", section_fmt)
                row += 1

                for item in section.get("rows", []):
                    ws.write(row, 0, item["label"], label_fmt)
                    is_pct = item.get("is_percentage", False)
                    for col, p in enumerate(periods, start=1):
                        val = item["values"].get(p)
                        fmt = pct_fmt if is_pct else (forecast_fmt if forecast_start and p >= forecast_start else number_fmt)
                        if val is not None:
                            ws.write(row, col, val / 100 if is_pct else val, fmt)
                        else:
                            ws.write(row, col, "", fmt)
                    row += 1

                row += 1  # blank row between sections

            # ── Assumptions Sheet ────────────────────────────────────────
            ws_ass = workbook.add_worksheet("Assumptions")
            writer.sheets["Assumptions"] = ws_ass
            ws_ass.set_column(0, 0, 35)
            ws_ass.set_column(1, 1, 15)

            ws_ass.write(0, 0, "Assumption", header_fmt)
            ws_ass.write(0, 1, "Value", header_fmt)

            assumptions = model_summary.get("assumptions", {})
            for i, (k, v) in enumerate(assumptions.items(), start=1):
                ws_ass.write(i, 0, k.replace("_", " ").title(), label_fmt)
                if isinstance(v, float) and (k.endswith("_rate") or k.endswith("_margin") or k.endswith("pct")):
                    ws_ass.write(i, 1, v, pct_fmt)
                else:
                    ws_ass.write(i, 1, v if v is not None else "", number_fmt)

            # ── Scenario Comparison Sheet ────────────────────────────────
            if scenarios and len(scenarios) > 1:
                ws_sc = workbook.add_worksheet("Scenarios")
                writer.sheets["Scenarios"] = ws_sc
                ws_sc.set_column(0, 0, 35)

                key_metrics = ["revenue", "ebitda", "net_income", "free_cash_flow"]
                ws_sc.write(0, 0, "Metric / Period", header_fmt)

                col = 1
                scenario_cols: dict[str, int] = {}
                for sc in scenarios:
                    ws_sc.write(0, col, sc.get("scenario", ""), header_fmt)
                    scenario_cols[sc.get("scenario", "")] = col
                    col += 1

                row = 1
                for metric in key_metrics:
                    for p in periods[-4:]:  # last 4 periods
                        ws_sc.write(row, 0, f"{metric} – {p}", label_fmt)
                        for sc in scenarios:
                            sc_col = scenario_cols[sc.get("scenario", "")]
                            val = sc.get("line_items", {}).get(metric, {}).get(p)
                            ws_sc.write(row, sc_col, val if val is not None else "", number_fmt)
                        row += 1

            # ── Chart Sheet ──────────────────────────────────────────────
            ws_chart = workbook.add_worksheet("Charts")
            writer.sheets["Charts"] = ws_chart

            # Revenue chart
            rev_data = []
            for section in model_summary.get("sections", []):
                for item in section.get("rows", []):
                    if item["key"] == "revenue":
                        rev_data = [(p, item["values"].get(p, 0)) for p in periods]

            if rev_data:
                # Write data for chart
                ws_chart.write_column(1, 0, [r[0] for r in rev_data])
                ws_chart.write_column(1, 1, [r[1] if r[1] else 0 for r in rev_data])

                chart = workbook.add_chart({"type": "column"})
                chart.add_series({
                    "name": "Revenue",
                    "categories": ["Charts", 1, 0, len(rev_data), 0],
                    "values": ["Charts", 1, 1, len(rev_data), 1],
                    "fill": {"color": "#1e3a5f"},
                })
                chart.set_title({"name": "Revenue by Period"})
                chart.set_x_axis({"name": "Period"})
                chart.set_y_axis({"name": "Value"})
                ws_chart.insert_chart("D2", chart, {"x_scale": 2, "y_scale": 1.5})

        return buf.getvalue()

    def export_csv(self, model_summary: dict) -> bytes:
        """Export model as CSV (flat format)."""
        periods = model_summary.get("periods", [])
        rows = []

        for section in model_summary.get("sections", []):
            for item in section.get("rows", []):
                row = {
                    "section": section["name"],
                    "line_item": item["label"],
                    "key": item["key"],
                }
                for p in periods:
                    row[p] = item["values"].get(p)
                rows.append(row)

        df = pd.DataFrame(rows)
        return df.to_csv(index=False).encode("utf-8")

    def export_raw_data_csv(self, line_items: list[dict]) -> bytes:
        """Export raw extracted line items as CSV."""
        df = pd.DataFrame(line_items)
        return df.to_csv(index=False).encode("utf-8")
