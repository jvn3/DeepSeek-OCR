#!/usr/bin/env python3
"""
Simple OCR server without authentication for local development
"""
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn
import base64
import json
from datetime import datetime

app = FastAPI(title="DeepSeek OCR Server", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock responses for testing
class SemanticRequest(BaseModel):
    text: str
    layout: Optional[Dict[str, Any]] = None
    hints: Optional[Dict[str, Any]] = None

@app.get("/v1/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().timestamp(),
        "version": "1.0.0"
    }

@app.post("/v1/ocr/image")
async def ocr_image(
    image: UploadFile = File(...),
    languageHint: Optional[str] = Form("en"),
    returnLayout: Optional[bool] = Form(True),
    returnWords: Optional[bool] = Form(True),
    pageIndex: Optional[int] = Form(0)
):
    """Mock OCR endpoint - accepts multipart/form-data with image file"""
    # Read the image (we don't actually process it in mock mode)
    image_data = await image.read()
    
    return {
        "text": f"Sample OCR text from page {pageIndex + 1}. This is a mock response for testing.\\n\\nThe DeepSeek OCR model would extract actual text from your image.",
        "blocks": [
            {
                "id": "block_0",
                "text": "Sample heading",
                "bbox": [0.1, 0.1, 0.9, 0.2],
                "type": "title",
                "conf": 0.98,
                "lineIds": ["line_0"],
                "page": pageIndex
            },
            {
                "id": "block_1",
                "text": "Sample paragraph text that would be extracted from the document.",
                "bbox": [0.1, 0.25, 0.9, 0.4],
                "type": "text",
                "conf": 0.95,
                "lineIds": ["line_1", "line_2"],
                "page": pageIndex
            }
        ],
        "lines": [
            {
                "id": "line_0",
                "text": "Sample heading",
                "bbox": [0.1, 0.1, 0.9, 0.2],
                "conf": 0.98,
                "wordIds": ["word_0", "word_1"],
                "page": pageIndex
            },
            {
                "id": "line_1",
                "text": "Sample paragraph text that would",
                "bbox": [0.1, 0.25, 0.9, 0.3],
                "conf": 0.96,
                "wordIds": ["word_2", "word_3", "word_4", "word_5", "word_6"],
                "page": pageIndex
            },
            {
                "id": "line_2",
                "text": "be extracted from the document.",
                "bbox": [0.1, 0.32, 0.9, 0.4],
                "conf": 0.94,
                "wordIds": ["word_7", "word_8", "word_9", "word_10", "word_11"],
                "page": pageIndex
            }
        ],
        "words": [
            {"id": "word_0", "text": "Sample", "bbox": [0.1, 0.1, 0.3, 0.2], "conf": 0.99, "page": pageIndex},
            {"id": "word_1", "text": "heading", "bbox": [0.32, 0.1, 0.5, 0.2], "conf": 0.97, "page": pageIndex},
            {"id": "word_2", "text": "Sample", "bbox": [0.1, 0.25, 0.2, 0.3], "conf": 0.98, "page": pageIndex},
            {"id": "word_3", "text": "paragraph", "bbox": [0.21, 0.25, 0.35, 0.3], "conf": 0.96, "page": pageIndex},
            {"id": "word_4", "text": "text", "bbox": [0.36, 0.25, 0.45, 0.3], "conf": 0.97, "page": pageIndex},
            {"id": "word_5", "text": "that", "bbox": [0.46, 0.25, 0.55, 0.3], "conf": 0.95, "page": pageIndex},
            {"id": "word_6", "text": "would", "bbox": [0.56, 0.25, 0.65, 0.3], "conf": 0.94, "page": pageIndex},
            {"id": "word_7", "text": "be", "bbox": [0.1, 0.32, 0.15, 0.4], "conf": 0.96, "page": pageIndex},
            {"id": "word_8", "text": "extracted", "bbox": [0.16, 0.32, 0.35, 0.4], "conf": 0.93, "page": pageIndex},
            {"id": "word_9", "text": "from", "bbox": [0.36, 0.32, 0.48, 0.4], "conf": 0.95, "page": pageIndex},
            {"id": "word_10", "text": "the", "bbox": [0.49, 0.32, 0.58, 0.4], "conf": 0.94, "page": pageIndex},
            {"id": "word_11", "text": "document.", "bbox": [0.59, 0.32, 0.8, 0.4], "conf": 0.92, "page": pageIndex},
        ],
        "timeMs": 145
    }

@app.post("/v1/parse/semantic")
async def parse_semantic(request: SemanticRequest):
    """Mock semantic parsing endpoint"""
    return {
        "detectedDocType": {
            "type": "Generic Document",
            "score": 0.85
        },
        "entities": [
            {"type": "DATE", "value": "2024-01-15", "conf": 0.95, "normalized": "2024-01-15"},
            {"type": "PERSON", "value": "John Smith", "conf": 0.92, "normalized": "John Smith"},
            {"type": "EMAIL", "value": "john@example.com", "conf": 0.98, "normalized": "john@example.com"},
        ],
        "fields": {
            "document_type": {
                "value": "Generic Document",
                "conf": 0.85,
                "source": {"page": 0, "wordIds": ["word_0", "word_1"]}
            },
            "name": {
                "value": "John Smith",
                "conf": 0.92,
                "source": {"page": 0, "wordIds": ["word_2", "word_3"]}
            },
            "date": {
                "value": "2024-01-15",
                "conf": 0.95,
                "source": {"page": 0, "wordIds": ["word_4"]}
            },
            "email": {
                "value": "john@example.com",
                "conf": 0.98,
                "source": {"page": 0, "wordIds": ["word_5"]}
            }
        }
    }

if __name__ == "__main__":
    print("=" * 60)
    print("DeepSeek OCR Simple Server (No Authentication)")
    print("=" * 60)
    print("Server starting on http://0.0.0.0:8000")
    print("Health check: http://localhost:8000/v1/health")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
