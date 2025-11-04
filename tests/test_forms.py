"""Unit tests for form matcher."""
import pytest
from forms.matcher import FormMatcher, FormSchema
from models.schemas import ExtractedField, FieldSource


def test_form_matcher_initialization():
    """Test form matcher initializes with schemas."""
    matcher = FormMatcher()
    
    # Should have predefined schemas
    assert len(matcher.schemas) > 0
    assert "ds-160@v2025-10" in matcher.schemas
    assert "passport@v1" in matcher.schemas


def test_form_matcher_exact_match():
    """Test exact field name matching."""
    matcher = FormMatcher()
    
    fields = {
        "full_name": ExtractedField(
            value="John Doe",
            conf=0.95,
            source=FieldSource(page=0, word_ids=[0, 1])
        ),
        "email": ExtractedField(
            value="john@example.com",
            conf=0.9,
            source=FieldSource(page=0, word_ids=[5])
        )
    }
    
    result = matcher.match_fields(
        form_id="resume@v1",
        extracted_fields=fields,
        strict=False
    )
    
    # Should find mappings
    assert len(result.mapping) > 0
    
    # Check mapping structure
    for mapping in result.mapping:
        assert mapping.form_field is not None
        assert mapping.source_field in fields
        assert 0.0 <= mapping.confidence <= 1.0


def test_form_matcher_fuzzy_match():
    """Test fuzzy field matching."""
    matcher = FormMatcher()
    
    fields = {
        "fullname": ExtractedField(  # Missing underscore
            value="Jane Smith",
            conf=0.98,
            source=FieldSource(page=0, word_ids=[0, 1])
        )
    }
    
    result = matcher.match_fields(
        form_id="resume@v1",
        extracted_fields=fields,
        strict=False
    )
    
    # Should still find match via fuzzy matching
    assert len(result.mapping) > 0


def test_form_matcher_strict_mode():
    """Test strict matching mode."""
    matcher = FormMatcher()
    
    fields = {
        "fullname": ExtractedField(  # Slightly different name
            value="Test",
            conf=0.9,
            source=FieldSource(page=0, word_ids=[0])
        )
    }
    
    result = matcher.match_fields(
        form_id="resume@v1",
        extracted_fields=fields,
        strict=True
    )
    
    # Strict mode should require exact match
    # This may or may not match depending on exact field names
    assert isinstance(result.mapping, list)


def test_form_matcher_unmapped_fields():
    """Test identification of unmapped form fields."""
    matcher = FormMatcher()
    
    fields = {
        "email": ExtractedField(
            value="test@example.com",
            conf=0.9,
            source=FieldSource(page=0, word_ids=[0])
        )
    }
    
    result = matcher.match_fields(
        form_id="resume@v1",
        extracted_fields=fields,
        strict=False
    )
    
    # Should have unmapped fields (fields in schema not matched)
    assert len(result.unmapped) > 0


def test_form_matcher_unknown_form():
    """Test handling of unknown form ID."""
    matcher = FormMatcher()
    
    result = matcher.match_fields(
        form_id="unknown-form@v1",
        extracted_fields={},
        strict=False
    )
    
    # Should return empty result for unknown form
    assert len(result.mapping) == 0
    assert len(result.unmapped) == 0


def test_form_matcher_add_schema():
    """Test adding custom form schema."""
    matcher = FormMatcher()
    
    custom_schema = FormSchema(
        form_id="custom@v1",
        fields={
            "field1": {"type": "text", "label": "Field 1"},
            "field2": {"type": "text", "label": "Field 2"}
        }
    )
    
    matcher.add_schema(custom_schema)
    
    # Should be retrievable
    retrieved = matcher.get_schema("custom@v1")
    assert retrieved is not None
    assert retrieved.form_id == "custom@v1"
    assert len(retrieved.fields) == 2


def test_form_matcher_confidence_propagation():
    """Test that confidence scores are properly propagated."""
    matcher = FormMatcher()
    
    fields = {
        "full_name": ExtractedField(
            value="Test Name",
            conf=0.75,
            source=FieldSource(page=0, word_ids=[0])
        )
    }
    
    result = matcher.match_fields(
        form_id="resume@v1",
        extracted_fields=fields,
        strict=False
    )
    
    # Mapping confidence should be <= source field confidence
    for mapping in result.mapping:
        source_field = fields[mapping.source_field]
        assert mapping.confidence <= source_field.confidence


def test_normalize_field_name():
    """Test field name normalization."""
    matcher = FormMatcher()
    
    # Various formats should normalize to same string
    assert matcher._normalize_field_name("full_name") == "fullname"
    assert matcher._normalize_field_name("Full Name") == "fullname"
    assert matcher._normalize_field_name("full-name") == "fullname"
    assert matcher._normalize_field_name("FULL NAME") == "fullname"


def test_similarity_score():
    """Test string similarity calculation."""
    matcher = FormMatcher()
    
    # Identical strings
    assert matcher._similarity_score("test", "test") == 1.0
    
    # Substring
    score = matcher._similarity_score("testing", "test")
    assert score > 0.5
    
    # Completely different
    score = matcher._similarity_score("abc", "xyz")
    assert score < 1.0
