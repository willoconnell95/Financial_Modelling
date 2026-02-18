from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


class DocumentBase(BaseModel):
    original_filename: str


class DocumentCreate(DocumentBase):
    pass


class ExtractedTableSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    page_number: Optional[int]
    table_index: int
    headers: Optional[list]
    data: dict
    confidence: Optional[float]
    table_type: Optional[str]
    created_at: datetime


class ExtractedTextSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    page_number: Optional[int]
    content: str
    text_type: Optional[str]
    created_at: datetime


class DocumentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    original_filename: str
    file_size: int
    mime_type: Optional[str]
    document_type: str
    status: str
    page_count: Optional[int]
    extraction_confidence: Optional[float]
    extraction_errors: Optional[dict]
    metadata_: Optional[dict]
    created_at: datetime
    updated_at: datetime


class DocumentDetailSchema(DocumentSchema):
    tables: list[ExtractedTableSchema] = []
    texts: list[ExtractedTextSchema] = []


class DocumentListResponse(BaseModel):
    total: int
    documents: list[DocumentSchema]


class ExtractionResult(BaseModel):
    document_id: int
    tables_extracted: int
    text_blocks_extracted: int
    financial_records_created: int
    confidence: float
    errors: list[str] = []
    warnings: list[str] = []
