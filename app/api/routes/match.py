"""
Resume-Job Description matching endpoints
"""
from typing import Optional, List 
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List
from uuid import uuid4
from datetime import datetime
from loguru import logger

from ...models.schemas import (
    MatchRequest, MatchResponse, AsyncMatchResponse,
    ResumeMatchResult, JobDescription
)
# from ...models.enums import MatchStatus
from ...models.enums import MatchStatus, EducationLevel
from ...config import settings
from ...dependencies import get_db, get_matcher, get_embedder, get_searcher
from ...core.task_manager import task_manager

router = APIRouter(prefix="/matches", tags=["Candidate Matching"])

@router.post("/real-time", response_model=MatchResponse)
async def match_realtime(
    request: MatchRequest,
    db=Depends(get_db),
    matcher=Depends(get_matcher),
    embedder=Depends(get_embedder)
):
    """
    Real-time matching of job description against all resumes
    Returns results immediately (synchronous)
    """
    from ...models.database import Resume
    
    start_time = datetime.now()
    
    # Get all completed resumes
    resumes_data = db.query(Resume).filter(
        Resume.status == "completed"
    ).all()
    
    if not resumes_data:
        raise HTTPException(status_code=404, detail="No resumes found in database")
    
    # Convert to Pydantic models and get embeddings
    resumes = []
    for r in resumes_data:
        from ...models.schemas import PersonalInfo, ParsedResume
        
        resume = ParsedResume(
            id=r.id,
            filename=r.original_filename,
            text=r.text,
            personal_info=PersonalInfo(**r.personal_info) if r.personal_info else PersonalInfo(),
            skills=r.skills or [],
            education=r.education or [],
            experience=r.experience or [],
            total_experience_years=r.total_experience_years or 0,
            education_level=getattr(r, "education_level", "bachelors"),
            languages=r.languages or [],
            certifications=r.certifications or [],
            status=r.status,
            created_at=r.created_at,
            updated_at=r.updated_at
        )
        resumes.append(resume)
    
    # Perform matching
    results = await matcher.match_batch(
        resumes=resumes,
        job=request.job_description,
        top_k=request.top_k,
        min_score=request.min_score_threshold
    )
    
    processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
    
    return MatchResponse(
        match_id=uuid4(),
        job_description=request.job_description,
        results=results,
        total_matches=len(results),
        processing_time_ms=processing_time_ms,
        timestamp=datetime.now()
    )

@router.post("/async", response_model=AsyncMatchResponse)
async def match_async(
    request: MatchRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """
    Async matching for large batches
    Returns task ID for polling
    """
    from ...models.database import JobDescriptionDB, ProcessingTask
    
    # Store job description
    job_db = JobDescriptionDB(
        id=str(uuid4()),
        title=request.job_description.title,
        company=request.job_description.company,
        description_text=request.job_description.description,
        required_skills=request.job_description.required_skills,
        preferred_skills=request.job_description.preferred_skills,
        min_experience=request.job_description.min_experience_years,
        max_experience=request.job_description.max_experience_years,
        education_requirement=request.job_description.education_requirement.value if request.job_description.education_requirement else None
    )
    db.add(job_db)
    db.commit()
    
    # Create task
    match_id = str(uuid4())
    task = ProcessingTask(
        id=match_id,
        task_type="match",
        target_id=job_db.id,
        status=MatchStatus.PENDING.value
    )
    db.add(task)
    db.commit()
    
    # Schedule background task
    task_manager.add_task(
        task_id=match_id,
        task_type="match_job",
        func=process_match_background,
        args=(match_id, job_db.id, request.job_description, request.top_k, request.min_score_threshold),
        kwargs={}
    )
    
    return AsyncMatchResponse(
        match_id=match_id,
        status=MatchStatus.PENDING,
        message="Match processing started. Poll /matches/{match_id} for results"
    )

async def process_match_background(
    match_id: str,
    job_id: str,
    job_description: JobDescription,
    top_k: int,
    min_score: float
):
    """
    Background task for async matching
    """
    from ...models.database import get_session, Resume, MatchResult, ProcessingTask
    from ...services.matcher import ResumeMatcher
    from ...services.embedder import TextEmbedder
    from ...models.schemas import PersonalInfo, ParsedResume
    
    db = get_session()
    
    try:
        # Update task status
        db.query(ProcessingTask).filter(
            ProcessingTask.id == match_id
        ).update({"status": MatchStatus.PROCESSING.value})
        db.commit()
        
        # Get all resumes
        resumes_data = db.query(Resume).filter(Resume.status == "completed").all()
        
        if not resumes_data:
            db.query(ProcessingTask).filter(
                ProcessingTask.id == match_id
            ).update({
                "status": MatchStatus.FAILED.value,
                "error": "No resumes found"
            })
            db.commit()
            return
        
        # Convert to Pydantic models
        resumes = []
        for r in resumes_data:
            resume = ParsedResume(
                id=r.id,
                filename=r.original_filename,
                text=r.text,
                personal_info=PersonalInfo(**r.personal_info) if r.personal_info else PersonalInfo(),
                skills=r.skills or [],
                education=r.education or [],
                experience=r.experience or [],
                total_experience_years=r.total_experience_years or 0,
                education_level=getattr(r, "education_level", "bachelors"),
                languages=r.languages or [],
                certifications=r.certifications or [],
                status=r.status,
                created_at=r.created_at,
                updated_at=r.updated_at
            )
            resumes.append(resume)
        
        # Initialize matcher
        embedder = TextEmbedder()
        from ...services.searcher import FAISSSearcher
        searcher = FAISSSearcher(embedder.get_embedding_dimension())
        matcher = ResumeMatcher(embedder, searcher)
        
        # Perform matching
        results = await matcher.match_batch(
            resumes=resumes,
            job=job_description,
            top_k=top_k,
            min_score=min_score
        )
        
        # Store results in database
        for result in results:
            match_result = MatchResult(
                id=str(uuid4()),
                resume_id=str(result.resume_id),
                job_id=job_id,
                overall_score=result.overall_score,
                skill_match_score=result.skill_match_score,
                experience_match_score=result.experience_match_score,
                education_match_score=result.education_match_score,
                semantic_similarity=result.semantic_similarity,
                matched_skills=result.matched_skills,
                missing_skills=result.missing_skills,
                match_components=[c.dict() for c in result.match_components],
                recommendation=result.recommendation,
                explanation=result.explanation
            )
            db.add(match_result)
        
        # Update task with results
        db.query(ProcessingTask).filter(
            ProcessingTask.id == match_id
        ).update({
            "status": MatchStatus.COMPLETED.value,
            "result": {
                "total_matches": len(results),
                "top_scores": [r.overall_score for r in results[:5]]
            }
        })
        db.commit()
        
        logger.info(f"Completed async match {match_id} with {len(results)} results")
        
    except Exception as e:
        logger.error(f"Async match {match_id} failed: {str(e)}")
        db.query(ProcessingTask).filter(
            ProcessingTask.id == match_id
        ).update({
            "status": MatchStatus.FAILED.value,
            "error": str(e)
        })
        db.commit()
    finally:
        db.close()


@router.get("/{match_id}", response_model=MatchResponse)
async def get_match_result(match_id: str, db=Depends(get_db)):
    """
    Get results of an async match job
    """
    from ...models.database import ProcessingTask, MatchResult, JobDescriptionDB, Resume
    from ...models.schemas import ResumeSummary, PersonalInfo
    
    task = db.query(ProcessingTask).filter(ProcessingTask.id == match_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Match not found")
    
    if task.status != MatchStatus.COMPLETED.value:
        raise HTTPException(
            status_code=202,
            detail=f"Match still processing. Status: {task.status}"
        )
    
    # Get match results
    match_results = db.query(MatchResult).filter(
        MatchResult.job_id == task.target_id
    ).order_by(MatchResult.overall_score.desc()).all()
    
    # Get job description
    job_db = db.query(JobDescriptionDB).filter(
        JobDescriptionDB.id == task.target_id
    ).first()
    
    if not job_db:
        raise HTTPException(status_code=404, detail="Job description not found")
    
    # Build response
    results = []
    for mr in match_results:
        resume = db.query(Resume).filter(Resume.id == mr.resume_id).first()
        if resume:
            resume_summary = ResumeSummary(
                id=resume.id,
                filename=resume.original_filename,
                personal_info=PersonalInfo(**resume.personal_info) if resume.personal_info else PersonalInfo(),
                total_skills=len(resume.skills or []),
                total_experience_years=resume.total_experience_years or 0,
                education_level=getattr(resume, "education_level", "bachelors"),
                status=resume.status,
                created_at=resume.created_at
            )
            
            results.append(ResumeMatchResult(
                resume_id=mr.resume_id,
                resume_summary=resume_summary,
                overall_score=mr.overall_score,
                skill_match_score=mr.skill_match_score,
                experience_match_score=mr.experience_match_score,
                education_match_score=mr.education_match_score,
                semantic_similarity=mr.semantic_similarity,
                match_components=mr.match_components,
                matched_skills=mr.matched_skills,
                missing_skills=mr.missing_skills,
                recommendation=mr.recommendation,
                explanation=mr.explanation
            ))
    
    job_description = JobDescription(
        title=job_db.title,
        company=job_db.company,
        description=job_db.description_text,
        required_skills=job_db.required_skills or [],
        preferred_skills=job_db.preferred_skills or [],
        min_experience_years=job_db.min_experience or 0,
        max_experience_years=job_db.max_experience,
        location=None,
        employment_type=None
    )
    
    return MatchResponse(
        match_id=match_id,
        job_description=job_description,
        results=results,
        total_matches=len(results),
        processing_time_ms=0,
        timestamp=datetime.now()
    )



@router.post("/for-job/{job_id}", response_model=MatchResponse)
async def match_resumes_for_job(
    job_id: str,
    top_k: int = 10,
    min_score_threshold: float = 0.5,
    db=Depends(get_db),
    matcher=Depends(get_matcher),
    embedder=Depends(get_embedder)
):
    """
    EMPLOYER ENDPOINT: Get candidate matches for a specific job
    
    This is the main endpoint employers use to see ranked candidates
    """
    from ...models.database import JobDescriptionDB, Resume
    from ...models.schemas import PersonalInfo, ParsedResume
    
    start_time = datetime.now()
    
    # Get job description
    job_db = db.query(JobDescriptionDB).filter(JobDescriptionDB.id == job_id).first()
    if not job_db:
        raise HTTPException(status_code=404, detail="Job description not found")
    
    # Convert to JobDescription object
    job = JobDescription(
        title=job_db.title,
        company=job_db.company,
        description=job_db.description_text,
        required_skills=job_db.required_skills or [],
        preferred_skills=job_db.preferred_skills or [],
        min_experience_years=job_db.min_experience or 0,
        max_experience_years=job_db.max_experience,
        education_requirement=EducationLevel(job_db.education_requirement) if job_db.education_requirement else None
    )
    
    # Get all processed resumes
    resumes_data = db.query(Resume).filter(Resume.status == "completed").all()
    
    if not resumes_data:
        raise HTTPException(status_code=404, detail="No resumes found in database")
    
    # Convert to Pydantic models
    resumes = []
    for r in resumes_data:
        resume = ParsedResume(
            id=r.id,
            filename=r.original_filename,
            text=r.text,
            personal_info=PersonalInfo(**r.personal_info) if r.personal_info else PersonalInfo(),
            skills=r.skills or [],
            education=r.education or [],
            experience=r.experience or [],
            total_experience_years=r.total_experience_years or 0,
            education_level=getattr(r, "education_level", "bachelors"),
            languages=r.languages or [],
            certifications=r.certifications or [],
            status=r.status,
            created_at=r.created_at,
            updated_at=r.updated_at
        )
        resumes.append(resume)
    
    # Perform matching
    results = await matcher.match_batch(
        resumes=resumes,
        job=job,
        top_k=top_k,
        min_score=min_score_threshold
    )
    
    # Store match results in database for audit/history
    from ...models.database import MatchResult
    for result in results:
        existing = db.query(MatchResult).filter(
            MatchResult.resume_id == str(result.resume_id),
            MatchResult.job_id == job_id
        ).first()
        
        if not existing:
            match_record = MatchResult(
                id=str(uuid4()),
                resume_id=str(result.resume_id),
                job_id=job_id,
                overall_score=result.overall_score,
                skill_match_score=result.skill_match_score,
                experience_match_score=result.experience_match_score,
                education_match_score=result.education_match_score,
                semantic_similarity=result.semantic_similarity,
                matched_skills=result.matched_skills,
                missing_skills=result.missing_skills,
                recommendation=result.recommendation,
                explanation=result.explanation
            )
            db.add(match_record)
    
    db.commit()
    
    processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
    
    return MatchResponse(
        match_id=str(uuid4()),
        job_description=job,
        results=results,
        total_matches=len(results),
        processing_time_ms=processing_time_ms,
        timestamp=datetime.now()
    )



@router.get("/all-jobs-matches")
async def get_matches_for_all_jobs(
    db=Depends(get_db),
    matcher=Depends(get_matcher),
    embedder=Depends(get_embedder)
):
    """Get match scores for all resumes against all jobs"""
    from ...models.database import JobDescriptionDB, Resume
    from ...models.schemas import JobDescription, ParsedResume, PersonalInfo
    
    # Get all jobs
    jobs_db = db.query(JobDescriptionDB).all()
    jobs = []
    for j in jobs_db:
        job = JobDescription(
            title=j.title,
            company=j.company,
            description=j.description_text,
            required_skills=j.required_skills or [],
            preferred_skills=j.preferred_skills or [],
            min_experience_years=j.min_experience or 0
        )
        jobs.append({"id": j.id, "job": job})
    
    # Get all resumes
    resumes_data = db.query(Resume).filter(Resume.status == "completed").all()
    resumes = []
    for r in resumes_data:
        resume = ParsedResume(
            id=r.id,
            filename=r.original_filename,
            text=r.text,
            personal_info=PersonalInfo(**r.personal_info) if r.personal_info else PersonalInfo(),
            skills=r.skills or [],
            education=r.education or [],
            experience=r.experience or [],
            total_experience_years=r.total_experience_years or 0,
            education_level=r.education_level,
            languages=r.languages or [],
            certifications=r.certifications or [],
            status=r.status,
            created_at=r.created_at,
            updated_at=r.updated_at
        )
        resumes.append(resume)
    
    # Calculate all matches
    results = {}
    for job_info in jobs:
        job_matches = await matcher.match_batch(
            resumes=resumes,
            job=job_info["job"],
            top_k=len(resumes),
            min_score=0
        )
        results[job_info["id"]] = {
            "title": job_info["job"].title,
            "matches": [
                {
                    "candidate": m.resume_summary.personal_info.name,
                    "score": m.overall_score,
                    "recommendation": m.recommendation
                }
                for m in job_matches
            ]
        }
    
    return results