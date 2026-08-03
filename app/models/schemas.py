"""
Pydantic schemas for API request/response validation
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, UUID4
from uuid import UUID
from .enums import ResumeStatus, MatchStatus, SkillType, ExperienceLevel, EducationLevel

# ============== Resume Schemas ==============

class Skill(BaseModel):
    """Skill extracted from resume"""
    name: str
    type: SkillType = SkillType.TECHNICAL
    confidence: float = Field(ge=0, le=1)
    context: Optional[str] = None

class Education(BaseModel):
    """Education entry"""
    degree: str
    institution: str
    field_of_study: Optional[str] = None
    graduation_year: Optional[int] = Field(None, ge=1900, le=2030)
    level: EducationLevel = EducationLevel.UNKNOWN
    confidence: float = Field(ge=0, le=1)

class Experience(BaseModel):
    """Work experience entry"""
    title: str
    company: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_years: float = Field(ge=0)
    description: Optional[str] = None
    responsibilities: List[str] = []
    achievements: List[str] = []
    confidence: float = Field(ge=0, le=1)

class PersonalInfo(BaseModel):
    """Personal information (anonymized for bias detection)"""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    # Bias detection fields (optional, for analysis)
    inferred_gender: Optional[str] = None
    inferred_age_group: Optional[str] = None
    inferred_ethnicity_hint: Optional[str] = None

class ParsedResume(BaseModel):
    """Complete parsed resume data"""
    id: UUID4
    filename: str
    text: str
    personal_info: PersonalInfo
    skills: List[Skill] = []
    education: List[Education] = []
    experience: List[Experience] = []
    total_experience_years: float = 0
    education_level: EducationLevel = EducationLevel.UNKNOWN
    languages: List[str] = []
    certifications: List[str] = []
    embedding: Optional[List[float]] = None  # Not returned in API responses
    status: ResumeStatus
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class ResumeUploadResponse(BaseModel):
    """Response after resume upload"""
    resume_id: UUID4
    filename: str
    status: ResumeStatus
    message: str
    created_at: datetime

class ResumeSummary(BaseModel):
    """Lightweight resume summary for lists"""
    id: UUID4
    filename: str
    personal_info: PersonalInfo
    total_skills: int
    total_experience_years: float
    education_level: EducationLevel
    status: ResumeStatus
    created_at: datetime

# ============== Job Description Schemas ==============

class JobDescription(BaseModel):
    """Job description input"""
    title: str
    company: Optional[str] = None
    description: str
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    min_experience_years: float = 0
    max_experience_years: Optional[float] = None
    education_requirement: Optional[EducationLevel] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None  # full-time, part-time, contract

class JobDescriptionEntity(BaseModel):
    """Extracted entities from JD"""
    skills_required: List[str] = []
    skills_preferred: List[str] = []
    experience_required: float = 0
    education_required: Optional[EducationLevel] = None
    responsibilities: List[str] = []
    benefits: List[str] = []

# ============== Matching Schemas ==============

class MatchScore(BaseModel):
    """Individual match score component"""
    component: str
    score: float
    weight: float
    details: Dict[str, Any]

class ResumeMatchResult(BaseModel):
    """Match result for a single resume"""
    resume_id: UUID4
    resume_summary: ResumeSummary
    overall_score: float = Field(ge=0, le=1)
    skill_match_score: float = Field(ge=0, le=1)
    experience_match_score: float = Field(ge=0, le=1)
    education_match_score: float = Field(ge=0, le=1)
    semantic_similarity: float = Field(ge=0, le=1)
    match_components: List[MatchScore]
    matched_skills: List[str]
    missing_skills: List[str]
    recommendation: str  # Strong Match, Good Match, Potential, Not Recommended
    explanation: str

class MatchRequest(BaseModel):
    """Request for matching"""
    job_description: JobDescription
    top_k: int = Field(default=10, ge=1, le=100)
    min_score_threshold: float = Field(default=0.5, ge=0, le=1)
    include_embeddings: bool = False

class MatchResponse(BaseModel):
    """Response for match request"""
    match_id: UUID4
    job_description: JobDescription
    results: List[ResumeMatchResult]
    total_matches: int
    processing_time_ms: int
    timestamp: datetime

class AsyncMatchResponse(BaseModel):
    """Response for async match request"""
    match_id: UUID4
    status: MatchStatus
    message: str

# ============== Search Schemas ==============

class SearchQuery(BaseModel):
    """Search query for resumes"""
    query: str
    skill_filter: Optional[List[str]] = None
    min_experience: Optional[float] = None
    max_experience: Optional[float] = None
    education_level: Optional[EducationLevel] = None
    top_k: int = Field(default=20, ge=1, le=200)

class SearchResult(BaseModel):
    """Single search result"""
    resume_id: UUID4
    resume_summary: ResumeSummary
    similarity_score: float
    matching_skills: List[str]
    relevance_explanation: str

class SearchResponse(BaseModel):
    """Response for search request"""
    query: str
    results: List[SearchResult]
    total_results: int
    processing_time_ms: int

# ============== Bias Detection Schemas ==============

class BiasAnalysisRequest(BaseModel):
    """Request for bias analysis"""
    attribute: str  # gender, age, ethnicity
    sample_size: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class BiasMetricResult(BaseModel):
    """Single bias metric result"""
    metric_name: str
    value: float
    interpretation: str
    is_biased: bool
    threshold: float

class AttributeAnalysis(BaseModel):
    """Analysis for a single protected attribute"""
    attribute: str
    metrics: List[BiasMetricResult]
    overall_bias_score: float
    recommendation: str
    sample_size: int
    distribution: Dict[str, int]  # e.g., {"male": 450, "female": 400}

class BiasAnalysisResponse(BaseModel):
    """Response for bias analysis"""
    analysis_id: UUID4
    timestamp: datetime
    analyses: List[AttributeAnalysis]
    overall_risk_level: str  # Low, Medium, High
    recommendations: List[str]

# ============== Health Check Schemas ==============

class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: datetime
    components: Dict[str, str]