"""
Fixed Information Extractor - Copy this to extractor.py
"""

import re
import asyncio
from typing import List, Dict, Any, Optional
from collections import Counter
from loguru import logger
import spacy

from ..config import settings
from ..models.enums import SkillType, ExperienceLevel, EducationLevel
from ..core.exceptions import ExtractionError

class InformationExtractor:
    """Extract structured information from resume text"""
    
    TECHNICAL_SKILLS = {
        'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust',
        'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'spring',
        'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform',
        'sql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
        'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy',
        'git', 'jenkins', 'github actions', 'ci/cd',
        'rest api', 'graphql', 'grpc', 'microservices', 'fastapi'
    }
    
    SOFT_SKILLS = {
        'leadership', 'communication', 'teamwork', 'problem solving',
        'critical thinking', 'time management', 'adaptability', 'creativity',
        'collaboration', 'project management', 'agile', 'scrum'
    }
    
    def __init__(self):
        self.nlp = None
        self._load_model()
        
    def _load_model(self):
        """Load spaCy model"""
        try:
            self.nlp = spacy.load(settings.ner_model)
            logger.info(f"Loaded spaCy model: {settings.ner_model}")
        except OSError:
            logger.warning(f"Could not load {settings.ner_model}, downloading...")
            spacy.cli.download(settings.ner_model_fallback)
            self.nlp = spacy.load(settings.ner_model_fallback)
            logger.info(f"Loaded fallback model: {settings.ner_model_fallback}")
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {str(e)}")
            self.nlp = None
    
    async def extract(self, text: str) -> Dict[str, Any]:
        """Extract all information from resume text"""
        
        # Validate input
        if not text or not isinstance(text, str):
            logger.error("Invalid text input for extraction")
            return self._empty_result()
        
        if len(text.strip()) < 50:
            logger.warning(f"Text too short: {len(text)} characters")
            return self._empty_result()
        
        try:
            # Process with spaCy
            doc = None
            if self.nlp:
                doc = await self._process_text(text)
            
            if doc is None:
                # Fallback to regex-only extraction
                return await self._regex_only_extraction(text)
            
            # Extract components
            skills = await self._extract_skills(doc, text)
            education = await self._extract_education(doc, text)
            experience = await self._extract_experience(doc, text)
            personal_info = await self._extract_personal_info(doc, text)
            
            total_experience = self._calculate_total_experience(experience)
            education_level = self._determine_education_level(education)
            languages = await self._extract_languages(text)
            certifications = await self._extract_certifications(text)
            
            return {
                "skills": skills,
                "education": education,
                "experience": experience,
                "personal_info": personal_info,
                "total_experience_years": total_experience,
                "education_level": education_level,
                "languages": languages,
                "certifications": certifications
            }
            
        except Exception as e:
            logger.error(f"Extraction failed: {str(e)}")
            return self._empty_result()
    
    async def _regex_only_extraction(self, text: str) -> Dict[str, Any]:
        """Fallback extraction using only regex patterns"""
        text_lower = text.lower()
        
        # Extract name (first few lines)
        lines = text.split('\n')[:10]
        name = None
        for line in lines:
            if len(line.strip()) > 5 and len(line.strip()) < 50:
                words = line.strip().split()
                if 2 <= len(words) <= 4:
                    name = line.strip()
                    break
        
        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, text)
        email = email_match.group(0) if email_match else None
        
        # Extract skills
        skills = []
        for skill in self.TECHNICAL_SKILLS:
            if skill in text_lower:
                skills.append({"name": skill, "type": "technical", "confidence": 0.8, "context": None})
        
        # Extract years of experience
        exp_pattern = r'(\d+)\+?\s*years?'
        exp_match = re.search(exp_pattern, text)
        total_experience = int(exp_match.group(1)) if exp_match else 0
        
        return {
            "skills": skills[:50],
            "education": [],
            "experience": [],
            "personal_info": {"name": name, "email": email, "phone": None, "location": None, "linkedin": None, "github": None},
            "total_experience_years": total_experience,
            "education_level": "unknown",
            "languages": [],
            "certifications": []
        }
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result"""
        return {
            "skills": [],
            "education": [],
            "experience": [],
            "personal_info": {"name": None, "email": None, "phone": None, "location": None, "linkedin": None, "github": None},
            "total_experience_years": 0,
            "education_level": "unknown",
            "languages": [],
            "certifications": []
        }
    
    async def _process_text(self, text: str):
        """Process text with spaCy"""
        def process():
            try:
                if not text or len(text.strip()) == 0:
                    return None
                if len(text) > 100000:
                    text = text[:100000]
                return self.nlp(text)
            except Exception as e:
                logger.error(f"SpaCy processing error: {str(e)}")
                return None
        
        return await asyncio.get_event_loop().run_in_executor(None, process)
    
    async def _extract_skills(self, doc, text: str) -> List[Dict]:
        """Extract skills"""
        skills = []
        if not text:
            return skills
        
        text_lower = text.lower()
        for skill in self.TECHNICAL_SKILLS:
            if skill in text_lower:
                skills.append({"name": skill, "type": "technical", "confidence": 0.9, "context": None})
        
        # Remove duplicates
        seen = set()
        unique = []
        for s in skills:
            if s["name"] not in seen:
                seen.add(s["name"])
                unique.append(s)
        return unique[:50]
    
    async def _extract_education(self, doc, text: str) -> List[Dict]:
        """Extract education"""
        education = []
        degree_patterns = [
            r'(bachelor|b\.?a\.?|b\.?s\.?)',
            r'(master|m\.?a\.?|m\.?s\.?|mba)',
            r'(ph\.?d\.?|doctorate)'
        ]
        text_lower = text.lower()
        for pattern in degree_patterns:
            if re.search(pattern, text_lower):
                education.append({"degree": pattern, "institution": "Unknown", "level": "unknown", "confidence": 0.6})
        return education[:5]
    
    async def _extract_experience(self, doc, text: str) -> List[Dict]:
        """Extract experience"""
        experiences = []
        exp_pattern = r'(\d{4})\s*[-–]\s*(\d{4}|present)'
        matches = re.findall(exp_pattern, text, re.IGNORECASE)
        
        for match in matches:
            try:
                start = int(match[0])
                end = 2024 if match[1].lower() == 'present' else int(match[1])
                duration = end - start
                if duration > 0:
                    experiences.append({
                        "title": "Unknown Position",
                        "company": "Unknown Company",
                        "duration_years": duration,
                        "confidence": 0.5
                    })
            except:
                pass
        
        return experiences[:10]
    
    async def _extract_personal_info(self, doc, text: str) -> Dict:
        """Extract personal info"""
        info = {"name": None, "email": None, "phone": None, "location": None, "linkedin": None, "github": None}
        
        # Extract name
        lines = text.split('\n')[:10]
        for line in lines:
            if len(line.strip()) > 5 and len(line.strip()) < 50:
                words = line.strip().split()
                if 2 <= len(words) <= 4:
                    info["name"] = line.strip()
                    break
        
        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, text)
        if email_match:
            info["email"] = email_match.group(0)
        
        return info
    
    async def _extract_languages(self, text: str) -> List[str]:
        """Extract languages"""
        languages = []
        lang_list = ['english', 'spanish', 'french', 'german', 'chinese', 'japanese']
        text_lower = text.lower()
        for lang in lang_list:
            if lang in text_lower:
                languages.append(lang)
        return languages
    
    async def _extract_certifications(self, text: str) -> List[str]:
        """Extract certifications"""
        certs = []
        cert_patterns = [r'certified', r'certification', r'aws certified', r'scrum', r'pmp']
        text_lower = text.lower()
        for pattern in cert_patterns:
            if re.search(pattern, text_lower):
                certs.append(pattern)
        return list(set(certs))
    
    def _calculate_total_experience(self, experiences: List[Dict]) -> float:
        """Calculate total years of experience"""
        total = 0
        for exp in experiences:
            if exp.get('duration_years'):
                total += exp['duration_years']
        return round(total, 1)
    
    def _determine_education_level(self, education: List[Dict]) -> str:
        """Determine highest education level"""
        levels = {'phd': 4, 'master': 3, 'bachelor': 2, 'high_school': 1}
        highest = "unknown"
        highest_score = 0
        
        for edu in education:
            degree = edu.get('degree', '').lower()
            for level, score in levels.items():
                if level in degree and score > highest_score:
                    highest_score = score
                    highest = level
        
        return highest if highest != "unknown" else "bachelors"
    
    def _find_context(self, text: str, keyword: str, window: int = 100) -> Optional[str]:
        """Find context around keyword"""
        index = text.lower().find(keyword.lower())
        if index != -1:
            start = max(0, index - window)
            end = min(len(text), index + len(keyword) + window)
            return text[start:end]
        return None
    
    async def extract_job_requirements(self, job_description: str) -> Dict[str, Any]:
        """Extract requirements from job description"""
        requirements = {'skills': [], 'min_experience': 0, 'education': None}
        
        text_lower = job_description.lower()
        for skill in self.TECHNICAL_SKILLS:
            if skill in text_lower:
                requirements['skills'].append(skill)
        
        exp_pattern = r'(\d+)\+?\s*years?'
        exp_match = re.search(exp_pattern, job_description)
        if exp_match:
            requirements['min_experience'] = int(exp_match.group(1))
        
        return requirements
