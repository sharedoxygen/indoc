"""
Document and DocumentChunk models
"""
from sqlalchemy import Column, String, Integer, Float, Text, Boolean, ForeignKey, JSON, LargeBinary, Enum
from sqlalchemy.orm import relationship
from app.core.types import GUID
import uuid

from app.models.base import BaseModel
from app.models.classification import DocumentClassification


class Document(BaseModel):
    __tablename__ = "documents"
    
    # Basic info
    uuid = Column(GUID(), default=uuid.uuid4, unique=True, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_hash = Column(String(64), index=True)  # SHA-256 hash
    
    # Storage
    storage_path = Column(String(500), nullable=False)
    temp_path = Column(String(500))  # Temporary path during processing
    folder_path = Column(String(1000), nullable=True, index=True)  # Logical folder hierarchy (e.g., "2022/ZX10R/manuals")
    parent_folder_id = Column(Integer, ForeignKey("documents.id"), nullable=True)  # For nested folder support
    
    # Processing status
    status = Column(String(50), default="pending", nullable=False)  # pending, processing, indexed, failed
    error_message = Column(Text)
    virus_scan_status = Column(String(50), default="pending")  # pending, clean, infected, error
    virus_scan_result = Column(JSON)
    
    # Metadata
    title = Column(String(500))
    description = Column(Text)
    tags = Column(JSON, default=list)
    custom_metadata = Column(JSON, default=dict)
    document_set_id = Column(String(100), nullable=True, index=True)  # For grouping related documents
    
    # Extracted content
    full_text = Column(Text)
    extracted_data = Column(JSON)  # Structured data from forms/tables
    language = Column(String(10))
    
    # Search
    elasticsearch_id = Column(String(100))
    qdrant_id = Column(String(100))
    
    # Security
    encrypted_fields = Column(JSON, default=list)  # List of encrypted field names
    access_level = Column(String(50), default="private")  # Legacy field (deprecated)
    classification = Column(
        Enum(DocumentClassification),
        default=DocumentClassification.INTERNAL,
        nullable=False,
        index=True
    )  # ABAC classification level
    
    # Multi-tenancy  
    tenant_id = Column(GUID(), nullable=True, index=True)
    
    # User relationship
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_by_user = relationship("User", back_populates="documents")
    
    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    document_metadata = relationship("Metadata", back_populates="document", cascade="all, delete-orphan")
    annotations = relationship("Annotation", back_populates="document", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(BaseModel):
    __tablename__ = "document_chunks"
    
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    
    # Content
    content = Column(Text, nullable=False)
    chunk_type = Column(String(50))  # paragraph, section, table, image_caption
    
    # Position in document
    page_number = Column(Integer)
    start_char = Column(Integer)
    end_char = Column(Integer)
    
    # Embeddings
    embedding_vector = Column(LargeBinary)  # Stored as binary
    embedding_model = Column(String(100))
    
    # Search scores
    relevance_score = Column(Float)
    
    # Relationships
    document = relationship("Document", back_populates="chunks")