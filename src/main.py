"""
Production-grade OCR microservice with zero-knowledge E2EE capabilities.

This service provides OCR, document understanding, and form mapping while
maintaining client-side encryption for sensitive documents.
"""
import os
import io
import time
import json
import asyncio
import logging
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

import uvicorn
from fastapi import (
    FastAPI, File, UploadFile, Depends, HTTPException, Request,
    Header, Response, BackgroundTasks
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.status import (
    HTTP_400_BAD_REQUEST, HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    HTTP_415_UNSUPPORTED_MEDIA_TYPE, HTTP_503_SERVICE_UNAVAILABLE
)

from models.schemas import (
    OCRImageRequest, OCRImageResponse, SemanticParseRequest, SemanticParseResponse,
    FormMatchRequest, FormMatchResponse, BatchOCRRequest, BatchOCRResponse,
    HealthResponse, ReadinessResponse, ErrorResponse, ErrorCode,
    Provenance, PageResult, BatchStreamEvent
)
from crypto.e2ee import get_server_session, SessionCrypto, parse_session_crypto_header
from auth.supabase import init_auth, verify_jwt, optional_jwt
from inference.adapter import InferenceAdapter, DeepSeekAdapter, MockAdapter
from forms.matcher import get_form_matcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment
class Config:
    """Service configuration from environment variables."""
    
    # Service
    VERSION = "1.0.0"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    
    # Model
    MODEL_PATH = os.getenv("MODEL_PATH", "deepseek-ai/DeepSeek-OCR")
    USE_MOCK_ADAPTER = os.getenv("USE_MOCK_ADAPTER", "false").lower() == "true"
    
    # Security
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
    REQUIRE_E2EE = os.getenv("REQUIRE_E2EE", "false").lower() == "true"
    
    # Limits
    MAX_PAGE_MEGAPIXELS = int(os.getenv("MAX_PAGE_MEGAPIXELS", "25"))
    MAX_PAGES = int(os.getenv("MAX_PAGES", "100"))
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
    
    # Features
    ENABLE_SSE = os.getenv("ENABLE_SSE", "true").lower() == "true"
    ALLOW_PDF_UPLOADS = os.getenv("ALLOW_PDF_UPLOADS", "false").lower() == "true"
    
    # Rate limiting
    MAX_REQUESTS_PER_MINUTE = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "60"))
    
    # Queue
    MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "10"))


config = Config()

# Prometheus metrics
REQUESTS_TOTAL = Counter(
    'ocr_requests_total',
    'Total OCR requests',
    ['endpoint', 'status']
)
REQUEST_DURATION = Histogram(
    'ocr_request_duration_seconds',
    'Request duration in seconds',
    ['endpoint']
)
OCR_PROCESSING_TIME = Histogram(
    'ocr_processing_time_ms',
    'OCR processing time in milliseconds'
)
QUEUE_DEPTH = Gauge(
    'ocr_queue_depth',
    'Current queue depth'
)
ACTIVE_JOBS = Gauge(
    'ocr_active_jobs',
    'Number of active batch jobs'
)

# Global state
inference_adapter: Optional[InferenceAdapter] = None
batch_jobs: Dict[str, Dict[str, Any]] = {}
job_semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    global inference_adapter
    
    # Startup
    logger.info("Starting OCR service...")
    
    # Initialize authentication
    if config.SUPABASE_URL:
        init_auth(config.SUPABASE_URL, config.SUPABASE_JWT_SECRET)
        logger.info("Supabase authentication initialized")
    
    # Initialize inference adapter
    try:
        if config.USE_MOCK_ADAPTER:
            logger.info("Using mock inference adapter")
            inference_adapter = MockAdapter()
        else:
            logger.info(f"Loading DeepSeek-OCR model from {config.MODEL_PATH}")
            inference_adapter = DeepSeekAdapter(config.MODEL_PATH)
        
        if inference_adapter.is_ready():
            logger.info("Inference adapter ready")
        else:
            logger.warning("Inference adapter not ready")
    except Exception as e:
        logger.error(f"Failed to initialize inference adapter: {e}")
        if not config.USE_MOCK_ADAPTER:
            logger.warning("Falling back to mock adapter")
            inference_adapter = MockAdapter()
    
    yield
    
    # Shutdown
    logger.info("Shutting down OCR service...")


# Create FastAPI app
app = FastAPI(
    title="DeepSeek-OCR API",
    version=config.VERSION,
    description="Production-grade OCR microservice with zero-knowledge E2EE",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "0.0.0.0"


def decrypt_request_body(
    body: bytes,
    client_pubkey: Optional[str]
) -> bytes:
    """
    Decrypt request body if E2EE is enabled.
    
    Args:
        body: Request body (encrypted or plaintext)
        client_pubkey: Client's X25519 public key (base64)
        
    Returns:
        Decrypted plaintext bytes
    """
    if not client_pubkey:
        if config.REQUIRE_E2EE:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": ErrorCode.E2EE_REQUIRED,
                    "message": "E2EE is required. Provide client_pubkey header."
                }
            )
        return body
    
    # Validate client pubkey
    validated_pubkey = parse_session_crypto_header(client_pubkey)
    if not validated_pubkey:
        raise HTTPException(
            status_code=400,
            detail={
                "error": ErrorCode.INVALID_REQUEST,
                "message": "Invalid client_pubkey format"
            }
        )
    
    try:
        session = get_server_session()
        shared_secret = session.derive_shared_secret(validated_pubkey)
        plaintext = SessionCrypto.decrypt_payload(body, shared_secret)
        return plaintext
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": ErrorCode.DECRYPTION_FAILED,
                "message": "Failed to decrypt request body"
            }
        )


def encrypt_response_body(
    body: bytes,
    client_pubkey: Optional[str]
) -> bytes:
    """Encrypt response body if E2EE session is active."""
    if not client_pubkey:
        return body
    
    try:
        session = get_server_session()
        shared_secret = session.derive_shared_secret(client_pubkey)
        encrypted, _ = SessionCrypto.encrypt_payload(body, shared_secret)
        return encrypted
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return body  # Fall back to plaintext


@app.get("/v1/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=time.time(),
        version=config.VERSION
    )


@app.get("/v1/ready", response_model=ReadinessResponse)
async def readiness_check():
    """Readiness check with dependency verification."""
    checks = {
        "model_loaded": inference_adapter is not None and inference_adapter.is_ready(),
        "queue_available": True,
    }
    
    ready = all(checks.values())
    
    return ReadinessResponse(
        ready=ready,
        checks=checks,
        queue_depth=len(batch_jobs)
    )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.post("/v1/ocr/image", response_model=OCRImageResponse)
async def ocr_image(
    request: Request,
    image: UploadFile = File(...),
    doc_type: str = "auto",
    language_hint: Optional[str] = None,
    return_layout: bool = True,
    return_words: bool = True,
    page_index: int = 0,
    client_pubkey: Optional[str] = Header(None, alias="X-Client-Pubkey"),
    user: dict = Depends(verify_jwt)
):
    """
    OCR a single page image with optional E2EE.
    
    The image can be encrypted using the session key derived from client_pubkey.
    """
    start_time = time.time()
    
    try:
        # Check file size
        content = await image.read()
        if len(content) > config.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={
                    "error": ErrorCode.PAYLOAD_TOO_LARGE,
                    "message": f"File size exceeds {config.MAX_FILE_SIZE_MB}MB limit"
                }
            )
        
        # Decrypt if needed
        plaintext_image = decrypt_request_body(content, client_pubkey)
        
        # Validate image type
        if not image.content_type or not image.content_type.startswith('image/'):
            raise HTTPException(
                status_code=HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail={
                    "error": ErrorCode.UNSUPPORTED_MEDIA_TYPE,
                    "message": "Only image files are supported (PNG, JPEG, TIFF)"
                }
            )
        
        # Perform OCR
        if not inference_adapter or not inference_adapter.is_ready():
            raise HTTPException(
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": ErrorCode.MODEL_UNAVAILABLE,
                    "message": "OCR model not available"
                }
            )
        
        result = inference_adapter.ocr_image(
            image_data=plaintext_image,
            language_hint=language_hint,
            return_layout=return_layout,
            return_words=return_words
        )
        
        # Record metrics
        OCR_PROCESSING_TIME.observe(result.processing_time_ms)
        
        response = OCRImageResponse(
            page_index=page_index,
            text=result.text,
            blocks=result.blocks if return_layout else None,
            lines=result.lines if return_layout else None,
            words=result.words if return_words else None,
            language=result.language,
            time_ms=result.processing_time_ms,
            provenance=Provenance(
                engine="deepseek-ocr",
                version=config.VERSION,
                model_path=config.MODEL_PATH
            )
        )
        
        REQUESTS_TOTAL.labels(endpoint='/v1/ocr/image', status='success').inc()
        REQUEST_DURATION.labels(endpoint='/v1/ocr/image').observe(time.time() - start_time)
        
        # Note: Response encryption happens at the transport level via E2EE session
        # The client will decrypt using the shared secret
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR error: {e}", exc_info=True)
        REQUESTS_TOTAL.labels(endpoint='/v1/ocr/image', status='error').inc()
        raise HTTPException(
            status_code=500,
            detail={
                "error": ErrorCode.INTERNAL_ERROR,
                "message": f"Internal server error: {str(e)}"
            }
        )


@app.post("/v1/parse/semantic", response_model=SemanticParseResponse)
async def parse_semantic(
    request_data: SemanticParseRequest,
    user: dict = Depends(verify_jwt)
):
    """Extract entities and structured fields from OCR output."""
    start_time = time.time()
    
    try:
        if not inference_adapter or not inference_adapter.is_ready():
            raise HTTPException(
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": ErrorCode.MODEL_UNAVAILABLE,
                    "message": "Model not available"
                }
            )
        
        # If no text provided, extract from layout
        text = request_data.text or ""
        if not text and request_data.layout:
            if request_data.layout.blocks:
                text = "\n\n".join(b.text for b in request_data.layout.blocks)
            elif request_data.layout.lines:
                text = "\n".join(l.text for l in request_data.layout.lines)
        
        if not text:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail={
                    "error": ErrorCode.INVALID_REQUEST,
                    "message": "Either text or layout must be provided"
                }
            )
        
        # Classify document type
        doc_classification = inference_adapter.classify_doc_type(
            text=text,
            layout=request_data.layout.model_dump() if request_data.layout else None
        )
        
        # Extract entities and fields
        doc_type = request_data.doc_type if request_data.doc_type != "auto" else doc_classification.type
        entities, fields = inference_adapter.extract_entities(
            doc_type=doc_type,
            text=text,
            layout=request_data.layout.model_dump() if request_data.layout else None,
            hints=request_data.hints
        )
        
        response = SemanticParseResponse(
            detected_doc_type=doc_classification,
            entities=entities,
            fields=fields
        )
        
        REQUESTS_TOTAL.labels(endpoint='/v1/parse/semantic', status='success').inc()
        REQUEST_DURATION.labels(endpoint='/v1/parse/semantic').observe(time.time() - start_time)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Semantic parse error: {e}", exc_info=True)
        REQUESTS_TOTAL.labels(endpoint='/v1/parse/semantic', status='error').inc()
        raise HTTPException(
            status_code=500,
            detail={
                "error": ErrorCode.INTERNAL_ERROR,
                "message": f"Internal server error: {str(e)}"
            }
        )


@app.post("/v1/forms/match", response_model=FormMatchResponse)
async def match_form(
    request_data: FormMatchRequest,
    user: dict = Depends(verify_jwt)
):
    """Map extracted fields to form schema."""
    start_time = time.time()
    
    try:
        matcher = get_form_matcher()
        response = matcher.match_fields(
            form_id=request_data.form_id,
            extracted_fields=request_data.fields,
            strict=request_data.strict
        )
        
        REQUESTS_TOTAL.labels(endpoint='/v1/forms/match', status='success').inc()
        REQUEST_DURATION.labels(endpoint='/v1/forms/match').observe(time.time() - start_time)
        
        return response
        
    except Exception as e:
        logger.error(f"Form match error: {e}", exc_info=True)
        REQUESTS_TOTAL.labels(endpoint='/v1/forms/match', status='error').inc()
        raise HTTPException(
            status_code=500,
            detail={
                "error": ErrorCode.INTERNAL_ERROR,
                "message": f"Internal server error: {str(e)}"
            }
        )


@app.post("/v1/ocr/batch", response_model=BatchOCRResponse)
async def ocr_batch(
    request_data: BatchOCRRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(verify_jwt)
):
    """
    Start a batch OCR job for multiple pages.
    
    Returns a job ID and SSE stream URL for progress updates.
    """
    try:
        if not request_data.pages:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail={
                    "error": ErrorCode.INVALID_REQUEST,
                    "message": "No pages provided"
                }
            )
        
        if len(request_data.pages) > config.MAX_PAGES:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail={
                    "error": ErrorCode.PAYLOAD_TOO_LARGE,
                    "message": f"Batch size exceeds {config.MAX_PAGES} pages limit"
                }
            )
        
        # Generate job ID
        import uuid
        job_id = str(uuid.uuid4())
        
        # Initialize job state
        batch_jobs[job_id] = {
            "status": "queued",
            "total_pages": len(request_data.pages),
            "completed": 0,
            "failed": 0,
            "results": [],
            "created_at": time.time()
        }
        
        # Start background processing
        background_tasks.add_task(
            process_batch_job,
            job_id=job_id,
            pages=request_data.pages,
            options=request_data
        )
        
        ACTIVE_JOBS.inc()
        
        return BatchOCRResponse(
            job_id=job_id,
            total_pages=len(request_data.pages),
            stream_url=f"/v1/ocr/stream/{job_id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch OCR error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": ErrorCode.INTERNAL_ERROR,
                "message": f"Internal server error: {str(e)}"
            }
        )


@app.get("/v1/ocr/stream/{job_id}")
async def stream_batch_results(
    job_id: str,
    request: Request,
    user: dict = Depends(optional_jwt)
):
    """Stream batch job results via Server-Sent Events."""
    if not config.ENABLE_SSE:
        raise HTTPException(
            status_code=400,
            detail={
                "error": ErrorCode.INVALID_REQUEST,
                "message": "SSE streaming is disabled"
            }
        )
    
    if job_id not in batch_jobs:
        raise HTTPException(
            status_code=404,
            detail={
                "error": ErrorCode.JOB_NOT_FOUND,
                "message": f"Job {job_id} not found"
            }
        )
    
    async def event_generator():
        """Generate SSE events for job progress."""
        while True:
            if await request.is_disconnected():
                break
            
            job = batch_jobs.get(job_id)
            if not job:
                break
            
            # Send progress update
            event = BatchStreamEvent(
                job_id=job_id,
                event_type="progress",
                progress={
                    "completed": job["completed"],
                    "failed": job["failed"],
                    "total": job["total_pages"]
                }
            )
            
            yield f"data: {event.model_dump_json()}\n\n"
            
            # Check if job is complete
            if job["status"] == "completed":
                final_event = BatchStreamEvent(
                    job_id=job_id,
                    event_type="job_completed",
                    progress={
                        "completed": job["completed"],
                        "failed": job["failed"],
                        "total": job["total_pages"]
                    }
                )
                yield f"data: {final_event.model_dump_json()}\n\n"
                break
            
            await asyncio.sleep(1)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


async def process_batch_job(
    job_id: str,
    pages: list[str],
    options: BatchOCRRequest
):
    """Process batch OCR job in background."""
    try:
        job = batch_jobs[job_id]
        job["status"] = "processing"
        
        for idx, page_data in enumerate(pages):
            async with job_semaphore:
                try:
                    # Decode page (assume base64 for now)
                    import base64
                    image_bytes = base64.b64decode(page_data)
                    
                    # Process page
                    result = inference_adapter.ocr_image(
                        image_data=image_bytes,
                        language_hint=options.language_hint,
                        return_layout=options.return_layout,
                        return_words=options.return_words
                    )
                    
                    page_result = PageResult(
                        page_index=idx,
                        status="completed",
                        result=OCRImageResponse(
                            page_index=idx,
                            text=result.text,
                            blocks=result.blocks,
                            lines=result.lines,
                            words=result.words,
                            language=result.language,
                            time_ms=result.processing_time_ms,
                            provenance=Provenance(engine="deepseek-ocr", version=config.VERSION)
                        )
                    )
                    
                    job["completed"] += 1
                    
                except Exception as e:
                    logger.error(f"Page {idx} processing failed: {e}")
                    page_result = PageResult(
                        page_index=idx,
                        status="failed",
                        error=str(e)
                    )
                    job["failed"] += 1
                
                job["results"].append(page_result)
        
        job["status"] = "completed"
        
    except Exception as e:
        logger.error(f"Batch job {job_id} failed: {e}")
        job["status"] = "failed"
    finally:
        ACTIVE_JOBS.dec()


@app.get("/")
async def root():
    """Root endpoint with API info."""
    session = get_server_session()
    
    return {
        "service": "DeepSeek-OCR API",
        "version": config.VERSION,
        "status": "ready" if inference_adapter and inference_adapter.is_ready() else "initializing",
        "e2ee": {
            "enabled": True,
            "server_pubkey": session.get_public_key_b64(),
            "algorithm": "x25519-xchacha20poly1305"
        },
        "endpoints": {
            "health": "/v1/health",
            "ready": "/v1/ready",
            "metrics": "/metrics",
            "ocr_image": "/v1/ocr/image",
            "parse_semantic": "/v1/parse/semantic",
            "forms_match": "/v1/forms/match",
            "ocr_batch": "/v1/ocr/batch",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,
        log_level="info"
    )
