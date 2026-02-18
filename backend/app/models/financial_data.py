from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime


class FinancialLineItem(Base):
    """
    Normalised financial line item extracted from a document.
    One row per (document, category, line_item_name, period).
    """
    __tablename__ = "financial_line_items"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)

    # Classification
    category = Column(String, index=True)       # income_statement | balance_sheet | cash_flow | kpi | other
    subcategory = Column(String, nullable=True)  # revenue | cogs | opex | headcount | arr | …
    line_item_name = Column(String)              # raw name from doc
    normalized_name = Column(String, index=True) # canonical key (e.g. "revenue", "ebitda")

    # Time
    period = Column(String, index=True)          # e.g. "FY2023", "2023-Q1", "2023-01"
    period_type = Column(String)                 # annual | quarterly | monthly

    # Value
    value = Column(Float)
    unit = Column(String, default="GBP")         # GBP | USD | EUR | % | headcount | x
    currency = Column(String, nullable=True)
    is_forecast = Column(Boolean, default=False)

    # Quality
    confidence_score = Column(Float, default=1.0)
    raw_text = Column(String, nullable=True)     # raw extracted text that produced this value

    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="financial_data")

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "category": self.category,
            "subcategory": self.subcategory,
            "line_item_name": self.line_item_name,
            "normalized_name": self.normalized_name,
            "period": self.period,
            "period_type": self.period_type,
            "value": self.value,
            "unit": self.unit,
            "currency": self.currency,
            "is_forecast": self.is_forecast,
            "confidence_score": self.confidence_score,
        }


class ExtractedTable(Base):
    """Raw table extracted from a document, before normalisation."""
    __tablename__ = "extracted_tables"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    table_index = Column(Integer, default=0)
    page_number = Column(Integer, nullable=True)
    headers = Column(JSON, nullable=True)       # list of header strings
    raw_data = Column(JSON)                     # list of row dicts
    table_type = Column(String, nullable=True)  # detected type
    confidence_score = Column(Float, default=0.5)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="extracted_tables")

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "table_index": self.table_index,
            "page_number": self.page_number,
            "headers": self.headers,
            "raw_data": self.raw_data,
            "table_type": self.table_type,
            "confidence_score": self.confidence_score,
        }
