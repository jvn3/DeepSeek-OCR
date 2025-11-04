"""Core data models and schemas for the OCR API."""
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator


class DocType(str, Enum):
    """Supported document types."""
    AUTO = "auto"
    PASSPORT = "passport"
    RESUME = "resume"
    GENERIC = "generic"
    FORM_DS160 = "form_ds160"
    INVOICE = "invoice"
    RECEIPT = "receipt"
    ID_CARD = "id_card"
    DRIVERS_LICENSE = "drivers_license"


class BBox(BaseModel):
    """Normalized bounding box in page coordinates [0,1]."""
    x1: float = Field(..., ge=0.0, le=1.0, description="Left x coordinate")
    y1: float = Field(..., ge=0.0, le=1.0, description="Top y coordinate")
    x2: float = Field(..., ge=0.0, le=1.0, description="Right x coordinate")
    y2: float = Field(..., ge=0.0, le=1.0, description="Bottom y coordinate")
    
    @field_validator('x2')
    @classmethod
    def x2_greater_than_x1(cls, v, info):
        if 'x1' in info.data and v <= info.data['x1']:
            raise ValueError('x2 must be greater than x1')
        return v
    
    @field_validator('y2')
    @classmethod
    def y2_greater_than_y1(cls, v, info):
        if 'y1' in info.data and v <= info.data['y1']:
            raise ValueError('y2 must be greater than y1')
        return v


class RedactionMask(BaseModel):
    """Region to redact/skip during OCR processing."""
    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)
    w: float = Field(..., gt=0.0, le=1.0)
    h: float = Field(..., gt=0.0, le=1.0)


class SessionCryptoInfo(BaseModel):
    """Session-level encryption parameters."""
    client_pubkey: str = Field(..., description="Base64-encoded X25519 public key")
    aead: str = Field(default="xchacha20poly1305", description="AEAD algorithm")


class ClientMeta(BaseModel):
    """Client metadata for request tracking."""
    request_id: Optional[str] = Field(None, description="Client-generated request ID")
    origin: Optional[str] = Field(None, description="Origin identifier (web, mobile, etc)")


class OCRImageRequest(BaseModel):
    """Request schema for /v1/ocr/image endpoint."""
    doc_type: DocType = Field(default=DocType.AUTO, description="Document type hint")
    language_hint: Optional[str] = Field(None, description="ISO 639-1 language code (en, es, etc)")
    return_layout: bool = Field(default=True, description="Include layout information (blocks, lines)")
    return_words: bool = Field(default=True, description="Include word-level details")
    redaction_masks: Optional[List[RedactionMask]] = Field(default=None, description="Regions to skip")
    page_index: int = Field(default=0, ge=0, description="Page number in multi-page document")
    client_meta: Optional[ClientMeta] = Field(default=None)
    session_crypto: Optional[SessionCryptoInfo] = Field(default=None, description="E2EE session parameters")


class Word(BaseModel):
    """Word-level OCR result."""
    text: str
    bbox: List[float] = Field(..., min_length=4, max_length=4, description="[x1, y1, x2, y2] normalized")
    confidence: float = Field(..., ge=0.0, le=1.0, alias="conf")
    
    class Config:
        populate_by_name = True


class Line(BaseModel):
    """Line-level OCR result."""
    text: str
    bbox: List[float] = Field(..., min_length=4, max_length=4)
    confidence: float = Field(..., ge=0.0, le=1.0, alias="conf")
    word_ids: Optional[List[int]] = Field(default=None, description="Indices of words in this line")
    
    class Config:
        populate_by_name = True


class Block(BaseModel):
    """Block-level OCR result (paragraph, heading, etc)."""
    text: str
    bbox: List[float] = Field(..., min_length=4, max_length=4)
    confidence: float = Field(..., ge=0.0, le=1.0, alias="conf")
    block_type: Optional[str] = Field(default="text", description="text, heading, table, figure, etc")
    line_ids: Optional[List[int]] = Field(default=None, description="Indices of lines in this block")
    
    class Config:
        populate_by_name = True


class Provenance(BaseModel):
    """Information about the OCR engine and version."""
    engine: str = Field(default="deepseek-ocr")
    version: str = Field(default="1.0.0")
    model_path: Optional[str] = None


class OCRImageResponse(BaseModel):
    """Response schema for /v1/ocr/image endpoint."""
    page_index: int
    text: str
    blocks: Optional[List[Block]] = None
    lines: Optional[List[Line]] = None
    words: Optional[List[Word]] = None
    language: Optional[str] = None
    time_ms: float = Field(..., description="Processing time in milliseconds")
    provenance: Provenance


class Entity(BaseModel):
    """Named entity extraction result."""
    label: str = Field(..., description="Entity type (PERSON, ORG, DATE, etc)")
    text: str
    confidence: float = Field(..., ge=0.0, le=1.0, alias="conf")
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    page: Optional[int] = None
    word_ids: Optional[List[int]] = None
    
    class Config:
        populate_by_name = True


class FieldSource(BaseModel):
    """Source provenance for an extracted field."""
    page: int
    word_ids: List[int] = Field(..., description="Indices of words that contributed to this field")


class ExtractedField(BaseModel):
    """Extracted and normalized field value."""
    value: Any
    confidence: float = Field(..., ge=0.0, le=1.0, alias="conf")
    source: FieldSource
    
    class Config:
        populate_by_name = True


class LayoutInput(BaseModel):
    """Layout information for semantic parsing."""
    blocks: Optional[List[Block]] = None
    lines: Optional[List[Line]] = None
    words: Optional[List[Word]] = None


class SemanticParseRequest(BaseModel):
    """Request schema for /v1/parse/semantic endpoint."""
    doc_type: DocType = Field(default=DocType.AUTO)
    text: Optional[str] = None
    layout: Optional[LayoutInput] = None
    hints: Optional[Dict[str, str]] = Field(
        default=None,
        description="Additional hints (country, dateFormat, etc)"
    )


class DocTypeClassification(BaseModel):
    """Document type classification result."""
    type: str
    score: float = Field(..., ge=0.0, le=1.0)


class SemanticParseResponse(BaseModel):
    """Response schema for /v1/parse/semantic endpoint."""
    detected_doc_type: DocTypeClassification
    entities: List[Entity]
    fields: Dict[str, ExtractedField]


class FormMatchRequest(BaseModel):
    """Request schema for /v1/forms/match endpoint."""
    form_id: str = Field(..., description="Form identifier (e.g., ds-160@v2025-10)")
    fields: Dict[str, ExtractedField]
    strict: bool = Field(default=False, description="Require exact field matches")


class FieldMapping(BaseModel):
    """Mapping between extracted field and form field."""
    form_field: str = Field(..., description="Target form field path (e.g., applicant.fullName)")
    source_field: str = Field(..., description="Source extracted field key")
    confidence: float = Field(..., ge=0.0, le=1.0)


class FormMatchResponse(BaseModel):
    """Response schema for /v1/forms/match endpoint."""
    form_id: str
    mapping: List[FieldMapping]
    unmapped: List[str] = Field(..., description="Form fields without matches")


class BatchOCRRequest(BaseModel):
    """Request schema for /v1/ocr/batch endpoint."""
    pages: Optional[List[str]] = Field(
        default=None,
        description="List of presigned URLs or base64-encoded images"
    )
    doc_type: DocType = Field(default=DocType.AUTO)
    language_hint: Optional[str] = None
    return_layout: bool = True
    return_words: bool = True
    webhook_url: Optional[str] = Field(
        default=None,
        description="Optional callback URL for job completion notification"
    )
    client_meta: Optional[ClientMeta] = None


class BatchOCRResponse(BaseModel):
    """Response schema for /v1/ocr/batch endpoint."""
    job_id: str
    total_pages: int
    stream_url: str = Field(..., description="SSE endpoint URL for streaming results")


class PageResult(BaseModel):
    """Single page result in batch processing."""
    page_index: int
    status: str = Field(..., description="completed, failed, processing")
    result: Optional[OCRImageResponse] = None
    error: Optional[str] = None


class BatchStreamEvent(BaseModel):
    """Server-sent event for batch job progress."""
    job_id: str
    event_type: str = Field(..., description="page_completed, job_completed, error")
    page_result: Optional[PageResult] = None
    progress: Optional[Dict[str, int]] = Field(
        default=None,
        description="completed, failed, total counts"
    )


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: float
    version: str


class ReadinessResponse(BaseModel):
    """Readiness check response."""
    ready: bool
    checks: Dict[str, bool] = Field(
        ...,
        description="Individual component checks (gpu, model_loaded, queue_available)"
    )
    queue_depth: Optional[int] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    retry_after: Optional[int] = Field(default=None, description="Seconds to wait before retry")
    request_id: Optional[str] = None


class ErrorCode(str, Enum):
    """Machine-readable error codes."""
    RATE_LIMITED = "RATE_LIMITED"
    UNSUPPORTED_MEDIA_TYPE = "UNSUPPORTED_MEDIA_TYPE"
    PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
    E2EE_REQUIRED = "E2EE_REQUIRED"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    INVALID_REQUEST = "INVALID_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    DECRYPTION_FAILED = "DECRYPTION_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
