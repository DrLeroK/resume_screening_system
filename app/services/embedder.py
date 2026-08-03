"""
Text embedding service using Sentence Transformers
"""

import asyncio
from typing import List, Union, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
import os
import sys

from ..config import settings
from ..core.exceptions import EmbeddingError

class TextEmbedder:
    """Generate embeddings for text using transformer models"""
    
    def __init__(self):
        self.model = None
        self.model_name = settings.embedding_model
        self.batch_size = settings.batch_embedding_size
        self._load_model()
        
    def _load_model(self):
        """Load the sentence transformer model with proper error handling"""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            
            # Set cache directory
            cache_dir = settings.models_cache_dir
            os.makedirs(cache_dir, exist_ok=True)
            
            # Try to load from cache first, then download if needed
            self.model = SentenceTransformer(
                self.model_name,
                cache_folder=cache_dir,
                device='cpu'  # Force CPU to avoid GPU issues
            )
            
            # Get embedding dimension
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded successfully. Embedding dimension: {self.embedding_dim}")
            
        except Exception as e:
            logger.error(f"Failed to load embedding model: {str(e)}")
            # Don't raise - allow system to continue with fallback
            self.embedding_dim = 384  # Default for MiniLM
            logger.warning("Using fallback mode - embeddings will be zeros")
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5)
    )
    async def embed(self, text: str) -> np.ndarray:
        """Generate embedding for a single text"""
        if not text or len(text.strip()) < 10:
            logger.warning("Text too short for embedding")
            return np.zeros(self.embedding_dim)
        
        # If model failed to load, return zeros
        if self.model is None:
            logger.warning("Model not loaded, returning zero embedding")
            return np.zeros(self.embedding_dim)
        
        try:
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, 
                lambda: self.model.encode(text, normalize_embeddings=True)
            )
            return embedding
            
        except Exception as e:
            logger.error(f"Embedding failed: {str(e)}")
            return np.zeros(self.embedding_dim)
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5)
    )
    async def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts in batch"""
        if not texts:
            return []
        
        # If model failed to load, return zeros
        if self.model is None:
            logger.warning("Model not loaded, returning zero embeddings")
            return [np.zeros(self.embedding_dim) for _ in texts]
        
        valid_texts = [t for t in texts if t and len(t.strip()) >= 10]
        if not valid_texts:
            return [np.zeros(self.embedding_dim) for _ in texts]
        
        try:
            loop = asyncio.get_event_loop()
            
            all_embeddings = []
            for i in range(0, len(valid_texts), self.batch_size):
                batch = valid_texts[i:i + self.batch_size]
                batch_embeddings = await loop.run_in_executor(
                    None,
                    lambda b=batch: self.model.encode(
                        b, 
                        normalize_embeddings=True,
                        show_progress_bar=False
                    )
                )
                all_embeddings.extend(batch_embeddings)
            
            result = []
            text_idx = 0
            for original_text in texts:
                if original_text and len(original_text.strip()) >= 10:
                    result.append(all_embeddings[text_idx])
                    text_idx += 1
                else:
                    result.append(np.zeros(self.embedding_dim))
            
            return result
            
        except Exception as e:
            logger.error(f"Batch embedding failed: {str(e)}")
            return [np.zeros(self.embedding_dim) for _ in texts]
    
    async def embed_job_description(self, job_text: str) -> np.ndarray:
        """Specialized embedding for job descriptions"""
        if self.model is None:
            return np.zeros(self.embedding_dim)
        
        sections = {
            'title': self._extract_section(job_text, 'title'),
            'description': job_text,
            'requirements': self._extract_section(job_text, 'requirements'),
            'responsibilities': self._extract_section(job_text, 'responsibilities')
        }
        
        weighted_text = f"""
        Title: {sections['title']}
        Requirements: {sections['requirements']}
        Responsibilities: {sections['responsibilities']}
        Full Description: {sections['description']}
        """
        
        return await self.embed(weighted_text)
    
    def _extract_section(self, text: str, section_type: str) -> str:
        """Extract specific section from job description"""
        text_lower = text.lower()
        
        if section_type == 'title':
            lines = text.split('\n')[:5]
            for line in lines:
                if len(line.strip()) > 5 and len(line.strip()) < 100:
                    return line.strip()
            return ""
        
        elif section_type == 'requirements':
            patterns = [
                r'(?:requirements?|qualifications?|need|must have)[:\s]*(.+?)(?=(?:preferred|bonus|responsibilities|$))',
                r'(?:required skills?)[:\s]*(.+?)(?=\n\n|\Z)'
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    return match.group(1)[:2000]
            return ""
        
        elif section_type == 'responsibilities':
            patterns = [
                r'(?:responsibilities?|what you\'ll do|role)[:\s]*(.+?)(?=(?:requirements?|qualifications?|preferred|$))',
                r'(?:key responsibilities?)[:\s]*(.+?)(?=\n\n|\Z)'
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    return match.group(1)[:2000]
            return ""
        
        return ""
    
    async def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings"""
        if embedding1 is None or embedding2 is None:
            return 0.0
        
        try:
            similarity = np.dot(embedding1, embedding2)
            return float(np.clip(similarity, 0, 1))
        except:
            return 0.0
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings"""
        return self.embedding_dim

# Add missing import
import re
