"""FastAPI endpoint for DeepSeek OCR PDF processing."""
import io
import logging
import os
from pathlib import Path
import threading
from typing import Iterable, List, Tuple

import fitz
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image
import torch

from config import CROP_MODE, MODEL_PATH, PROMPT, MAX_CONCURRENCY
from deepseek_ocr import DeepseekOCRForCausalLM
from process.image_process import DeepseekOCRProcessor
from process.ngram_norepeat import NoRepeatNGramLogitsProcessor
from vllm import LLM, SamplingParams
from vllm.model_executor.models.registry import ModelRegistry

# Environment configuration to match the standalone scripts.
if torch.version.cuda == "11.8":
    os.environ.setdefault("TRITON_PTXAS_PATH", "/usr/local/cuda-11.8/bin/ptxas")
os.environ.setdefault("VLLM_USE_V1", "0")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

LOGGER = logging.getLogger("deepseek_ocr_api")
logging.basicConfig(level=logging.INFO)

DATA_ROOT = Path(os.environ.get("DEEPSEEK_OCR_DATA_ROOT", "/data"))
DATA_ROOT.mkdir(parents=True, exist_ok=True)

END_OF_SENTENCE_TOKEN = "<\uFF5Cend\u2581of\u2581sentence\uFF5C>"

ModelRegistry.register_model("DeepseekOCRForCausalLM", DeepseekOCRForCausalLM)

llm = LLM(
    model=MODEL_PATH,
    hf_overrides={"architectures": ["DeepseekOCRForCausalLM"]},
    block_size=256,
    enforce_eager=False,
    trust_remote_code=True,
    max_model_len=8192,
    swap_space=0,
    max_num_seqs=MAX_CONCURRENCY,
    tensor_parallel_size=1,
    gpu_memory_utilization=0.9,
    disable_mm_preprocessor_cache=True,
)

logits_processors = [
    NoRepeatNGramLogitsProcessor(
        ngram_size=20,
        window_size=50,
        whitelist_token_ids={128821, 128822},
    )
]

sampling_params = SamplingParams(
    temperature=0.0,
    max_tokens=8192,
    logits_processors=logits_processors,
    skip_special_tokens=False,
    include_stop_str_in_output=True,
)

processor = DeepseekOCRProcessor()
model_lock = threading.Lock()

app = FastAPI(title="DeepSeek OCR API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def normalise_component(value: str, fallback: str) -> str:
    value = value.strip()
    cleaned = "".join(
        ch if ch.isalnum() or ch in {"@", "-", "_", "."} else "_" for ch in value
    )
    cleaned = cleaned.strip("_")
    if not cleaned:
        cleaned = fallback
    if ".." in cleaned or "/" in cleaned or "\\" in cleaned:
        raise ValueError("Invalid path component")
    return cleaned


def store_pdf(pdf_bytes: bytes, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "wb") as pdf_file:
        pdf_file.write(pdf_bytes)


def pdf_to_images(pdf_path: Path, output_dir: Path, dpi: int = 144) -> Tuple[List[Image.Image], List[Path]]:
    images: List[Image.Image] = []
    image_paths: List[Path] = []
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_document = fitz.open(pdf_path)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    Image.MAX_IMAGE_PIXELS = None

    try:
        for page_index in range(pdf_document.page_count):
            page = pdf_document[page_index]
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            buffer = io.BytesIO(pixmap.tobytes("png"))
            image = Image.open(buffer).convert("RGB")
            image_path = output_dir / f"page_{page_index:04d}.jpg"
            image.save(image_path, format="JPEG", quality=95)
            images.append(image)
            image_paths.append(image_path)
    finally:
        pdf_document.close()

    return images, image_paths


def run_inference(images: Iterable[Image.Image], prompt: str) -> List[str]:
    cache_items = []
    for image in images:
        tokenized = processor.tokenize_with_images(
            images=[image],
            bos=True,
            eos=True,
            cropping=CROP_MODE,
        )
        cache_items.append({"prompt": prompt, "multi_modal_data": {"image": tokenized}})

    if not cache_items:
        return []

    with model_lock:
        outputs = llm.generate(cache_items, sampling_params=sampling_params)

    page_texts: List[str] = []
    for output in outputs:
        text = output.outputs[0].text or ""
        text = text.replace(END_OF_SENTENCE_TOKEN, "").strip()
        page_texts.append(text)

    return page_texts


def handle_request(
    user_email: str,
    prompt: str,
    original_filename: str,
    pdf_bytes: bytes,
) -> dict:
    if not original_filename.lower().endswith(".pdf"):
        raise ValueError("Only PDF files are supported")

    email_component = normalise_component(user_email, "user")
    pdf_name = normalise_component(Path(original_filename).stem, "document")

    base_dir = DATA_ROOT / email_component / "pdfs" / pdf_name
    screenshots_dir = base_dir / "screenshots"

    pdf_path = base_dir / f"{pdf_name}.pdf"
    store_pdf(pdf_bytes, pdf_path)

    if screenshots_dir.exists():
        for item in screenshots_dir.iterdir():
            if item.is_file():
                item.unlink()

    images, image_paths = pdf_to_images(pdf_path, screenshots_dir)

    if not images:
        raise ValueError("The supplied PDF has no pages")

    final_prompt = prompt.strip() if prompt and prompt.strip() else PROMPT

    page_texts = run_inference(images, final_prompt)

    output_path = base_dir / "output.mmd"
    with open(output_path, "w", encoding="utf-8") as outfile:
        for index, text in enumerate(page_texts, start=1):
            outfile.write(f"<--- Page {index} --->\n")
            outfile.write(text)
            outfile.write("\n\n")

    return {
        "user_email": user_email,
        "pdf_name": pdf_name,
        "base_directory": str(base_dir),
        "original_pdf": str(pdf_path),
        "screenshots": [str(path) for path in image_paths],
        "output_file": str(output_path),
        "page_count": len(page_texts),
        "pages": [
            {"index": idx + 1, "text": text}
            for idx, text in enumerate(page_texts)
        ],
    }


@app.post("/api/ocr/pdf")
async def process_pdf(
    user_email: str = Form(...),
    prompt: str = Form(PROMPT),
    file: UploadFile = File(...),
):
    if file.content_type not in {"application/pdf", "application/x-pdf", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="Uploaded file must be a PDF")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    try:
        result = await run_in_threadpool(
            handle_request,
            user_email,
            prompt,
            file.filename or "document.pdf",
            pdf_bytes,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:  # pragma: no cover - unexpected server error
        LOGGER.exception("PDF processing failed", exc_info=error)
        raise HTTPException(status_code=500, detail="Failed to process PDF") from error

    return JSONResponse(content=result)


@app.get("/health")
async def healthcheck() -> dict:
    return {"status": "ok"}
