"""
Information Extractor - Complete Fixed Version
"""

import re
import asyncio
from typing import List, Dict, Any, Optional
from loguru import logger
import spacy

from ..config import settings
from ..models.enums import SkillType, EducationLevel

class InformationExtractor:
    """Extract structured information from resume text"""
    
    TECHNICAL_SKILLS = {
        'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust',
        'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'spring',
        'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform',
        'sql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
        'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy',
        'git', 'jenkins', 'github actions', 'ci/cd', 'fastapi'
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
            self.nlp = spacy.load("en_core_web_lg")
            logger.info("✓ spaCy model 'en_core_web_lg' loaded successfully")
        except OSError:
            logger.warning("en_core_web_lg not found, downloading...")
            spacy.cli.download("en_core_web_lg")
            self.nlp = spacy.load("en_core_web_lg")
            logger.info("✓ spaCy model downloaded and loaded")
        except Exception as e:
            logger.error(f"Failed to load spaCy: {e}")
            self.nlp = None
    
    async def extract(self, text: str) -> Dict[str, Any]:
        """Extract all information from resume text"""
        if not text or not isinstance(text, str):
            logger.error("Invalid text input")
            return self._empty_result()
        
        if len(text.strip()) < 50:
            logger.warning(f"Text too short: {len(text)} chars")
            return self._empty_result()
        
        try:
            skills = await self._extract_skills(text)
            education = await self._extract_education(text)
            experience = await self._extract_experience(text)
            personal_info = await self._extract_personal_info(text)
            
            total_experience = self._calculate_total_experience(experience)
            education_level = self._determine_education_level(education)
            languages = await self._extract_languages(text)
            certifications = await self._extract_certifications(text)
            
            result = {
                "skills": skills,
                "education": education,
                "experience": experience,
                "personal_info": personal_info,
                "total_experience_years": total_experience,
                "education_level": education_level,
                "languages": languages,
                "certifications": certifications
            }
            
            logger.info(f"Extraction complete: {len(skills)} skills, {len(experience)} experiences")
            return result
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return self._empty_result()
    
    async def _extract_skills(self, text: str) -> List[Dict]:
        """Extract skills from text"""
        skills = []
        text_lower = text.lower()
        
        for skill in self.TECHNICAL_SKILLS:
            if skill in text_lower:
                skills.append({
                    "name": skill,
                    "type": SkillType.TECHNICAL.value,
                    "confidence": 0.9,
                    "context": self._find_context(text, skill)
                })
        
        for skill in self.SOFT_SKILLS:
            if skill in text_lower:
                skills.append({
                    "name": skill,
                    "type": SkillType.SOFT.value,
                    "confidence": 0.7,
                    "context": self._find_context(text, skill)
                })
        
        seen = set()
        unique = []
        for s in skills:
            if s["name"] not in seen:
                seen.add(s["name"])
                unique.append(s)
        
        return unique[:50]
    
    async def _extract_education(self, text: str) -> List[Dict]:
        """Extract education information"""
        education = []
        text_lower = text.lower()
        
        patterns = [
            (r'bachelor|b\.?s\.?|b\.?a\.?', 'bachelors', 0.8),
            (r'master|m\.?s\.?|m\.?a\.?|mba', 'masters', 0.8),
            (r'ph\.?d\.?|doctorate', 'phd', 0.9),
            (r'associate|a\.?s\.?|a\.?a\.?', 'associate', 0.7)
        ]
        
        for pattern, level, confidence in patterns:
            if re.search(pattern, text_lower):
                institution = "Unknown"
                uni_pattern = r'(?:at|from|of)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+University|\s+College|\s+Institute))'
                uni_match = re.search(uni_pattern, text, re.IGNORECASE)
                if uni_match:
                    institution = uni_match.group(1)
                
                education.append({
                    "degree": pattern.replace('|', '/'),
                    "institution": institution,
                    "field_of_study": None,
                    "graduation_year": None,
                    "level": level,
                    "confidence": confidence
                })
                break
        
        return education[:3]
    
    async def _extract_experience(self, text: str) -> List[Dict]:
        """Extract work experience"""
        experiences = []
        
        exp_patterns = [
            r'(\d+)\+?\s*years?\s+of\s+experience',
            r'(\d+)\s*\+\s*years?\s+experience',
            r'(\d+)\s*years?\s+of\s+professional\s+experience'
        ]
        
        total_years = 0
        for pattern in exp_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                total_years = int(match.group(1))
                logger.info(f"Found {total_years} years experience from text")
                break
        
        date_pattern = r'(\d{4})\s*[-–]\s*(\d{4}|present|current)'
        matches = re.findall(date_pattern, text, re.IGNORECASE)
        
        calculated_total = 0
        for match in matches:
            try:
                start_year = int(match[0])
                end_text = match[1].lower()
                end_year = 2024 if end_text in ['present', 'current'] else int(end_text)
                duration = end_year - start_year
                
                if 0 < duration < 50:
                    calculated_total += duration
                    experiences.append({
                        "title": "Professional Experience",
                        "company": "Unknown Company",
                        "start_date": str(start_year),
                        "end_date": "Present" if end_text in ['present', 'current'] else str(end_year),
                        "duration_years": duration,
                        "description": "",
                        "responsibilities": [],
                        "achievements": [],
                        "confidence": 0.7
                    })
            except:
                continue
        
        if total_years > calculated_total:
            if experiences:
                experiences[0]["duration_years"] = total_years
            else:
                experiences.append({
                    "title": "Professional Experience",
                    "company": "Various Companies",
                    "start_date": str(2024 - total_years),
                    "end_date": "Present",
                    "duration_years": total_years,
                    "description": "",
                    "responsibilities": [],
                    "achievements": [],
                    "confidence": 0.6
                })
        
        return experiences[:10]
    
    async def _extract_personal_info(self, text: str) -> Dict:
        """Extract personal information - COMPLETELY FIXED VERSION"""
        info = {
            "name": None,
            "email": None,
            "phone": None,
            "location": None,
            "linkedin": None,
            "github": None
        }
        
        # Extract email first
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, text)
        if email_match:
            info["email"] = email_match.group(0)
        
        # Split into lines for name extraction
        lines = text.split('\n')
        
        # Words that indicate a line is a section header (not a name)
        header_words = [
            'SUMMARY', 'EXPERIENCE', 'EDUCATION', 'SKILLS', 'TECHNICAL', 
            'PROJECTS', 'CERTIFICATIONS', 'CONTACT', 'WORK', 'PROFILE',
            'EMPLOYMENT', 'QUALIFICATIONS', 'COMPETENCIES', 'OBJECTIVE',
            'TECHNICAL SKILLS', 'SOFT SKILLS', 'CORE COMPETENCIES',
            'PERSONAL', 'DETAILS', 'INFORMATION', 'ABOUT', 'ME'
        ]
        
        for line in lines[:20]:
            line = line.strip()
            if not line:
                continue
            
            line_upper = line.upper()
            
            # CRITICAL: Skip exact section headers
            if line_upper in header_words:
                continue
            
            # Skip any line that is all caps and longer than 10 chars
            if line.isupper() and len(line) > 10:
                continue
            
            # Skip lines containing header words
            skip = False
            for word in header_words:
                if word in line_upper and len(word) > 5:
                    skip = True
                    break
            if skip:
                continue
            
            # Skip lines with email or phone
            if '@' in line:
                continue
            if re.search(r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}', line):
                continue
            
            # Name should be 2-4 words, appropriate length
            words = line.split()
            if 2 <= len(words) <= 4 and 10 <= len(line) <= 60:
                # Check if all words start with capital letter
                if all(w[0].isupper() for w in words if w):
                    # No digits allowed in name
                    if not any(c.isdigit() for c in line):
                        # Additional check: name shouldn't contain common skill words
                        skill_check_words = ['PYTHON', 'JAVA', 'AWS', 'DOCKER', 'KUBERNETES']
                        if not any(word.upper() in skill_check_words for word in words):
                            info["name"] = line
                            logger.info(f"Extracted name: {line}")
                            break
        
        # Fallback: look for line before email
        if not info["name"] and info["email"]:
            email_pos = text.find(info["email"])
            if email_pos > 0:
                before_text = text[:email_pos]
                before_lines = before_text.strip().split('\n')
                if before_lines:
                    potential_name = before_lines[-1].strip()
                    if potential_name and len(potential_name) < 60:
                        words = potential_name.split()
                        if 2 <= len(words) <= 4:
                            info["name"] = potential_name
                            logger.info(f"Email-relative name: {potential_name}")
        
        # Extract phone
        phone_pattern = r'\b(\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})\b'
        phone_match = re.search(phone_pattern, text)
        if phone_match:
            info["phone"] = phone_match.group(0)
        
        # Extract location
        location_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z]{2})\b'
        location_match = re.search(location_pattern, text)
        if location_match:
            info["location"] = f"{location_match.group(1)}, {location_match.group(2)}"
        
        return info
    
    async def _extract_languages(self, text: str) -> List[str]:
        """Extract languages"""
        languages = []
        lang_list = ['english', 'spanish', 'french', 'german', 'chinese', 'japanese']
        text_lower = text.lower()
        
        for lang in lang_list:
            if lang in text_lower:
                languages.append(lang.capitalize())
        
        return languages[:5]
    
    async def _extract_certifications(self, text: str) -> List[str]:
        """Extract certifications"""
        certifications = []
        cert_patterns = [
            (r'aws certified', 'AWS Certified'),
            (r'azure certified', 'Azure Certified'),
            (r'scrum master', 'Scrum Master'),
            (r'pmp', 'PMP'),
            (r'kubernetes', 'Kubernetes Certified'),
            (r'tensorflow', 'TensorFlow Certified')
        ]
        
        text_lower = text.lower()
        for pattern, name in cert_patterns:
            if re.search(pattern, text_lower):
                certifications.append(name)
        
        return list(set(certifications))[:10]
    
    def _calculate_total_experience(self, experiences: List[Dict]) -> float:
        total = 0
        for exp in experiences:
            duration = exp.get('duration_years', 0)
            if duration:
                total += duration
        return round(total, 1)
    
    def _determine_education_level(self, education: List[Dict]) -> str:
        priority = {'phd': 4, 'masters': 3, 'bachelors': 2, 'associate': 1}
        highest = 'unknown'
        highest_score = 0
        
        for edu in education:
            level = edu.get('level', 'unknown')
            score = priority.get(level, 0)
            if score > highest_score:
                highest_score = score
                highest = level
        
        return highest if highest != 'unknown' else 'bachelors'
    
    def _find_context(self, text: str, keyword: str, window: int = 100) -> Optional[str]:
        index = text.lower().find(keyword.lower())
        if index != -1:
            start = max(0, index - window)
            end = min(len(text), index + len(keyword) + window)
            context = text[start:end].replace('\n', ' ').strip()
            return context if len(context) < 200 else context[:200]
        return None
    
    def _empty_result(self) -> Dict[str, Any]:
        return {
            "skills": [],
            "education": [],
            "experience": [],
            "personal_info": {
                "name": None, "email": None, "phone": None,
                "location": None, "linkedin": None, "github": None
            },
            "total_experience_years": 0,
            "education_level": "unknown",
            "languages": [],
            "certifications": []
        }
    
    async def extract_job_requirements(self, job_description: str) -> Dict[str, Any]:
        requirements = {'skills': [], 'min_experience': 0, 'education': None}
        
        text_lower = job_description.lower()
        
        for skill in self.TECHNICAL_SKILLS:
            if skill in text_lower:
                requirements['skills'].append(skill)
                if len(requirements['skills']) >= 20:
                    break
        
        exp_pattern = r'(\d+)\+?\s*years?'
        exp_match = re.search(exp_pattern, job_description)
        if exp_match:
            requirements['min_experience'] = int(exp_match.group(1))
        
        return requirements
