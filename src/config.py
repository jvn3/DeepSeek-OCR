"""Environment configuration with validation."""
import os
from typing import Optional


class Settings:
    """Application settings loaded from environment variables."""
    
    # Service
    VERSION: str = "1.0.0"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Model
    MODEL_PATH: str = os.getenv("MODEL_PATH", "deepseek-ai/DeepSeek-OCR")
    USE_MOCK_ADAPTER: bool = os.getenv("USE_MOCK_ADAPTER", "false").lower() == "true"
    DEVICE: str = os.getenv("DEVICE", "cuda")
    GPU_MEMORY_UTILIZATION: float = float(os.getenv("GPU_MEMORY_UTILIZATION", "0.9"))
    
    # Security
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")
    REQUIRE_E2EE: bool = os.getenv("REQUIRE_E2EE", "false").lower() == "true"
    USE_JWKS: bool = os.getenv("USE_JWKS", "true").lower() == "true"
    
    # Limits
    MAX_PAGE_MEGAPIXELS: int = int(os.getenv("MAX_PAGE_MEGAPIXELS", "25"))
    MAX_PAGES: int = int(os.getenv("MAX_PAGES", "100"))
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
    
    # Features
    ENABLE_SSE: bool = os.getenv("ENABLE_SSE", "true").lower() == "true"
    ALLOW_PDF_UPLOADS: bool = os.getenv("ALLOW_PDF_UPLOADS", "false").lower() == "true"
    
    # Rate limiting
    MAX_REQUESTS_PER_MINUTE: int = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "60"))
    MAX_REQUESTS_PER_MINUTE_PER_IP: int = int(os.getenv("MAX_REQUESTS_PER_MINUTE_PER_IP", "100"))
    
    # Queue
    MAX_CONCURRENCY: int = int(os.getenv("MAX_CONCURRENCY", "10"))
    
    # CORS
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    
    def validate(self):
        """Validate configuration."""
        errors = []
        
        if self.PORT < 1 or self.PORT > 65535:
            errors.append("PORT must be between 1 and 65535")
        
        if self.MAX_FILE_SIZE_MB < 1:
            errors.append("MAX_FILE_SIZE_MB must be at least 1")
        
        if self.MAX_CONCURRENCY < 1:
            errors.append("MAX_CONCURRENCY must be at least 1")
        
        if not self.USE_MOCK_ADAPTER and not self.MODEL_PATH:
            errors.append("MODEL_PATH is required when USE_MOCK_ADAPTER=false")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True


settings = Settings()
