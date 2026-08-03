"""
Semantic search endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
from loguru import logger

from ...models.schemas import SearchQuery, SearchResponse, SearchResult, ResumeSummary
from ...models.enums import EducationLevel
from ...config import settings
from ...dependencies import get_db, get_embedder, get_searcher

router = APIRouter(prefix="/search", tags=["Semantic Search"])

@router.post("/", response_model=SearchResponse)
async def semantic_search(
    query: SearchQuery,
    db=Depends(get_db),
    embedder=Depends(get_embedder),
    searcher=Depends(get_searcher)
):
    from ...models.database import Resume
    
    start_time = datetime.now()
    
    query_embedding = await embedder.embed(query.query)
    search_results = await searcher.search(query_embedding, k=query.top_k)
    
    if not search_results:
        return SearchResponse(
            query=query.query,
            results=[],
            total_results=0,
            processing_time_ms=0
        )
    
    resume_ids = [rid for rid, _ in search_results]
    resumes = db.query(Resume).filter(Resume.id.in_(resume_ids)).all()
    resume_map = {r.id: r for r in resumes}
    
    results = []
    for resume_id, similarity in search_results:
        if resume_id not in resume_map:
            continue
        
        resume = resume_map[resume_id]
        
        if query.skill_filter:
            resume_skills = {s.get('name', '').lower() for s in (resume.skills or [])}
            if not any(skill.lower() in resume_skills for skill in query.skill_filter):
                continue
        
        if query.min_experience and (resume.total_experience_years or 0) < query.min_experience:
            continue
        
        if query.max_experience and (resume.total_experience_years or 0) > query.max_experience:
            continue
        
        if query.education_level:
            edu_level = getattr(resume, 'education_level', 'unknown')
            if edu_level != query.education_level.value:
                continue
        
        from ...models.schemas import PersonalInfo
        personal_info_data = resume.personal_info or {}
        if isinstance(personal_info_data, str):
            import json
            try:
                personal_info_data = json.loads(personal_info_data)
            except:
                personal_info_data = {}
        
        resume_summary = ResumeSummary(
            id=resume.id,
            filename=resume.original_filename,
            personal_info=PersonalInfo(**personal_info_data),
            total_skills=len(resume.skills or []),
            total_experience_years=resume.total_experience_years or 0,
            education_level=getattr(resume, 'education_level', 'unknown'),
            status=resume.status,
            created_at=resume.created_at
        )
        
        query_terms = set(query.query.lower().split())
        resume_skills = {s.get('name', '').lower() for s in (resume.skills or [])}
        matching_skills = list(query_terms & resume_skills)[:5]
        
        explanation = f"Semantic similarity score: {similarity:.2f}. "
        if matching_skills:
            explanation += f"Matches skills: {', '.join(matching_skills)}. "
        
        results.append(SearchResult(
            resume_id=resume_id,
            resume_summary=resume_summary,
            similarity_score=similarity,
            matching_skills=matching_skills,
            relevance_explanation=explanation
        ))
    
    processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
    
    return SearchResponse(
        query=query.query,
        results=results[:query.top_k],
        total_results=len(results),
        processing_time_ms=processing_time_ms
    )

@router.post("/advanced", response_model=SearchResponse)
async def advanced_search(
    query: SearchQuery,
    db=Depends(get_db),
    embedder=Depends(get_embedder),
    searcher=Depends(get_searcher)
):
    from ...models.database import Resume
    
    start_time = datetime.now()
    
    weighted_query = f"""
    Skills: {query.query}
    Experience: min {query.min_experience or 0} years
    Education: {query.education_level.value if query.education_level else 'any'}
    """
    
    query_embedding = await embedder.embed(weighted_query)
    search_results = await searcher.search(query_embedding, k=query.top_k * 2)
    
    if not search_results:
        return SearchResponse(
            query=query.query,
            results=[],
            total_results=0,
            processing_time_ms=0
        )
    
    resume_ids = [rid for rid, _ in search_results]
    resumes = db.query(Resume).filter(Resume.id.in_(resume_ids)).all()
    
    scored_results = []
    for resume_id, semantic_score in search_results:
        resume = next((r for r in resumes if r.id == resume_id), None)
        if not resume:
            continue
        
        field_score = semantic_score
        
        if query.skill_filter:
            resume_skills = {s.get('name', '').lower() for s in (resume.skills or [])}
            skill_matches = sum(1 for s in query.skill_filter if s.lower() in resume_skills)
            skill_bonus = skill_matches / len(query.skill_filter) * 0.3
            field_score += skill_bonus
        
        if query.min_experience and resume.total_experience_years:
            if resume.total_experience_years >= query.min_experience:
                field_score += 0.1
        
        if query.education_level:
            edu_level = getattr(resume, 'education_level', 'unknown')
            if edu_level == query.education_level.value:
                field_score += 0.1
        
        scored_results.append((resume, field_score, semantic_score))
    
    scored_results.sort(key=lambda x: x[1], reverse=True)
    
    from ...models.schemas import PersonalInfo
    results = []
    for resume, final_score, semantic_score in scored_results[:query.top_k]:
        personal_info_data = resume.personal_info or {}
        if isinstance(personal_info_data, str):
            import json
            try:
                personal_info_data = json.loads(personal_info_data)
            except:
                personal_info_data = {}
        
        resume_summary = ResumeSummary(
            id=resume.id,
            filename=resume.original_filename,
            personal_info=PersonalInfo(**personal_info_data),
            total_skills=len(resume.skills or []),
            total_experience_years=resume.total_experience_years or 0,
            education_level=getattr(resume, 'education_level', 'unknown'),
            status=resume.status,
            created_at=resume.created_at
        )
        
        query_terms = set(query.query.lower().split())
        resume_skills = {s.get('name', '').lower() for s in (resume.skills or [])}
        matching_skills = list(query_terms & resume_skills)[:5]
        
        explanation = f"Relevance score: {final_score:.2f} (semantic: {semantic_score:.2f})"
        if matching_skills:
            explanation += f" | Skills matched: {', '.join(matching_skills)}"
        
        results.append(SearchResult(
            resume_id=resume.id,
            resume_summary=resume_summary,
            similarity_score=final_score,
            matching_skills=matching_skills,
            relevance_explanation=explanation
        ))
    
    processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
    
    return SearchResponse(
        query=query.query,
        results=results,
        total_results=len(results),
        processing_time_ms=processing_time_ms
    )
