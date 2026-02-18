from sqlalchemy import Column, Integer, String, DateTime, Float, JSON
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
import enum


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False, unique=True)           # stored filename (uuid-based)
    original_filename = Column(String, nullable=False)               # user-provided name
    file_type = Column(String, nullable=False)                       # pdf, xlsx, csv, docx, image
    file_size = Column(Integer)                                      # bytes
    file_path = Column(String, nullable=False)                       # absolute path on disk
    status = Column(String, default=DocumentStatus.UPLOADED.value)
    extraction_confidence = Column(Float, nullable=True)
    error_message = Column(String, nullable=True)
    page_count = Column(Integer, nullable=True)
    doc_metadata = Column(JSON, nullable=True)                       # author, dates, title, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    financial_data = relationship("FinancialLineItem", back_populates="document", cascade="all, delete-orphan")
    extracted_tables = relationship("ExtractedTable", back_populates="document", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "status": self.status,
            "extraction_confidence": self.extraction_confidence,
            "error_message": self.error_message,
            "page_count": self.page_count,
            "doc_metadata": self.doc_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
