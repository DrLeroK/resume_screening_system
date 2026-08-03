"""
FAISS-based semantic search service
"""

import numpy as np
import faiss
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import asyncio
import json
from loguru import logger
import pickle

from ..config import settings
from ..core.exceptions import IndexError

class FAISSSearcher:
    """Manages FAISS index for fast similarity search"""
    
    def __init__(self, dimension: int):
        self.dimension = dimension
        self.index = None
        self.id_to_resume_map = {}  # FAISS position -> resume_id
        self.resume_id_to_position = {}  # resume_id -> FAISS position
        self.index_path = settings.faiss_index_path
        
        self._initialize_index()
    
    def _initialize_index(self):
        """Initialize or load existing FAISS index"""
        try:
            if self.index_path.exists() and settings.faiss_memory_mapped:
                # Load existing index with memory mapping
                logger.info(f"Loading existing index from {self.index_path}")
                self.index = faiss.read_index(
                    str(self.index_path), 
                    faiss.IO_FLAG_MMAP
                )
                self._load_mappings()
                logger.info(f"Loaded index with {self.index.ntotal} vectors")
                
            elif self.index_path.exists():
                # Load without memory mapping
                logger.info(f"Loading existing index from {self.index_path}")
                self.index = faiss.read_index(str(self.index_path))
                self._load_mappings()
                logger.info(f"Loaded index with {self.index.ntotal} vectors")
                
            else:
                # Create new index
                logger.info("Creating new FAISS index")
                self._create_new_index()
                
        except Exception as e:
            logger.error(f"Failed to initialize index: {str(e)}")
            # Fall back to new index
            self._create_new_index()
    
    def _create_new_index(self):
        """Create a new FAISS index"""
        # Use inner product for cosine similarity (vectors are normalized)
        self.index = faiss.IndexFlatIP(self.dimension)
        
        # For larger indexes, we could use HNSW
        # self.index = faiss.index_factory(self.dimension, "HNSW32", faiss.METRIC_INNER_PRODUCT)
        
        self.id_to_resume_map = {}
        self.resume_id_to_position = {}
        
        logger.info("Created new FAISS index")
    
    def _load_mappings(self):
        """Load mapping files"""
        mapping_path = self.index_path.parent / "mappings.pkl"
        if mapping_path.exists():
            try:
                with open(mapping_path, 'rb') as f:
                    mappings = pickle.load(f)
                    self.id_to_resume_map = mappings.get('id_to_resume', {})
                    self.resume_id_to_position = mappings.get('resume_to_position', {})
                logger.info(f"Loaded mappings for {len(self.id_to_resume_map)} resumes")
            except Exception as e:
                logger.error(f"Failed to load mappings: {str(e)}")
                self.id_to_resume_map = {}
                self.resume_id_to_position = {}
    
    def _save_mappings(self):
        """Save mapping files"""
        mapping_path = self.index_path.parent / "mappings.pkl"
        try:
            with open(mapping_path, 'wb') as f:
                mappings = {
                    'id_to_resume': self.id_to_resume_map,
                    'resume_to_position': self.resume_id_to_position
                }
                pickle.dump(mappings, f)
            logger.debug(f"Saved mappings to {mapping_path}")
        except Exception as e:
            logger.error(f"Failed to save mappings: {str(e)}")
    
    async def add_vector(self, resume_id: str, embedding: np.ndarray) -> int:
        """
        Add a single vector to the index
        
        Returns:
            Position in the index
        """
        if embedding is None or embedding.shape[0] != self.dimension:
            raise IndexError(f"Invalid embedding dimension. Expected {self.dimension}")
        
        # Check if resume already exists
        if resume_id in self.resume_id_to_position:
            logger.warning(f"Resume {resume_id} already in index, removing first")
            await self.remove_vector(resume_id)
        
        # Reshape to 2D array
        vector = embedding.reshape(1, -1).astype(np.float32)
        
        # Add to index
        position = self.index.ntotal
        self.index.add(vector)
        
        # Update mappings
        self.id_to_resume_map[position] = resume_id
        self.resume_id_to_position[resume_id] = position
        
        # Save mappings
        self._save_mappings()
        
        # Save index periodically (every 100 vectors)
        if position % 100 == 0:
            await self._save_index()
        
        logger.info(f"Added vector for resume {resume_id} at position {position}")
        return position
    
    async def add_vectors_batch(self, resume_embeddings: List[Tuple[str, np.ndarray]]):
        """
        Add multiple vectors in batch
        
        Args:
            resume_embeddings: List of (resume_id, embedding) tuples
        """
        if not resume_embeddings:
            return
        
        vectors = []
        positions = []
        
        for resume_id, embedding in resume_embeddings:
            if embedding.shape[0] != self.dimension:
                logger.error(f"Invalid embedding for {resume_id}, skipping")
                continue
            
            # Check for duplicates
            if resume_id in self.resume_id_to_position:
                await self.remove_vector(resume_id)
            
            vectors.append(embedding.reshape(1, -1).astype(np.float32))
            positions.append(self.index.ntotal + len(vectors) - 1)
        
        if not vectors:
            return
        
        # Batch add
        batch_vectors = np.vstack(vectors)
        self.index.add(batch_vectors)
        
        # Update mappings
        for pos, (resume_id, _) in zip(positions, resume_embeddings[:len(positions)]):
            self.id_to_resume_map[pos] = resume_id
            self.resume_id_to_position[resume_id] = pos
        
        self._save_mappings()
        logger.info(f"Added {len(vectors)} vectors in batch")
        
        # Save index
        await self._save_index()
    
    async def remove_vector(self, resume_id: str):
        """
        Remove a vector from the index
        Note: FAISS doesn't support direct removal, so we rebuild
        """
        if resume_id not in self.resume_id_to_position:
            logger.warning(f"Resume {resume_id} not found in index")
            return
        
        position = self.resume_id_to_position[resume_id]
        
        # Get all vectors except the one to remove
        all_vectors = []
        all_ids = []
        
        for pos, rid in self.id_to_resume_map.items():
            if pos != position:
                # Extract vector (this is expensive - consider rebuilding)
                # For now, we'll rebuild the index
                pass
        
        # Rebuild index without the removed vector
        await self._rebuild_index()
        
        logger.info(f"Removed resume {resume_id} from index")
    
    async def search(self, query_embedding: np.ndarray, k: int = 10) -> List[Tuple[str, float]]:
        """
        Search for similar vectors
        
        Args:
            query_embedding: Query vector
            k: Number of results to return
            
        Returns:
            List of (resume_id, similarity_score) tuples
        """
        if self.index.ntotal == 0:
            return []
        
        if query_embedding.shape[0] != self.dimension:
            raise IndexError(f"Invalid query dimension. Expected {self.dimension}")
        
        # Reshape query
        query = query_embedding.reshape(1, -1).astype(np.float32)
        
        # Search
        k = min(k, self.index.ntotal)
        scores, indices = self.index.search(query, k)
        
        # Map indices to resume IDs
        results = []
        for idx, score in zip(indices[0], scores[0]):
            if idx != -1 and idx in self.id_to_resume_map:
                resume_id = self.id_to_resume_map[idx]
                similarity = float(score)
                results.append((resume_id, similarity))
        
        return results
    
    async def search_batch(self, query_embeddings: List[np.ndarray], k: int = 10) -> List[List[Tuple[str, float]]]:
        """
        Search for multiple queries in batch
        """
        if self.index.ntotal == 0:
            return [[] for _ in query_embeddings]
        
        results = []
        for query in query_embeddings:
            result = await self.search(query, k)
            results.append(result)
        
        return results
    
    async def _rebuild_index(self):
        """Rebuild the entire index from stored data"""
        logger.info("Rebuilding FAISS index...")
        
        # Get all vectors (need to store them somewhere persistent)
        # For now, we'll rebuild from database
        # This is expensive and should be done infrequently
        
        # Create new index
        self._create_new_index()
        
        # Reload vectors from database
        # This requires integration with database service
        logger.warning("Index rebuild not fully implemented - vectors will be reloaded from DB")
        
        await self._save_index()
    
    async def _save_index(self):
        """Save index to disk"""
        try:
            # Create backup of old index
            if self.index_path.exists():
                backup_path = self.index_path.with_suffix('.bin.backup')
                import shutil
                shutil.copy(self.index_path, backup_path)
                logger.debug(f"Created backup at {backup_path}")
            
            # Save new index
            faiss.write_index(self.index, str(self.index_path))
            logger.info(f"Saved index to {self.index_path}")
            
        except Exception as e:
            logger.error(f"Failed to save index: {str(e)}")
    
    def get_index_size(self) -> int:
        """Get number of vectors in index"""
        return self.index.ntotal if self.index else 0
    
    def get_index_info(self) -> Dict:
        """Get information about the index"""
        return {
            "total_vectors": self.index.ntotal,
            "dimension": self.dimension,
            "index_type": type(self.index).__name__,
            "is_memory_mapped": settings.faiss_memory_mapped,
            "index_path": str(self.index_path)
        }