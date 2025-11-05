#!/usr/bin/env python3
"""
Real DeepSeek OCR Server
"""
import os
import sys
import re
import io
from typing import Optional, Dict, Any

sys.path.insert(0, '/data/DeepSeek-OCR/app/DeepSeek-OCR-master/DeepSeek-OCR-vllm')

import torch
if torch.version.cuda == '11.8':
    os.environ["TRITON_PTXAS_PATH"] = "/usr/local/cuda-11.8/bin/ptxas"

os.environ['VLLM_USE_V1'] = '0'
os.environ["CUDA_VISIBLE_DEVICES"] = '0'

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from vllm import AsyncLLMEngine, SamplingParams
from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.model_executor.models.registry import ModelRegistry
from deepseek_ocr import DeepseekOCRForCausalLM
from PIL import Image, ImageOps
from process.ngram_norepeat import NoRepeatNGramLogitsProcessor
from datetime import datetime

# Configuration
MODEL_PATH = 'deepseek-ai/DeepSeek-OCR'
PROMPT = '<image>\n<|grounding|>Convert the document to markdown.'

ModelRegistry.register_model("DeepseekOCRForCausalLM", DeepseekOCRForCausalLM)

app = FastAPI(title="DeepSeek OCR Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = None

class SemanticRequest(BaseModel):
    text: str
    layout: Optional[Dict[str, Any]] = None
    hints: Optional[Dict[str, Any]] = None

async def initialize_model():
    global engine
    
    print("\n" + "="*70)
    print("INITIALIZING DEEPSEEK OCR MODEL")
    print("="*70)
    print(f"Model: {MODEL_PATH}")
    print("Loading vLLM engine (this will take 1-2 minutes)...")
    
    engine_args = AsyncEngineArgs(
        model=MODEL_PATH,
        hf_overrides={"architectures": ["DeepseekOCRForCausalLM"]},
        block_size=256,
        max_model_len=8192,
        enforce_eager=False,
        trust_remote_code=True,
        tensor_parallel_size=1,
        gpu_memory_utilization=0.9,
    )
    engine = AsyncLLMEngine.from_engine_args(engine_args)
    
    print("\n" + "="*70)
    print("MODEL READY - Server accepting requests")
    print("="*70 + "\n")

@app.on_event("startup")
async def startup_event():
    await initialize_model()

def load_image_from_bytes(image_bytes: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image = ImageOps.exif_transpose(image)
        # Convert to RGB (required by DeepSeek processor)
        return image.convert('RGB')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {e}")

def parse_ocr_output(text: str, page_index: int = 0) -> Dict[str, Any]:
    clean_text = re.sub(r'<\|.*?\|>', '', text).strip()
    
    words = []
    lines = []
    blocks = []
    
    text_lines = clean_text.split('\n')
    y_pos = 0.1
    word_id = 0
    line_id = 0
    
    for line_text in text_lines:
        if not line_text.strip():
            continue
            
        line_words = line_text.split()
        line_word_ids = []
        x_pos = 0.1
        
        for word_text in line_words:
            word_width = len(word_text) * 0.01
            words.append({
                "id": f"word_{word_id}",
                "text": word_text,
                "bbox": [x_pos, y_pos, x_pos + word_width, y_pos + 0.05],
                "conf": 0.95,
                "page": page_index
            })
            line_word_ids.append(f"word_{word_id}")
            x_pos += word_width + 0.01
            word_id += 1
        
        lines.append({
            "id": f"line_{line_id}",
            "text": line_text,
            "bbox": [0.1, y_pos, 0.9, y_pos + 0.05],
            "conf": 0.95,
            "wordIds": line_word_ids,
            "page": page_index
        })
        
        y_pos += 0.06
        line_id += 1
    
    if lines:
        blocks.append({
            "id": "block_0",
            "text": clean_text,
            "bbox": [0.1, 0.1, 0.9, min(y_pos, 0.9)],
            "type": "text",
            "conf": 0.95,
            "lineIds": [line["id"] for line in lines],
            "page": page_index
        })
    
    return {
        "text": clean_text,
        "blocks": blocks,
        "lines": lines,
        "words": words,
        "timeMs": 0
    }

@app.get("/v1/health")
async def health():
    return {
        "status": "healthy" if engine else "initializing",
        "timestamp": datetime.now().timestamp(),
        "version": "1.0.0",
        "model": MODEL_PATH
    }

@app.post("/v1/ocr/image")
async def ocr_image(
    image: UploadFile = File(...),
    languageHint: Optional[str] = Form("en"),
    returnLayout: Optional[bool] = Form(True),
    returnWords: Optional[bool] = Form(True),
    pageIndex: Optional[int] = Form(0)
):
    if not engine:
        raise HTTPException(status_code=503, detail="Model not initialized")
    
    start_time = datetime.now()
    
    try:
        print(f"\n[OCR] Processing page {pageIndex}...")
        
        # Load image and convert to RGB
        image_bytes = await image.read()
        pil_image = load_image_from_bytes(image_bytes)
        pil_image = pil_image.convert('RGB')
        print(f"  Image: {pil_image.size}")
        
        # Sampling params
        logits_processors = [NoRepeatNGramLogitsProcessor(
            ngram_size=30, 
            window_size=90, 
            whitelist_token_ids={128821, 128822}
        )]
        
        sampling_params = SamplingParams(
            temperature=0.0,
            max_tokens=8192,
            logits_processors=logits_processors,
            skip_special_tokens=False,
        )
        
        # Generate - pass request dict directly
        print(f"  Running inference...")
        request_id = f"ocr_{pageIndex}_{start_time.timestamp()}"
        request_dict = {
            "prompt": PROMPT,
            "multi_modal_data": {"image": pil_image}
        }
        
        result_text = ""
        async for request_output in engine.generate(
            request_dict, 
            sampling_params, 
            request_id
        ):
            if request_output.outputs:
                result_text = request_output.outputs[0].text
        
        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        result = parse_ocr_output(result_text, pageIndex)
        result["timeMs"] = elapsed_ms
        
        print(f"  Done in {elapsed_ms}ms ({len(result_text)} chars)\n")
        
        return result
        
    except Exception as e:
        print(f"\n  Error: {e}\n")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")

@app.post("/v1/parse/semantic")
async def parse_semantic(request: SemanticRequest):
    text = request.text
    entities = []
    
    dates = re.findall(r'\b\d{4}-\d{2}-\d{2}\b|\b\d{2}/\d{2}/\d{4}\b', text)
    for date in dates:
        entities.append({"type": "DATE", "value": date, "conf": 0.9, "normalized": date})
    
    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    for email in emails:
        entities.append({"type": "EMAIL", "value": email, "conf": 0.95, "normalized": email})
    
    return {
        "detectedDocType": {"type": "Document", "score": 0.8},
        "entities": entities,
        "fields": {
            "content": {
                "value": text[:500] if len(text) > 500 else text,
                "conf": 0.9,
                "source": {"page": 0, "wordIds": []}
            }
        }
    }

if __name__ == "__main__":
    print("\n" + "="*70)
    print("DEEPSEEK OCR SERVER")
    print("="*70)
    print(f"Model: {MODEL_PATH}")
    print("Server: http://0.0.0.0:8000")
    print("="*70 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
