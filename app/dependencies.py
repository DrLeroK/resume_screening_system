"""
Dependency injection for FastAPI
"""

from sqlalchemy.orm import Session
from .models.database import get_session
from .services.parser import DocumentParser
from .services.extractor import InformationExtractor
from .services.embedder import TextEmbedder
from .services.searcher import FAISSSearcher
from .services.matcher import ResumeMatcher

# Singleton instances
_parser = None
_extractor = None
_embedder = None
_searcher = None
_matcher = None

def get_db():
    """Get database session"""
    db = get_session()
    try:
        yield db
    finally:
        db.close()

def get_parser():
    """Get document parser instance (singleton)"""
    global _parser
    if _parser is None:
        _parser = DocumentParser()
    return _parser

def get_extractor():
    """Get information extractor instance (singleton)"""
    global _extractor
    if _extractor is None:
        _extractor = InformationExtractor()
    return _extractor

def get_embedder():
    """Get text embedder instance (singleton)"""
    global _embedder
    if _embedder is None:
        _embedder = TextEmbedder()
    return _embedder

def get_searcher():
    """Get FAISS searcher instance (singleton)"""
    global _searcher
    if _searcher is None:
        # Get embedding dimension from embedder
        embedder = get_embedder()
        _searcher = FAISSSearcher(embedder.get_embedding_dimension())
    return _searcher

def get_matcher():
    """Get resume matcher instance (singleton)"""
    global _matcher
    if _matcher is None:
        embedder = get_embedder()
        searcher = get_searcher()
        _matcher = ResumeMatcher(embedder, searcher)
    return _matcher