"""
Resume-Job Description matching service - FIXED VERSION
"""

from typing import List, Dict, Any, Tuple, Optional
from uuid import uuid4
import asyncio
from datetime import datetime
import numpy as np
from loguru import logger

from ..models.schemas import (
    JobDescription, ResumeMatchResult, MatchScore,
    ParsedResume, ResumeSummary
)
from ..models.enums import EducationLevel
from ..config import settings
from ..core.exceptions import ExtractionError

class ResumeMatcher:
    """Match resumes against job descriptions"""
    
    def __init__(self, embedder, searcher):
        self.embedder = embedder
        self.searcher = searcher
        
        self.weights = {
            'skills': 0.35,
            'experience': 0.25,
            'education': 0.15,
            'semantic': 0.25
        }
    
    async def match_resume_to_job(
        self,
        resume: ParsedResume,
        job: JobDescription,
        resume_embedding: Optional[np.ndarray] = None
    ) -> ResumeMatchResult:
        """Match a single resume against a job description"""
        
        if resume_embedding is None and resume.embedding:
            resume_embedding = np.array(resume.embedding)
        elif resume_embedding is None:
            resume_embedding = await self.embedder.embed(resume.text)
        
        job_embedding = await self.embedder.embed_job_description(job.description)
        
        # Calculate match scores - FIXED: Access Pydantic models as attributes
        skill_score = await self._calculate_skill_match(resume.skills, job)
        experience_score = await self._calculate_experience_match(
            resume.total_experience_years, job
        )
        education_score = await self._calculate_education_match(
            resume.education_level, job
        )
        semantic_score = await self.embedder.compute_similarity(
            resume_embedding, job_embedding
        )
        
        overall_score = (
            skill_score * self.weights['skills'] +
            experience_score * self.weights['experience'] +
            education_score * self.weights['education'] +
            semantic_score * self.weights['semantic']
        )
        
        matched_skills, missing_skills = self._get_skill_matches(
            resume.skills, job.required_skills
        )
        
        recommendation = self._get_recommendation(overall_score)
        explanation = self._generate_explanation(
            overall_score, skill_score, experience_score, 
            education_score, semantic_score, matched_skills, missing_skills
        )
        
        match_components = [
            MatchScore(
                component="Skills Match",
                score=skill_score,
                weight=self.weights['skills'],
                details={"matched": len(matched_skills), "missing": len(missing_skills)}
            ),
            MatchScore(
                component="Experience Match",
                score=experience_score,
                weight=self.weights['experience'],
                details={"required": job.min_experience_years, "has": resume.total_experience_years}
            ),
            MatchScore(
                component="Education Match",
                score=education_score,
                weight=self.weights['education'],
                details={"required": job.education_requirement, "has": resume.education_level}
            ),
            MatchScore(
                component="Semantic Similarity",
                score=semantic_score,
                weight=self.weights['semantic'],
                details={}
            )
        ]
        
        resume_summary = ResumeSummary(
            id=resume.id,
            filename=resume.filename,
            personal_info=resume.personal_info,
            total_skills=len(resume.skills),
            total_experience_years=resume.total_experience_years,
            education_level=resume.education_level,
            status=resume.status,
            created_at=resume.created_at
        )
        
        return ResumeMatchResult(
            resume_id=resume.id,
            resume_summary=resume_summary,
            overall_score=overall_score,
            skill_match_score=skill_score,
            experience_match_score=experience_score,
            education_match_score=education_score,
            semantic_similarity=semantic_score,
            match_components=match_components,
            matched_skills=matched_skills[:20],
            missing_skills=missing_skills[:20],
            recommendation=recommendation,
            explanation=explanation
        )
    
    async def match_batch(
        self,
        resumes: List[ParsedResume],
        job: JobDescription,
        top_k: int = 10,
        min_score: float = 0.5
    ) -> List[ResumeMatchResult]:
        """Match multiple resumes against a job description"""
        if not resumes:
            return []
        
        resume_texts = [r.text for r in resumes]
        embeddings = await self.embedder.embed_batch(resume_texts)
        
        tasks = []
        for resume, embedding in zip(resumes, embeddings):
            if embedding is not None:
                task = self.match_resume_to_job(resume, job, embedding)
                tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        filtered = [r for r in results if r.overall_score >= min_score]
        sorted_results = sorted(filtered, key=lambda x: x.overall_score, reverse=True)
        
        return sorted_results[:top_k]
    
    async def _calculate_skill_match(
        self,
        resume_skills: List,
        job: JobDescription
    ) -> float:
        """Calculate skill match score - FIXED: Access Pydantic models as attributes"""
        if not job.required_skills:
            return 1.0
        
        # FIXED: Access skill.name as attribute, not .get()
        resume_skill_names = {s.name.lower() for s in resume_skills}
        required_skills = {s.lower() for s in job.required_skills}
        preferred_skills = {s.lower() for s in job.preferred_skills}
        
        matched_required = len(resume_skill_names & required_skills)
        required_score = matched_required / len(required_skills) if required_skills else 1.0
        
        matched_preferred = len(resume_skill_names & preferred_skills)
        preferred_score = matched_preferred / len(preferred_skills) if preferred_skills else 0.5
        
        skill_score = (required_score * 0.8) + (preferred_score * 0.2)
        
        return min(1.0, skill_score)
    
    async def _calculate_experience_match(
        self,
        resume_experience_years: float,
        job: JobDescription
    ) -> float:
        """Calculate experience match score"""
        required = job.min_experience_years
        
        if required == 0:
            return 1.0
        
        if resume_experience_years >= required:
            bonus = min(0.5, (resume_experience_years - required) / required)
            return min(1.0, 1.0 + bonus)
        else:
            ratio = resume_experience_years / required
            return ratio * 0.7
    
    async def _calculate_education_match(
        self,
        resume_level: EducationLevel,
        job: JobDescription
    ) -> float:
        """Calculate education match score"""
        if not job.education_requirement:
            return 1.0
        
        level_values = {
            EducationLevel.HIGH_SCHOOL: 1,
            EducationLevel.BACHELORS: 2,
            EducationLevel.MASTERS: 3,
            EducationLevel.PHD: 4,
            EducationLevel.UNKNOWN: 0
        }
        
        resume_value = level_values.get(resume_level, 0)
        required_value = level_values.get(job.education_requirement, 0)
        
        if required_value == 0:
            return 1.0
        
        if resume_value >= required_value:
            return 1.0
        elif resume_value == 0:
            return 0.0
        else:
            return resume_value / required_value
    
    def _get_skill_matches(
        self,
        resume_skills: List,
        required_skills: List[str]
    ) -> Tuple[List[str], List[str]]:
        """Get matched and missing skills - FIXED: Access Pydantic models as attributes"""
        resume_skill_names = {s.name.lower() for s in resume_skills}
        required_lower = {s.lower() for s in required_skills}
        
        matched = [s for s in required_skills if s.lower() in resume_skill_names]
        missing = [s for s in required_skills if s.lower() not in resume_skill_names]
        
        return matched, missing
    
    def _get_recommendation(self, score: float) -> str:
        """Get recommendation based on score"""
        if score >= 0.85:
            return "Strong Match"
        elif score >= 0.70:
            return "Good Match"
        elif score >= 0.55:
            return "Potential Match"
        else:
            return "Not Recommended"
    
    def _generate_explanation(
        self,
        overall: float,
        skills: float,
        experience: float,
        education: float,
        semantic: float,
        matched_skills: List[str],
        missing_skills: List[str]
    ) -> str:
        """Generate human-readable explanation"""
        explanations = []
        
        if overall >= 0.85:
            explanations.append("This candidate is highly qualified for the position.")
        elif overall >= 0.70:
            explanations.append("This candidate meets most of the requirements.")
        elif overall >= 0.55:
            explanations.append("This candidate has potential but may need additional training.")
        else:
            explanations.append("This candidate does not meet the minimum requirements.")
        
        if skills >= 0.8:
            explanations.append(f"Strong skill match with {len(matched_skills)} required skills.")
        elif missing_skills:
            explanations.append(f"Missing key skills: {', '.join(missing_skills[:3])}.")
        
        if experience >= 0.9:
            explanations.append("Excellent experience match.")
        elif experience < 0.6:
            explanations.append("Experience level below requirements.")
        
        return " ".join(explanations)
