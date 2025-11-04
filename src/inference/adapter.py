"""
Inference adapter abstraction for OCR and document understanding.

Provides a clean interface for OCR processing, document classification,
and entity extraction, with both DeepSeek and mock implementations.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
import io
import time
import torch
import numpy as np
from PIL import Image

from models.schemas import (
    Word, Line, Block, Entity, ExtractedField, FieldSource,
    DocTypeClassification, DocType, BBox
)


class OCRResult:
    """Container for OCR processing results."""
    
    def __init__(
        self,
        text: str,
        blocks: List[Block],
        lines: List[Line],
        words: List[Word],
        language: Optional[str] = None,
        processing_time_ms: float = 0.0
    ):
        self.text = text
        self.blocks = blocks
        self.lines = lines
        self.words = words
        self.language = language
        self.processing_time_ms = processing_time_ms


class InferenceAdapter(ABC):
    """Abstract base class for OCR inference adapters."""
    
    @abstractmethod
    def ocr_image(
        self,
        image_data: bytes,
        language_hint: Optional[str] = None,
        return_layout: bool = True,
        return_words: bool = True,
        redaction_masks: Optional[List[BBox]] = None
    ) -> OCRResult:
        """
        Perform OCR on a single image.
        
        Args:
            image_data: Raw image bytes (PNG/JPEG/TIFF)
            language_hint: ISO 639-1 language code
            return_layout: Whether to return block/line layout
            return_words: Whether to return word-level details
            redaction_masks: Regions to skip/redact from OCR
            
        Returns:
            OCRResult with text, layout, and metadata
        """
        pass
    
    @abstractmethod
    def classify_doc_type(
        self,
        text: str,
        layout: Optional[Dict[str, Any]] = None
    ) -> DocTypeClassification:
        """
        Classify document type from OCR output.
        
        Args:
            text: Extracted text
            layout: Optional layout information
            
        Returns:
            Document type classification with confidence score
        """
        pass
    
    @abstractmethod
    def extract_entities(
        self,
        doc_type: DocType,
        text: str,
        layout: Optional[Dict[str, Any]] = None,
        hints: Optional[Dict[str, str]] = None
    ) -> Tuple[List[Entity], Dict[str, ExtractedField]]:
        """
        Extract entities and structured fields from document.
        
        Args:
            doc_type: Document type (or AUTO for detection)
            text: Extracted text
            layout: Optional layout information
            hints: Additional extraction hints (country, dateFormat, etc)
            
        Returns:
            Tuple of (entities list, fields dict)
        """
        pass
    
    @abstractmethod
    def is_ready(self) -> bool:
        """Check if the adapter is ready for inference."""
        pass


class DeepSeekAdapter(InferenceAdapter):
    """DeepSeek-OCR model adapter implementation."""
    
    def __init__(self, model_path: str, device: str = "cuda"):
        """
        Initialize DeepSeek OCR adapter.
        
        Args:
            model_path: Path to DeepSeek-OCR model
            device: Device to run inference on (cuda/cpu)
        """
        self.model_path = model_path
        self.device = device
        self.model = None
        self.processor = None
        self._ready = False
        
        # Import DeepSeek components
        try:
            import sys
            sys.path.append('/data/DeepSeek-OCR/DeepSeek-OCR-master/DeepSeek-OCR-vllm')
            from process.image_process import DeepseekOCRProcessor
            from vllm import LLM, SamplingParams
            
            self.processor = DeepseekOCRProcessor()
            
            # Initialize vLLM model
            self.model = LLM(
                model=model_path,
                trust_remote_code=True,
                gpu_memory_utilization=0.9,
                max_model_len=8192,
                limit_mm_per_prompt={"image": 10}
            )
            
            self.sampling_params = SamplingParams(
                temperature=0.0,
                max_tokens=4096,
                stop_token_ids=[self.processor.tokenizer.eos_token_id]
            )
            
            self._ready = True
            
        except Exception as e:
            print(f"Error initializing DeepSeek adapter: {e}")
            self._ready = False
    
    def ocr_image(
        self,
        image_data: bytes,
        language_hint: Optional[str] = None,
        return_layout: bool = True,
        return_words: bool = True,
        redaction_masks: Optional[List[BBox]] = None
    ) -> OCRResult:
        """Perform OCR using DeepSeek-OCR model."""
        start_time = time.time()
        
        # Load image
        image = Image.open(io.BytesIO(image_data))
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Process image with DeepSeek processor
        from config import PROMPT
        
        # Generate OCR output
        outputs = self.model.generate(
            [{
                "prompt": PROMPT,
                "multi_modal_data": {"image": [image]}
            }],
            sampling_params=self.sampling_params
        )
        
        # Extract text from output
        raw_text = outputs[0].outputs[0].text
        
        # Parse the output to extract structured layout
        blocks, lines, words = self._parse_layout(raw_text, image.size)
        
        processing_time = (time.time() - start_time) * 1000
        
        return OCRResult(
            text=raw_text,
            blocks=blocks if return_layout else [],
            lines=lines if return_layout else [],
            words=words if return_words else [],
            language=language_hint or "en",
            processing_time_ms=processing_time
        )
    
    def _parse_layout(
        self,
        text: str,
        image_size: Tuple[int, int]
    ) -> Tuple[List[Block], List[Line], List[Word]]:
        """
        Parse OCR output into structured layout.
        
        This is a simplified parser. For production, implement proper
        markdown/grounding token parsing based on DeepSeek-OCR format.
        """
        blocks = []
        lines = []
        words = []
        
        # Simple paragraph splitting
        paragraphs = text.split('\n\n')
        
        for block_idx, para in enumerate(paragraphs):
            if not para.strip():
                continue
            
            # Create block
            block = Block(
                text=para,
                bbox=[0.0, 0.0, 1.0, 1.0],  # Placeholder
                conf=0.95,
                block_type="text"
            )
            blocks.append(block)
            
            # Split into lines
            para_lines = para.split('\n')
            for line_text in para_lines:
                if not line_text.strip():
                    continue
                    
                line = Line(
                    text=line_text,
                    bbox=[0.0, 0.0, 1.0, 1.0],  # Placeholder
                    conf=0.95
                )
                lines.append(line)
                
                # Split into words
                for word_text in line_text.split():
                    word = Word(
                        text=word_text,
                        bbox=[0.0, 0.0, 1.0, 1.0],  # Placeholder
                        conf=0.95
                    )
                    words.append(word)
        
        return blocks, lines, words
    
    def classify_doc_type(
        self,
        text: str,
        layout: Optional[Dict[str, Any]] = None
    ) -> DocTypeClassification:
        """Classify document type using keyword matching and heuristics."""
        text_lower = text.lower()
        
        # Simple keyword-based classification
        if "passport" in text_lower or "travel document" in text_lower:
            return DocTypeClassification(type="passport", score=0.9)
        elif "resume" in text_lower or "curriculum vitae" in text_lower or "cv" in text_lower:
            return DocTypeClassification(type="resume", score=0.85)
        elif "invoice" in text_lower or "bill to" in text_lower:
            return DocTypeClassification(type="invoice", score=0.88)
        elif "receipt" in text_lower and "total" in text_lower:
            return DocTypeClassification(type="receipt", score=0.86)
        elif "ds-160" in text_lower or "nonimmigrant visa" in text_lower:
            return DocTypeClassification(type="form_ds160", score=0.92)
        else:
            return DocTypeClassification(type="generic", score=0.6)
    
    def extract_entities(
        self,
        doc_type: DocType,
        text: str,
        layout: Optional[Dict[str, Any]] = None,
        hints: Optional[Dict[str, str]] = None
    ) -> Tuple[List[Entity], Dict[str, ExtractedField]]:
        """Extract entities and fields using pattern matching."""
        entities = []
        fields = {}
        
        # Simple regex-based extraction (expand for production)
        import re
        
        # Extract dates
        date_pattern = r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})\b'
        for match in re.finditer(date_pattern, text):
            entities.append(Entity(
                label="DATE",
                text=match.group(0),
                conf=0.85,
                start_char=match.start(),
                end_char=match.end()
            ))
        
        # Extract emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        for match in re.finditer(email_pattern, text):
            entities.append(Entity(
                label="EMAIL",
                text=match.group(0),
                conf=0.9,
                start_char=match.start(),
                end_char=match.end()
            ))
            
            fields["email"] = ExtractedField(
                value=match.group(0),
                conf=0.9,
                source=FieldSource(page=0, word_ids=[])
            )
        
        # Document-type specific extraction
        if doc_type == DocType.PASSPORT or "passport" in doc_type.value:
            self._extract_passport_fields(text, fields, entities)
        elif doc_type == DocType.RESUME or "resume" in doc_type.value:
            self._extract_resume_fields(text, fields, entities)
        
        return entities, fields
    
    def _extract_passport_fields(
        self,
        text: str,
        fields: Dict[str, ExtractedField],
        entities: List[Entity]
    ):
        """Extract passport-specific fields."""
        import re
        
        # Passport number (simplified pattern)
        passport_pattern = r'\b[A-Z]{1,2}\d{7,9}\b'
        match = re.search(passport_pattern, text)
        if match:
            fields["passport_number"] = ExtractedField(
                value=match.group(0),
                conf=0.9,
                source=FieldSource(page=0, word_ids=[])
            )
    
    def _extract_resume_fields(
        self,
        text: str,
        fields: Dict[str, ExtractedField],
        entities: List[Entity]
    ):
        """Extract resume-specific fields."""
        # Name extraction (first line heuristic)
        lines = text.split('\n')
        if lines:
            potential_name = lines[0].strip()
            if len(potential_name.split()) <= 4 and len(potential_name) < 50:
                fields["full_name"] = ExtractedField(
                    value=potential_name,
                    conf=0.75,
                    source=FieldSource(page=0, word_ids=[])
                )
                
                entities.append(Entity(
                    label="PERSON",
                    text=potential_name,
                    conf=0.75
                ))
    
    def is_ready(self) -> bool:
        """Check if model is loaded and ready."""
        return self._ready


class MockAdapter(InferenceAdapter):
    """Mock adapter for testing without model dependencies."""
    
    def __init__(self):
        self._ready = True
    
    def ocr_image(
        self,
        image_data: bytes,
        language_hint: Optional[str] = None,
        return_layout: bool = True,
        return_words: bool = True,
        redaction_masks: Optional[List[BBox]] = None
    ) -> OCRResult:
        """Return mock OCR results."""
        mock_text = "MOCK OCR OUTPUT\n\nThis is a test document.\nIt contains multiple lines.\n\nWith different paragraphs."
        
        words = [
            Word(text="MOCK", bbox=[0.1, 0.1, 0.2, 0.15], conf=0.99),
            Word(text="OCR", bbox=[0.21, 0.1, 0.3, 0.15], conf=0.99),
            Word(text="OUTPUT", bbox=[0.31, 0.1, 0.45, 0.15], conf=0.98),
        ]
        
        lines = [
            Line(text="MOCK OCR OUTPUT", bbox=[0.1, 0.1, 0.45, 0.15], conf=0.99),
            Line(text="This is a test document.", bbox=[0.1, 0.2, 0.6, 0.25], conf=0.97),
        ]
        
        blocks = [
            Block(
                text="MOCK OCR OUTPUT",
                bbox=[0.1, 0.1, 0.45, 0.15],
                conf=0.99,
                block_type="heading"
            ),
            Block(
                text="This is a test document.\nIt contains multiple lines.",
                bbox=[0.1, 0.2, 0.6, 0.35],
                conf=0.97,
                block_type="text"
            ),
        ]
        
        return OCRResult(
            text=mock_text,
            blocks=blocks if return_layout else [],
            lines=lines if return_layout else [],
            words=words if return_words else [],
            language=language_hint or "en",
            processing_time_ms=42.0
        )
    
    def classify_doc_type(
        self,
        text: str,
        layout: Optional[Dict[str, Any]] = None
    ) -> DocTypeClassification:
        """Return mock classification."""
        return DocTypeClassification(type="generic", score=0.85)
    
    def extract_entities(
        self,
        doc_type: DocType,
        text: str,
        layout: Optional[Dict[str, Any]] = None,
        hints: Optional[Dict[str, str]] = None
    ) -> Tuple[List[Entity], Dict[str, ExtractedField]]:
        """Return mock entities and fields."""
        entities = [
            Entity(
                label="PERSON",
                text="John Doe",
                conf=0.95,
                start_char=10,
                end_char=18
            ),
            Entity(
                label="DATE",
                text="2024-01-15",
                conf=0.9,
                start_char=50,
                end_char=60
            ),
        ]
        
        fields = {
            "full_name": ExtractedField(
                value="John Doe",
                conf=0.95,
                source=FieldSource(page=0, word_ids=[0, 1])
            ),
            "email": ExtractedField(
                value="john.doe@example.com",
                conf=0.92,
                source=FieldSource(page=0, word_ids=[5])
            ),
        }
        
        return entities, fields
    
    def is_ready(self) -> bool:
        """Mock adapter is always ready."""
        return self._ready
