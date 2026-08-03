"""
Job Description Management Endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from uuid import uuid4
from datetime import datetime
from loguru import logger

from ...models.schemas import JobDescription
from ...models.enums import EducationLevel
from ...config import settings
from ...dependencies import get_db, get_embedder, get_extractor

router = APIRouter(prefix="/jobs", tags=["Job Description Management"])

@router.post("/create", response_model=dict)
async def create_job_description(
    job: JobDescription,
    db=Depends(get_db),
    embedder=Depends(get_embedder),
    extractor=Depends(get_extractor)
):
    """
    EMPLOYER ENDPOINT: Create a new job description for screening
    """
    from ...models.database import JobDescriptionDB
    
    # Generate unique job ID
    job_id = str(uuid4())
    
    # Auto-extract requirements from description if not provided
    if not job.required_skills or not job.min_experience_years:
        logger.info(f"Auto-extracting requirements for job: {job.title}")
        extracted = await extractor.extract_job_requirements(job.description)
        
        if not job.required_skills:
            job.required_skills = extracted.get('skills', [])
        if not job.min_experience_years:
            job.min_experience_years = extracted.get('min_experience', 0)
    
    # Generate embedding for this job
    job_embedding = await embedder.embed_job_description(job.description)
    
    # Store in database
    job_db = JobDescriptionDB(
        id=job_id,
        title=job.title,
        company=job.company,
        description_text=job.description,
        required_skills=job.required_skills,
        preferred_skills=job.preferred_skills,
        min_experience=job.min_experience_years,
        max_experience=job.max_experience_years,
        education_requirement=job.education_requirement.value if job.education_requirement else None,
        embedding=job_embedding.tolist() if job_embedding is not None else None,
        created_at=datetime.now()
    )
    
    db.add(job_db)
    db.commit()
    
    logger.info(f"Job description created with ID: {job_id}")
    
    return {
        "job_id": job_id,
        "title": job.title,
        "message": "Job description created successfully. Use this JOB_ID to get matches.",
        "requirements": {
            "required_skills": job.required_skills,
            "min_experience": job.min_experience_years,
            "education": job.education_requirement
        },
        "created_at": datetime.now().isoformat()
    }

@router.get("/{job_id}", response_model=dict)
async def get_job_description(
    job_id: str,
    db=Depends(get_db)
):
    """Get job description details by ID"""
    from ...models.database import JobDescriptionDB
    
    job = db.query(JobDescriptionDB).filter(JobDescriptionDB.id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job description not found")
    
    return {
        "job_id": job.id,
        "title": job.title,
        "company": job.company,
        "description": job.description_text,
        "required_skills": job.required_skills,
        "preferred_skills": job.preferred_skills,
        "min_experience": job.min_experience,
        "max_experience": job.max_experience,
        "education_requirement": job.education_requirement,
        "created_at": job.created_at.isoformat() if job.created_at else None
    }

@router.get("/", response_model=List[dict])
async def list_job_descriptions(
    skip: int = 0,
    limit: int = 50,
    db=Depends(get_db)
):
    """List all job descriptions"""
    from ...models.database import JobDescriptionDB
    
    jobs = db.query(JobDescriptionDB).order_by(
        JobDescriptionDB.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return [
        {
            "job_id": job.id,
            "title": job.title,
            "company": job.company,
            "required_skills_count": len(job.required_skills or []),
            "min_experience": job.min_experience,
            "created_at": job.created_at.isoformat() if job.created_at else None
        }
        for job in jobs
    ]

@router.put("/{job_id}", response_model=dict)
async def update_job_description(
    job_id: str,
    job: JobDescription,
    db=Depends(get_db),
    embedder=Depends(get_embedder)
):
    """Update an existing job description"""
    from ...models.database import JobDescriptionDB
    
    existing_job = db.query(JobDescriptionDB).filter(JobDescriptionDB.id == job_id).first()
    
    if not existing_job:
        raise HTTPException(status_code=404, detail="Job description not found")
    
    # Update fields
    existing_job.title = job.title
    existing_job.company = job.company
    existing_job.description_text = job.description
    existing_job.required_skills = job.required_skills
    existing_job.preferred_skills = job.preferred_skills
    existing_job.min_experience = job.min_experience_years
    existing_job.max_experience = job.max_experience_years
    existing_job.education_requirement = job.education_requirement.value if job.education_requirement else None
    
    # Regenerate embedding
    job_embedding = await embedder.embed_job_description(job.description)
    existing_job.embedding = job_embedding.tolist() if job_embedding is not None else None
    
    db.commit()
    
    return {
        "job_id": job_id,
        "message": "Job description updated successfully"
    }

@router.delete("/{job_id}")
async def delete_job_description(
    job_id: str,
    db=Depends(get_db)
):
    """Delete a job description"""
    from ...models.database import JobDescriptionDB, MatchResult
    
    job = db.query(JobDescriptionDB).filter(JobDescriptionDB.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job description not found")
    
    # Delete associated matches
    db.query(MatchResult).filter(MatchResult.job_id == job_id).delete()
    
    # Delete job
    db.delete(job)
    db.commit()
    
    return {"message": f"Job description '{job.title}' deleted successfully"}

