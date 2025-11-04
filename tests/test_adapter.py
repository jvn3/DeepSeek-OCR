"""Unit tests for inference adapters."""
import pytest
from inference.adapter import MockAdapter, OCRResult
from models.schemas import DocType


def test_mock_adapter_initialization():
    """Test mock adapter initializes correctly."""
    adapter = MockAdapter()
    assert adapter.is_ready() is True


def test_mock_adapter_ocr_image():
    """Test mock OCR processing."""
    adapter = MockAdapter()
    
    # Mock image data
    image_data = b"fake image bytes"
    
    result = adapter.ocr_image(
        image_data=image_data,
        language_hint="en",
        return_layout=True,
        return_words=True
    )
    
    # Check result structure
    assert isinstance(result, OCRResult)
    assert result.text is not None
    assert len(result.text) > 0
    assert result.blocks is not None
    assert result.lines is not None
    assert result.words is not None
    assert result.language == "en"
    assert result.processing_time_ms > 0


def test_mock_adapter_ocr_without_layout():
    """Test OCR with layout disabled."""
    adapter = MockAdapter()
    
    result = adapter.ocr_image(
        image_data=b"test",
        return_layout=False,
        return_words=False
    )
    
    assert result.text is not None
    assert len(result.blocks) == 0
    assert len(result.lines) == 0
    assert len(result.words) == 0


def test_mock_adapter_classify_doc_type():
    """Test document classification."""
    adapter = MockAdapter()
    
    classification = adapter.classify_doc_type(
        text="This is a test document",
        layout=None
    )
    
    assert classification.type is not None
    assert 0.0 <= classification.score <= 1.0


def test_mock_adapter_extract_entities():
    """Test entity extraction."""
    adapter = MockAdapter()
    
    entities, fields = adapter.extract_entities(
        doc_type=DocType.GENERIC,
        text="John Doe john.doe@example.com",
        layout=None
    )
    
    # Should extract some entities
    assert len(entities) > 0
    
    # Should extract some fields
    assert len(fields) > 0
    
    # Check entity structure
    for entity in entities:
        assert entity.label is not None
        assert entity.text is not None
        assert 0.0 <= entity.confidence <= 1.0
    
    # Check field structure
    for key, field in fields.items():
        assert field.value is not None
        assert 0.0 <= field.confidence <= 1.0
        assert field.source is not None


def test_mock_adapter_bbox_format():
    """Test that bounding boxes are correctly formatted."""
    adapter = MockAdapter()
    
    result = adapter.ocr_image(
        image_data=b"test",
        return_words=True
    )
    
    for word in result.words:
        bbox = word.bbox
        assert len(bbox) == 4
        assert all(0.0 <= coord <= 1.0 for coord in bbox)
        assert bbox[0] < bbox[2]  # x1 < x2
        assert bbox[1] < bbox[3]  # y1 < y2


def test_mock_adapter_confidence_ranges():
    """Test that confidence scores are in valid range."""
    adapter = MockAdapter()
    
    result = adapter.ocr_image(image_data=b"test")
    
    # Check block confidences
    for block in result.blocks:
        assert 0.0 <= block.confidence <= 1.0
    
    # Check line confidences
    for line in result.lines:
        assert 0.0 <= line.confidence <= 1.0
    
    # Check word confidences
    for word in result.words:
        assert 0.0 <= word.confidence <= 1.0
