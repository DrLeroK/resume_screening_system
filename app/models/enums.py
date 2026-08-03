"""
Enum definitions for type safety
"""

from enum import Enum

class ResumeStatus(str, Enum):
    """Status of resume processing"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"

class MatchStatus(str, Enum):
    """Status of matching job"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class DocumentType(str, Enum):
    """Type of uploaded document"""
    PDF = "pdf"
    DOCX = "docx"
    UNKNOWN = "unknown"

class SkillType(str, Enum):
    """Type of skill"""
    TECHNICAL = "technical"
    SOFT = "soft"
    LANGUAGE = "language"
    CERTIFICATION = "certification"

class ExperienceLevel(str, Enum):
    """Experience level"""
    ENTRY = "entry"  # 0-2 years
    MID = "mid"      # 3-5 years
    SENIOR = "senior" # 6-9 years
    EXPERT = "expert" # 10+ years
    UNKNOWN = "unknown"

class EducationLevel(str, Enum):
    """Education level"""
    HIGH_SCHOOL = "high_school"
    BACHELORS = "bachelors"
    MASTERS = "masters"
    PHD = "phd"
    UNKNOWN = "unknown"

class Gender(str, Enum):
    """Gender for bias detection (anonymized)"""
    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non_binary"
    UNKNOWN = "unknown"

class BiasMetric(str, Enum):
    """Types of bias metrics"""
    STATISTICAL_PARITY = "statistical_parity"
    DEMOGRAPHIC_PARITY = "demographic_parity"
    EQUAL_OPPORTUNITY = "equal_opportunity"
    DISPARATE_IMPACT = "disparate_impact"