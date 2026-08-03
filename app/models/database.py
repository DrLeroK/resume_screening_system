"""
SQLAlchemy ORM models for database
"""

from sqlalchemy import (
    create_engine, Column, String, Integer, Float, 
    DateTime, JSON, Text, ForeignKey, Boolean, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
from uuid import uuid4
import json

from ..config import settings

Base = declarative_base()

def generate_uuid():
    """Generate UUID for primary keys"""
    return str(uuid4())

class Resume(Base):
    """Resume metadata and extracted information"""
    __tablename__ = "resumes"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer)
    file_hash = Column(String(64), index=True)
    
    # Extracted data (stored as JSON for flexibility)
    text = Column(Text)  # Full extracted text
    personal_info = Column(JSON)
    skills = Column(JSON)  # List of skills
    education = Column(JSON)  # List of education entries
    experience = Column(JSON)  # List of experience entries
    total_experience_years = Column(Float, default=0)
    languages = Column(JSON, default=list)
    certifications = Column(JSON, default=list)
    
    # For bias detection (optional, could be None)
    inferred_gender = Column(String(20))
    inferred_age_group = Column(String(20))
    inferred_ethnicity_hint = Column(String(50))
    
    # Processing metadata
    status = Column(String(20), default="pending", index=True)
    error_message = Column(Text)
    processing_time_ms = Column(Integer)
    
    # Dates
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    matches = relationship("MatchResult", back_populates="resume", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_resume_status_created', 'status', 'created_at'),
        Index('idx_resume_experience', 'total_experience_years'),
    )
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "total_experience_years": self.total_experience_years,
            "languages": json.loads(self.languages) if self.languages else [],
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class JobDescriptionDB(Base):
    """Job descriptions for matching"""
    __tablename__ = "job_descriptions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    company = Column(String(255))
    description_text = Column(Text, nullable=False)
    
    # Extracted entities
    required_skills = Column(JSON)
    preferred_skills = Column(JSON)
    min_experience = Column(Float, default=0)
    max_experience = Column(Float)
    education_requirement = Column(String(50))
    responsibilities = Column(JSON)
    
    # Embedding
    embedding = Column(JSON)  # Store as list for potential reuse
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    matches = relationship("MatchResult", back_populates="job")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "company": self.company,
            "min_experience": self.min_experience
        }

class MatchResult(Base):
    """Results of resume-JD matching"""
    __tablename__ = "match_results"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    resume_id = Column(String(36), ForeignKey("resumes.id", ondelete="CASCADE"))
    job_id = Column(String(36), ForeignKey("job_descriptions.id", ondelete="CASCADE"))
    
    # Scores
    overall_score = Column(Float, index=True)
    skill_match_score = Column(Float)
    experience_match_score = Column(Float)
    education_match_score = Column(Float)
    semantic_similarity = Column(Float)
    
    # Detailed results
    matched_skills = Column(JSON)
    missing_skills = Column(JSON)
    match_components = Column(JSON)
    recommendation = Column(String(50))
    explanation = Column(Text)
    
    # Metadata
    processing_time_ms = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    resume = relationship("Resume", back_populates="matches")
    job = relationship("JobDescriptionDB", back_populates="matches")
    
    # Indexes
    __table_args__ = (
        Index('idx_match_resume_job', 'resume_id', 'job_id', unique=True),
        Index('idx_match_score', 'overall_score'),
    )

class BiasAnalysis(Base):
    """Historical bias analysis results"""
    __tablename__ = "bias_analyses"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    attribute = Column(String(50))
    metric = Column(String(50))
    value = Column(Float)
    is_biased = Column(Boolean)
    sample_size = Column(Integer)
    distribution = Column(JSON)
    analysis_date = Column(DateTime, server_default=func.now(), index=True)
    
    __table_args__ = (
        Index('idx_bias_attr_date', 'attribute', 'analysis_date'),
    )

class ProcessingTask(Base):
    """Track background processing tasks"""
    __tablename__ = "processing_tasks"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_type = Column(String(50))  # parse, match, bias_analysis
    target_id = Column(String(36))  # resume_id, match_id, etc.
    status = Column(String(20), default="pending", index=True)
    progress = Column(Integer, default=0)
    result = Column(JSON)
    error = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    __table_args__ = (
        Index('idx_task_status_type', 'status', 'task_type'),
    )

class UsageLog(Base):
    """Track API usage for monitoring"""
    __tablename__ = "usage_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    endpoint = Column(String(255))
    method = Column(String(10))
    status_code = Column(Integer)
    processing_time_ms = Column(Integer)
    client_ip = Column(String(45))
    created_at = Column(DateTime, server_default=func.now(), index=True)
    
    __table_args__ = (
        Index('idx_usage_created', 'created_at'),
        Index('idx_usage_endpoint', 'endpoint'),
    )

def init_database():
    """Initialize database and create tables"""
    engine = create_engine(f"sqlite:///{settings.database_path}", echo=settings.debug)
    Base.metadata.create_all(engine)
    return engine

def get_session():
    """Get database session"""
    engine = create_engine(f"sqlite:///{settings.database_path}", echo=settings.debug)
    Session = sessionmaker(bind=engine)
    return Session()