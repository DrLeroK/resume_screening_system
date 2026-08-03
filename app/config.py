"""
Centralized configuration management using Pydantic Settings
"""

from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import os

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_name: str = Field(default="Resume Screening System")
    app_version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    
    # Directories
    base_dir: Path = Field(default=Path(__file__).parent.parent)
    data_dir: Path = Field(default=Path("./data"))
    upload_dir: Path = Field(default=Path("./data/uploads"))
    parsed_dir: Path = Field(default=Path("./data/parsed"))
    faiss_index_path: Path = Field(default=Path("./data/faiss/index.bin"))
    database_path: Path = Field(default=Path("./data/screening.db"))
    models_cache_dir: Path = Field(default=Path("./models_cache"))
    
    # API Security
    api_key_enabled: bool = Field(default=False)
    api_key: Optional[str] = Field(default=None)
    
    # Processing limits
    max_file_size_mb: int = Field(default=10)
    allowed_extensions: List[str] = Field(default=[".pdf", ".docx"])
    background_workers: int = Field(default=4)
    batch_size: int = Field(default=50)
    
    # ML Models
    embedding_model: str = Field(default="all-MiniLM-L6-v2")
    ner_model: str = Field(default="en_core_web_lg")
    ner_model_fallback: str = Field(default="en_core_web_sm")
    
    # Matching
    similarity_threshold: float = Field(default=0.65)
    top_k_results: int = Field(default=10)
    use_reranking: bool = Field(default=False)
    
    # Bias Detection
    bias_protected_attributes: List[str] = Field(default=["gender", "age", "ethnicity"])
    bias_sample_size: int = Field(default=1000)
    bias_threshold: float = Field(default=0.8)
    
    # Performance
    cache_size: int = Field(default=100)
    faiss_memory_mapped: bool = Field(default=True)
    batch_embedding_size: int = Field(default=32)
    
    # OCR
    ocr_enabled: bool = Field(default=False)
    tesseract_cmd: str = Field(default="/usr/bin/tesseract")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
    @validator("allowed_extensions", pre=True)
    def parse_allowed_extensions(cls, v):
        """Parse allowed extensions from string or list"""
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v
    
    @validator("bias_protected_attributes", pre=True)
    def parse_protected_attributes(cls, v):
        """Parse protected attributes from string or list"""
        if isinstance(v, str):
            return [attr.strip() for attr in v.split(",")]
        return v
    
    def setup_directories(self):
        """Create necessary directories if they don't exist"""
        directories = [
            self.data_dir,
            self.upload_dir,
            self.parsed_dir,
            self.faiss_index_path.parent,
            self.models_cache_dir,
            Path("./logs")
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def validate_paths(self):
        """Validate all paths are writable/readable"""
        # Check upload directory is writable
        if not self.upload_dir.exists():
            raise PermissionError(f"Upload directory {self.upload_dir} does not exist and cannot be created")
        
        # Check database directory is writable
        if not self.database_path.parent.exists():
            raise PermissionError(f"Database directory {self.database_path.parent} does not exist")

# Global settings instance
settings = Settings()

# Setup directories on import
settings.setup_directories()