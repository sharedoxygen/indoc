"""
Metadata and Annotation models
"""
from sqlalchemy import Column, String, Integer, Text, ForeignKey, JSON, Float, Boolean
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Metadata(BaseModel):
    __tablename__ = "metadata"
    
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    
    # Metadata fields
    key = Column(String(100), nullable=False)
    value = Column(Text)
    value_type = Column(String(50))  # string, number, date, boolean, json
    
    # Source
    source = Column(String(100))  # extracted, manual, system
    confidence = Column(Float)  # Confidence score for extracted metadata
    
    # Encryption
    is_encrypted = Column(Boolean, default=False)
    
    # Relationships
    document = relationship("Document", back_populates="document_metadata")


class Annotation(BaseModel):
    __tablename__ = "annotations"
    
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Annotation details
    annotation_type = Column(String(50), nullable=False)  # comment, highlight, tag, correction
    content = Column(Text)
    
    # Position in document
    page_number = Column(Integer)
    start_char = Column(Integer)
    end_char = Column(Integer)
    coordinates = Column(JSON)  # For spatial annotations on images/PDFs
    
    # Status
    status = Column(String(50), default="active")  # active, resolved, deleted
    
    # Relationships
    document = relationship("Document", back_populates="annotations")
    user = relationship("User", back_populates="annotations")