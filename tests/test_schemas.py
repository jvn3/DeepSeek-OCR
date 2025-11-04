"""Unit tests for Pydantic schemas and models."""
import pytest
from pydantic import ValidationError
from models.schemas import (
    BBox, Word, Line, Block, OCRImageRequest, OCRImageResponse,
    Entity, ExtractedField, FieldSource, DocType, ErrorCode
)


def test_bbox_validation():
    """Test BBox coordinate validation."""
    # Valid bbox
    bbox = BBox(x1=0.1, y1=0.2, x2=0.5, y2=0.6)
    assert bbox.x1 == 0.1
    assert bbox.x2 == 0.5
    
    # Invalid: x2 <= x1
    with pytest.raises(ValidationError):
        BBox(x1=0.5, y1=0.2, x2=0.4, y2=0.6)
    
    # Invalid: y2 <= y1
    with pytest.raises(ValidationError):
        BBox(x1=0.1, y1=0.6, x2=0.5, y2=0.5)
    
    # Invalid: out of range
    with pytest.raises(ValidationError):
        BBox(x1=0.0, y1=0.0, x2=1.5, y2=0.5)


def test_word_model():
    """Test Word model."""
    word = Word(
        text="Hello",
        bbox=[0.1, 0.2, 0.3, 0.4],
        conf=0.95
    )
    
    assert word.text == "Hello"
    assert len(word.bbox) == 4
    assert word.confidence == 0.95
    
    # Test alias
    word2 = Word(text="World", bbox=[0.1, 0.2, 0.3, 0.4], confidence=0.9)
    assert word2.confidence == 0.9


def test_line_model():
    """Test Line model."""
    line = Line(
        text="Hello World",
        bbox=[0.1, 0.2, 0.5, 0.4],
        conf=0.92,
        word_ids=[0, 1]
    )
    
    assert line.text == "Hello World"
    assert line.word_ids == [0, 1]


def test_block_model():
    """Test Block model."""
    block = Block(
        text="Paragraph text",
        bbox=[0.0, 0.0, 1.0, 0.5],
        conf=0.9,
        block_type="text",
        line_ids=[0, 1, 2]
    )
    
    assert block.block_type == "text"
    assert len(block.line_ids) == 3


def test_ocr_image_request():
    """Test OCRImageRequest model."""
    request = OCRImageRequest(
        doc_type=DocType.PASSPORT,
        language_hint="en",
        return_layout=True,
        page_index=5
    )
    
    assert request.doc_type == DocType.PASSPORT
    assert request.language_hint == "en"
    assert request.page_index == 5


def test_ocr_image_response():
    """Test OCRImageResponse model."""
    from models.schemas import Provenance
    
    response = OCRImageResponse(
        page_index=0,
        text="Extracted text",
        blocks=[],
        lines=[],
        words=[],
        language="en",
        time_ms=125.5,
        provenance=Provenance(engine="deepseek-ocr", version="1.0.0")
    )
    
    assert response.page_index == 0
    assert response.text == "Extracted text"
    assert response.time_ms == 125.5


def test_entity_model():
    """Test Entity model."""
    entity = Entity(
        label="PERSON",
        text="John Doe",
        conf=0.95,
        start_char=10,
        end_char=18,
        page=0
    )
    
    assert entity.label == "PERSON"
    assert entity.text == "John Doe"
    assert entity.confidence == 0.95


def test_extracted_field():
    """Test ExtractedField model."""
    field = ExtractedField(
        value="test@example.com",
        conf=0.9,
        source=FieldSource(page=0, word_ids=[5, 6])
    )
    
    assert field.value == "test@example.com"
    assert field.confidence == 0.9
    assert field.source.page == 0


def test_field_source():
    """Test FieldSource model."""
    source = FieldSource(page=2, word_ids=[10, 11, 12])
    
    assert source.page == 2
    assert len(source.word_ids) == 3


def test_doc_type_enum():
    """Test DocType enum."""
    assert DocType.AUTO == "auto"
    assert DocType.PASSPORT == "passport"
    assert DocType.RESUME == "resume"
    
    # Should be usable in model
    request = OCRImageRequest(doc_type=DocType.PASSPORT)
    assert request.doc_type == DocType.PASSPORT


def test_error_code_enum():
    """Test ErrorCode enum."""
    assert ErrorCode.RATE_LIMITED == "RATE_LIMITED"
    assert ErrorCode.MODEL_UNAVAILABLE == "MODEL_UNAVAILABLE"
    assert ErrorCode.E2EE_REQUIRED == "E2EE_REQUIRED"


def test_confidence_validation():
    """Test confidence score validation."""
    # Valid confidence
    word = Word(text="test", bbox=[0.0, 0.0, 0.1, 0.1], conf=0.5)
    assert word.confidence == 0.5
    
    # Invalid: too high
    with pytest.raises(ValidationError):
        Word(text="test", bbox=[0.0, 0.0, 0.1, 0.1], conf=1.5)
    
    # Invalid: negative
    with pytest.raises(ValidationError):
        Word(text="test", bbox=[0.0, 0.0, 0.1, 0.1], conf=-0.1)


def test_model_serialization():
    """Test model JSON serialization."""
    word = Word(text="test", bbox=[0.1, 0.2, 0.3, 0.4], conf=0.95)
    
    # Serialize to dict
    data = word.model_dump()
    assert data["text"] == "test"
    assert data["bbox"] == [0.1, 0.2, 0.3, 0.4]
    
    # Serialize to JSON
    json_str = word.model_dump_json()
    assert "test" in json_str
    assert "0.95" in json_str


def test_model_deserialization():
    """Test model JSON deserialization."""
    data = {
        "text": "hello",
        "bbox": [0.1, 0.2, 0.3, 0.4],
        "conf": 0.88
    }
    
    word = Word(**data)
    assert word.text == "hello"
    assert word.confidence == 0.88
