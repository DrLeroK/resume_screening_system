"""
Resume upload endpoints
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from typing import List, Optional 
from uuid import uuid4
from pathlib import Path
from datetime import datetime
import aiofiles
from loguru import logger

from ...models.schemas import ResumeUploadResponse, ResumeSummary, ParsedResume
from ...models.enums import ResumeStatus
from ...config import settings
from ...core.task_manager import task_manager
from ...dependencies import get_db, get_parser, get_extractor, get_embedder, get_searcher

router = APIRouter(prefix="/resumes", tags=["Resume Management"])

@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db=Depends(get_db),
    parser=Depends(get_parser),
    extractor=Depends(get_extractor),
    embedder=Depends(get_embedder),
    searcher=Depends(get_searcher)
):
    """
    Upload a resume file for processing
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(settings.allowed_extensions)}"
        )
    
    # Generate unique ID
    resume_id = str(uuid4())
    file_path = settings.upload_dir / f"{resume_id}{file_ext}"
    
    # Save file
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
    except Exception as e:
        logger.error(f"Failed to save file: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")
    
    # Create database record
    from ...models.database import Resume
    resume = Resume(
        id=resume_id,
        filename=f"{resume_id}{file_ext}",
        original_filename=file.filename,
        file_size_bytes=len(content),
        status=ResumeStatus.PENDING.value
    )
    db.add(resume)
    db.commit()
    
    # Schedule background processing
    task_manager.add_task(
        task_id=resume_id,
        task_type="parse_resume",
        func=process_resume,
        args=(resume_id, file_path, file.filename, file_ext),
        kwargs={}
    )
    
    return ResumeUploadResponse(
        resume_id=resume_id,
        filename=file.filename,
        status=ResumeStatus.PENDING,
        message="Resume uploaded successfully. Processing in background.",
        created_at=resume.created_at
    )

async def process_resume(resume_id: str, file_path: Path, original_filename: str, file_ext: str):
    """
    Background task to process uploaded resume
    """
    from ...models.database import Resume, get_session
    from ...services.parser import DocumentParser
    from ...services.extractor import InformationExtractor
    from ...services.embedder import TextEmbedder
    from ...services.searcher import FAISSSearcher
    from datetime import datetime
    
    db = get_session()
    
    try:
        # Update status
        db.query(Resume).filter(Resume.id == resume_id).update({"status": ResumeStatus.PROCESSING.value})
        db.commit()
        
        # Parse document
        parser = DocumentParser()
        text, doc_type, file_hash = await parser.parse(file_path, original_filename)
        
        # Extract information
        extractor = InformationExtractor()
        extracted_data = await extractor.extract(text)
        
        # Generate embedding
        embedder = TextEmbedder()
        embedding = await embedder.embed(text)
        
        # Add to search index
        searcher = FAISSSearcher(embedder.get_embedding_dimension())
        await searcher.add_vector(resume_id, embedding)
        
        # Update database with extracted data
        update_data = {
            "status": ResumeStatus.COMPLETED.value,
            "text": text,
            "file_hash": file_hash,
            "personal_info": extracted_data["personal_info"],
            "skills": extracted_data["skills"],
            "education": extracted_data["education"],
            "experience": extracted_data["experience"],
            "total_experience_years": extracted_data["total_experience_years"],
            "languages": extracted_data["languages"],
            "certifications": extracted_data["certifications"],
            "inferred_gender": extracted_data["personal_info"].get("inferred_gender"),
            "inferred_age_group": extracted_data["personal_info"].get("inferred_age_group"),
            "updated_at": datetime.now()
        }
        
        db.query(Resume).filter(Resume.id == resume_id).update(update_data)
        db.commit()
        
        logger.info(f"Successfully processed resume {resume_id}")
        
    except Exception as e:
        logger.error(f"Failed to process resume {resume_id}: {str(e)}")
        db.query(Resume).filter(Resume.id == resume_id).update({
            "status": ResumeStatus.FAILED.value,
            "error_message": str(e)
        })
        db.commit()
    finally:
        db.close()

@router.get("/{resume_id}", response_model=ParsedResume)
async def get_resume(resume_id: str, db=Depends(get_db)):
    """
    Get parsed resume by ID
    """
    from ...models.database import Resume
    from ...models.schemas import PersonalInfo
    from ...models.enums import EducationLevel
    
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # SAFELY get attributes
    edu_level = getattr(resume, 'education_level', 'unknown')
    if edu_level is None:
        edu_level = "unknown"
    
    # Convert to enum
    try:
        education_level_enum = EducationLevel(edu_level)
    except ValueError:
        education_level_enum = EducationLevel.UNKNOWN
    
    # Parse personal info
    personal_info_data = resume.personal_info or {}
    if isinstance(personal_info_data, str):
        import json
        try:
            personal_info_data = json.loads(personal_info_data)
        except:
            personal_info_data = {}
    
    return ParsedResume(
        id=resume.id,
        filename=resume.original_filename,
        text=resume.text or "",
        personal_info=PersonalInfo(**personal_info_data),
        skills=resume.skills or [],
        education=resume.education or [],
        experience=resume.experience or [],
        total_experience_years=resume.total_experience_years or 0,
        education_level=education_level_enum,
        languages=resume.languages or [],
        certifications=resume.certifications or [],
        status=resume.status,
        error_message=resume.error_message,
        created_at=resume.created_at,
        updated_at=resume.updated_at or resume.created_at
    )

@router.get("/", response_model=List[ResumeSummary])
async def list_resumes(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db=Depends(get_db)
):
    """
    List all resumes with pagination
    """
    from ...models.database import Resume
    from ...models.schemas import PersonalInfo
    
    query = db.query(Resume)
    
    if status:
        query = query.filter(Resume.status == status)
    
    resumes = query.order_by(Resume.created_at.desc()).offset(skip).limit(limit).all()
    
    results = []
    for r in resumes:
        # SAFELY get education_level using getattr
        edu_level = getattr(r, 'education_level', 'unknown')
        if edu_level is None:
            edu_level = "unknown"
        
        # Safely parse personal info
        personal_info_data = r.personal_info or {}
        if isinstance(personal_info_data, str):
            import json
            try:
                personal_info_data = json.loads(personal_info_data)
            except:
                personal_info_data = {}
        
        results.append(ResumeSummary(
            id=r.id,
            filename=r.original_filename,
            personal_info=PersonalInfo(**personal_info_data),
            total_skills=len(r.skills or []),
            total_experience_years=r.total_experience_years or 0,
            education_level=edu_level,
            status=r.status,
            created_at=r.created_at
        ))
    
    return results

@router.delete("/{resume_id}")
async def delete_resume(resume_id: str, db=Depends(get_db), searcher=Depends(get_searcher)):
    """
    Delete a resume and remove from search index
    """
    from ...models.database import Resume
    
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Remove from search index
    await searcher.remove_vector(resume_id)
    
    # Delete file
    file_path = settings.upload_dir / resume.filename
    if file_path.exists():
        file_path.unlink()
    
    # Delete from database
    db.delete(resume)
    db.commit()
    
    return {"message": "Resume deleted successfully"}

@router.post("/upload-batch", response_model=List[ResumeUploadResponse])
async def upload_resumes_batch(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None,
    db=Depends(get_db),
    parser=Depends(get_parser),
    extractor=Depends(get_extractor),
    embedder=Depends(get_embedder),
    searcher=Depends(get_searcher)
):
    """
    Upload multiple resumes at once (Bulk Upload)
    """
    from ...models.database import Resume
    
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    results = []
    failed = []
    
    for file in files:
        # Validate file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in settings.allowed_extensions:
            failed.append({
                "filename": file.filename,
                "error": f"Invalid file type. Allowed: {', '.join(settings.allowed_extensions)}"
            })
            continue
        
        try:
            # Generate unique ID
            resume_id = str(uuid4())
            file_path = settings.upload_dir / f"{resume_id}{file_ext}"
            
            # Save file
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            # Create database record
            resume = Resume(
                id=resume_id,
                filename=f"{resume_id}{file_ext}",
                original_filename=file.filename,
                file_size_bytes=len(content),
                status=ResumeStatus.PENDING.value
            )
            db.add(resume)
            db.commit()
            
            # Schedule background processing
            task_manager.add_task(
                task_id=resume_id,
                task_type="parse_resume",
                func=process_resume,
                args=(resume_id, file_path, file.filename, file_ext),
                kwargs={}
            )
            
            results.append(ResumeUploadResponse(
                resume_id=resume_id,
                filename=file.filename,
                status=ResumeStatus.PENDING,
                message="Resume uploaded successfully. Processing in background.",
                created_at=resume.created_at
            ))
            
        except Exception as e:
            logger.error(f"Failed to upload {file.filename}: {str(e)}")
            failed.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    # Return results with summary
    return {
        "successful": len(results),
        "failed": len(failed),
        "results": results,
        "errors": failed if failed else None
    }
