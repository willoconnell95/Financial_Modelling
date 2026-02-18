"""
Extraction data API endpoints.
GET  /extraction/line-items          - All extracted line items
GET  /extraction/line-items/summary  - Grouped summary
GET  /extraction/by-document/{id}    - Items from a specific document
DELETE /extraction/line-items/{id}   - Remove an incorrect item
PATCH  /extraction/line-items/{id}   - Correct an item
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.financial_data import FinancialLineItem

router = APIRouter(prefix="/extraction", tags=["extraction"])


class LineItemUpdate(BaseModel):
    normalized_name: Optional[str] = None
    value: Optional[float] = None
    period: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None


@router.get("/line-items")
def list_line_items(
    category: Optional[str] = None,
    normalized_name: Optional[str] = None,
    period: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all extracted financial line items, with optional filters."""
    q = db.query(FinancialLineItem)
    if category:
        q = q.filter(FinancialLineItem.category == category)
    if normalized_name:
        q = q.filter(FinancialLineItem.normalized_name == normalized_name)
    if period:
        q = q.filter(FinancialLineItem.period == period)

    items = q.order_by(
        FinancialLineItem.category,
        FinancialLineItem.normalized_name,
        FinancialLineItem.period,
    ).all()
    return {"line_items": [i.to_dict() for i in items]}


@router.get("/line-items/summary")
def line_items_summary(db: Session = Depends(get_db)):
    """
    Return a pivot-style summary:
    {metric: {period: value}} for all extracted data.
    """
    items = db.query(FinancialLineItem).all()

    summary: dict[str, dict] = {}
    for item in items:
        key = item.normalized_name
        if key not in summary:
            summary[key] = {
                "category": item.category,
                "periods": {},
                "unit": item.unit,
            }
        # If same metric/period appears multiple times, take highest-confidence value
        existing = summary[key]["periods"].get(item.period)
        if existing is None or item.confidence_score > existing.get("confidence", 0):
            summary[key]["periods"][item.period] = {
                "value": item.value,
                "confidence": item.confidence_score,
            }

    # Flatten: {metric: {period: value}}
    flat: dict[str, dict] = {}
    for key, data in summary.items():
        flat[key] = {
            "category": data["category"],
            "unit": data["unit"],
            "values": {p: v["value"] for p, v in data["periods"].items()},
        }

    return {"summary": flat}


@router.get("/by-document/{document_id}")
def items_by_document(document_id: int, db: Session = Depends(get_db)):
    """Return all line items extracted from a specific document."""
    items = (
        db.query(FinancialLineItem)
        .filter(FinancialLineItem.document_id == document_id)
        .order_by(FinancialLineItem.category, FinancialLineItem.period)
        .all()
    )
    return {"line_items": [i.to_dict() for i in items]}


@router.patch("/line-items/{item_id}")
def update_line_item(
    item_id: int,
    update: LineItemUpdate,
    db: Session = Depends(get_db),
):
    """Manually correct an extracted line item."""
    item = db.query(FinancialLineItem).filter(FinancialLineItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Line item not found")

    for field, val in update.dict(exclude_none=True).items():
        setattr(item, field, val)

    db.commit()
    db.refresh(item)
    return item.to_dict()


@router.delete("/line-items/{item_id}")
def delete_line_item(item_id: int, db: Session = Depends(get_db)):
    """Remove an incorrectly extracted line item."""
    item = db.query(FinancialLineItem).filter(FinancialLineItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Line item not found")
    db.delete(item)
    db.commit()
    return {"deleted": item_id}
