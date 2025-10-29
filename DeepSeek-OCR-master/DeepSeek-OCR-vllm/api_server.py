"""FastAPI endpoint for DeepSeek OCR PDF processing."""
import io
import json
import logging
import os
import re
from pathlib import Path
import threading
from typing import Iterable, List, Tuple, Dict, Any, Optional

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


TOKEN_PATTERN = re.compile(
    r"<\|ref\|>(?P<kind>[^<]+)<\|/ref\|><\|det\|>\[\[(?P<bbox>[^\]]+)\]\]<\|/det\|>\n?(?P<content>.*?)(?=(<\|ref\|>|$))",
    re.DOTALL,
)

FIELD_KEYWORDS = (
    "name",
    "date",
    "number",
    "address",
    "telephone",
    "phone",
    "email",
    "country",
    "city",
    "state",
    "zip",
    "postal",
    "registration",
    "account",
    "uscis",
    "investment",
    "capital",
    "job",
    "employees",
    "signature",
    "citizenship",
    "residence",
    "sex",
    "birth",
    "status",
)

MAX_STRUCTURED_FIELDS = 150
def _parse_bbox(raw: str) -> List[int]:
    parts: List[float] = []
    for fragment in raw.split(","):
        fragment = fragment.strip()
        if not fragment:
            continue
        try:
            parts.append(float(fragment))
        except ValueError:
            continue
    if len(parts) >= 4:
        x1, y1, x2, y2 = parts[:4]
        width = max(1.0, x2 - x1)
        height = max(1.0, y2 - y1)
        return [int(round(x1)), int(round(y1)), int(round(width)), int(round(height))]
    return [0, 0, 0, 0]


def _clean_whitespace(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _clean_heading(text: str) -> str:
    if not text:
        return ""
    text = text.strip().lstrip("#").strip()
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = _clean_whitespace(text)
    return text.rstrip(":")


def _clean_label(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = text.replace("__", "_")
    return _clean_whitespace(text)


def _is_possible_field_label(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    if lowered.startswith(("note", "please", "important")):
        return False
    if "instructions" in lowered or ("see" in lowered and "part" in lowered):
        return False
    if len(text) < 3:
        return False
    if re.match(r"^[0-9]+[\.)]\s*$", text):
        return False
    if re.match(r"^[0-9]+[\.)]\s", text):
        return True
    return any(keyword in lowered for keyword in FIELD_KEYWORDS)


def _infer_field_type(label: str, token_type: str) -> str:
    lowered = (label or "").lower()
    token_type = (token_type or "").lower()
    if token_type == "checkbox":
        return "checkbox"
    if token_type == "radio":
        return "radio"
    if "email" in lowered:
        return "email"
    if "date" in lowered:
        return "date"
    if "telephone" in lowered or "phone" in lowered:
        return "tel"
    if "number" in lowered or "amount" in lowered or "total" in lowered:
        return "number"
    if "signature" in lowered:
        return "signature"
    if "sex" in lowered or "status" in lowered:
        return "select"
    return "text"


def _infer_options(field_type: str, label: str) -> List[Dict[str, str]]:
    lowered = (label or "").lower()
    if field_type in {"checkbox", "radio", "select"} and "yes" in lowered and "no" in lowered:
        return [
            {"id": "yes", "label": "Yes", "value": "yes"},
            {"id": "no", "label": "No", "value": "no"},
        ]
    return []


def _slugify(value: str, existing: set[str], fallback: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    if not base:
        base = fallback
    candidate = base
    counter = 2
    while candidate in existing:
        candidate = f"{base}-{counter}"
        counter += 1
    existing.add(candidate)
    return candidate


def _get_or_create_section(
    sections: List[Dict[str, Any]],
    index: Dict[str, Dict[str, Any]],
    title: str,
    page: int,
    used_section_ids: set[str],
) -> Dict[str, Any]:
    cleaned = _clean_heading(title) or f"Page {page}"
    slug = _slugify(cleaned, used_section_ids, "section")
    if slug not in index:
        section = {"id": slug, "title": cleaned, "page": page, "fields": []}
        index[slug] = section
        sections.append(section)
    return index[slug]


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
        ngram_size=10,  # Reduced for shorter patterns
        window_size=30,  # Reduced window
        whitelist_token_ids={128821, 128822},
    )
]

sampling_params = SamplingParams(
    temperature=0.1,  # Slight randomness to avoid loops
    max_tokens=4096,  # Reduced for cleaner output
    logits_processors=logits_processors,
    skip_special_tokens=False,
    include_stop_str_in_output=True,
    stop=["}]}", "}\n}", "```", "---"],  # Stop sequences for JSON completion
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


def parse_form_structure_from_text(page_texts: List[str]) -> Dict[str, Any]:
    """Parse the OCR output text to extract structured form data in the required JSON format."""
    # Combine all page texts to look for JSON structure
    combined_text = "\n".join(page_texts)
    
    LOGGER.info(f"Parsing form structure from {len(combined_text)} characters")
    
    # Check for repetitive content that indicates model issues
    if "Date types should be formatted" in combined_text and combined_text.count("Date types") > 5:
        LOGGER.warning("Detected repetitive model output, extracting meaningful content")
        
        # Extract meaningful parts before the repetition
        lines = combined_text.split('\n')
        meaningful_lines = []
        for line in lines:
            if "Date types should be formatted" in line:
                break
            if line.strip() and not line.startswith("For checkbox"):
                meaningful_lines.append(line.strip())
        
        combined_text = "\n".join(meaningful_lines[:50])  # Limit to first 50 meaningful lines
    
    # Try to extract JSON first
    try:
        json_start = combined_text.find('{')
        if json_start != -1:
            brace_count = 0
            json_end = -1
            for i, char in enumerate(combined_text[json_start:], json_start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break
            
            if json_end != -1:
                json_text = combined_text[json_start:json_end]
                json_text = json_text.replace('\n', ' ').replace('\r', ' ')
                json_text = ' '.join(json_text.split())
                
                parsed_json = json.loads(json_text)
                if isinstance(parsed_json, dict) and "title" in parsed_json:
                    LOGGER.info("Successfully parsed JSON structure from OCR output")
                    return validate_and_complete_json_structure(parsed_json)
    except (json.JSONDecodeError, ValueError) as e:
        LOGGER.debug(f"JSON parsing failed: {e}")
    
    # Parse grounding information if available
    return extract_form_structure_from_grounding(combined_text, page_texts)


def validate_and_complete_json_structure(parsed_json: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure the JSON structure has all required fields."""
    if "formId" not in parsed_json:
        parsed_json["formId"] = parsed_json.get("title", "UNKNOWN").replace(" ", "-").upper()
    
    if "sections" not in parsed_json:
        parsed_json["sections"] = []
    
    for section in parsed_json.get("sections", []):
        if "fields" not in section:
            section["fields"] = []
        
        for field in section.get("fields", []):
            if "bbox" not in field:
                field["bbox"] = [0, 0, 100, 20]
            if "options" not in field:
                field["options"] = []
            if "type" not in field:
                field["type"] = "text"
            if "page" not in field:
                field["page"] = 1
    
    return parsed_json


def extract_form_structure_from_grounding(combined_text: str, page_texts: List[str]) -> Dict[str, Any]:
    """Extract form structure from grounding tokens and OCR output."""

    LOGGER.info("Extracting form structure from grounding tokens")

    # Identify form id/title using heuristics
    form_id_patterns = (
        r"(Form\s+[A-Z]-?\d+)",
        r"(Form\s+[A-Z]{1,3}\s?\d{2,4})",
        r"(I-[0-9]{3})",
        r"(N-[0-9]{3})",
        r"(USCIS\s+Form\s+[A-Z0-9-]+)",
    )

    title_patterns = (
        r"form titled\s+\"([^\"]+)\"",
        r"titled\s+\"([^\"]+)\"",
        r"\"([^\"]*Request for[^\"]*)\"",
        r"\"([^\"]*Application[^\"]*)\"",
        r"\"([^\"]*Certification[^\"]*)\"",
    )

    extracted_form_id = None
    for pattern in form_id_patterns:
        match = re.search(pattern, combined_text, re.IGNORECASE)
        if match:
            extracted_form_id = _clean_whitespace(match.group(1))
            extracted_form_id = extracted_form_id.replace("USCIS", "").strip()
            LOGGER.info("Detected form identifier: %s", extracted_form_id)
            break

    extracted_title = None
    for pattern in title_patterns:
        match = re.search(pattern, combined_text, re.IGNORECASE)
        if match:
            extracted_title = _clean_heading(match.group(1))
            LOGGER.info("Detected form title text: %s", extracted_title)
            break

    if extracted_form_id and extracted_title:
        title = f"{extracted_form_id}: {extracted_title}"
        form_id = extracted_form_id.replace(" ", "-").replace(".", "").upper()
    elif extracted_form_id:
        title = extracted_form_id
        form_id = extracted_form_id.replace(" ", "-").replace(".", "").upper()
    elif extracted_title:
        title = extracted_title
        form_id = extracted_title.replace(" ", "-").replace(".", "").upper()[:24]
    else:
        title = "Unknown Form"
        # Try to fall back to page specific hints
        for page_text in page_texts:
            match = re.search(r"Form\s+[A-Z]-?\d+", page_text, re.IGNORECASE)
            if match:
                title = _clean_whitespace(match.group(0))
                break
        form_id = title.replace(" ", "-").replace(".", "").upper() or "UNKNOWN"

    LOGGER.info("Final title=%s form_id=%s", title, form_id)

    # Track cumulative page spans so we can map tokens back to pages
    page_spans: List[Tuple[int, int]] = []
    accumulator = 0
    for text in page_texts:
        start = accumulator
        accumulator += len(text)
        page_spans.append((start, accumulator))
        accumulator += 1  # account for newline join

    def locate_page(pos: int) -> int:
        for index, (start, end) in enumerate(page_spans):
            if start <= pos <= end:
                return index + 1
        return 1

    sections: List[Dict[str, Any]] = []
    section_index: Dict[str, Dict[str, Any]] = {}
    used_section_ids: set[str] = set()
    used_field_ids: set[str] = set()

    current_section: Optional[Dict[str, Any]] = None
    fields_added = 0

    for match in TOKEN_PATTERN.finditer(combined_text):
        if fields_added >= MAX_STRUCTURED_FIELDS:
            LOGGER.info("Reached structured field cap (%s)", MAX_STRUCTURED_FIELDS)
            break

        token_kind = _clean_whitespace(match.group("kind")).lower()
        raw_content = match.group("content")
        content = _clean_whitespace(raw_content)

        if not content:
            continue

        # Skip boilerplate paragraphs that are unlikely to be field labels
        if len(content) < 3:
            continue

        page = locate_page(match.start())
        bbox = _parse_bbox(match.group("bbox"))

        is_heading = False
        if token_kind in {"heading", "title", "section", "subheading"}:
            is_heading = True
        elif content.endswith(":") and len(content.split()) < 12:
            is_heading = True
        elif len(content.split()) <= 6 and content.isupper():
            is_heading = True

        if is_heading:
            current_section = _get_or_create_section(
                sections,
                section_index,
                content,
                page,
                used_section_ids,
            )
            continue

        if not _is_possible_field_label(content):
            continue

        section = current_section or _get_or_create_section(
            sections,
            section_index,
            f"Page {page}",
            page,
            used_section_ids,
        )

        field_type = _infer_field_type(content, token_kind)
        options = _infer_options(field_type, content)
        field_id = _slugify(content, used_field_ids, f"field-{fields_added+1}")

        section["fields"].append(
            {
                "id": field_id,
                "label": _clean_label(content),
                "type": field_type,
                "page": page,
                "bbox": bbox,
                "options": options,
            }
        )
        fields_added += 1

    # Drop empty sections
    sections = [section for section in sections if section.get("fields")]

    if not sections:
        LOGGER.info("No usable grounding tokens found; falling back to raw page text")
        fallback_sections = []
        for page_index, text in enumerate(page_texts, start=1):
            cleaned = _clean_whitespace(text)
            if not cleaned:
                continue
            fallback_sections.append(
                {
                    "id": f"page-{page_index}",
                    "title": f"Page {page_index}",
                    "page": page_index,
                    "fields": [
                        {
                            "id": f"page-{page_index}-content",
                            "label": "Extracted Text",
                            "type": "textarea",
                            "page": page_index,
                            "bbox": [0, 0, 0, 0],
                            "options": [],
                            "extracted_text": text[:500] + ("..." if len(text) > 500 else ""),
                        }
                    ],
                }
            )
        sections = fallback_sections

    return {
        "title": title,
        "formId": form_id or "UNKNOWN",
        "sections": sections,
    }


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

    # Parse the structured form data from OCR output
    form_structure = parse_form_structure_from_text(page_texts)

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
        # Add the structured form data
        "form_structure": form_structure,
        # Also include the form structure at root level for compatibility
        "title": form_structure.get("title", "Unknown Form"),
        "formId": form_structure.get("formId", "UNKNOWN"),
        "sections": form_structure.get("sections", [])
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
