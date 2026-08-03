"""
Custom exceptions for the application
"""

from typing import Optional, Any

class ScreeningSystemException(Exception):
    """Base exception for the screening system"""
    def __init__(self, message: str, details: Optional[Any] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)

class ParsingError(ScreeningSystemException):
    """Error during document parsing"""
    pass

class ExtractionError(ScreeningSystemException):
    """Error during NER/extraction"""
    pass

class EmbeddingError(ScreeningSystemException):
    """Error during embedding generation"""
    pass

class IndexError(ScreeningSystemException):
    """Error with FAISS index"""
    pass

class BiasDetectionError(ScreeningSystemException):
    """Error during bias detection"""
    pass

class ValidationError(ScreeningSystemException):
    """Input validation error"""
    pass

class ResourceNotFoundError(ScreeningSystemException):
    """Resource not found"""
    pass

class ProcessingTimeoutError(ScreeningSystemException):
    """Background task timeout"""
    pass

class ModelLoadError(ScreeningSystemException):
    """Error loading ML model"""
    pass

class ConfigurationError(ScreeningSystemException):
    """Configuration error"""
    pass