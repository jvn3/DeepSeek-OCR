"""Form matching utilities for mapping extracted fields to form schemas."""
from typing import Dict, List, Optional
from models.schemas import (
    ExtractedField, FieldMapping, FormMatchRequest, FormMatchResponse
)


class FormSchema:
    """Represents a form schema with field definitions."""
    
    def __init__(self, form_id: str, fields: Dict[str, Dict[str, str]]):
        """
        Initialize form schema.
        
        Args:
            form_id: Unique form identifier (e.g., ds-160@v2025-10)
            fields: Dictionary mapping form field paths to metadata
                    e.g., {"applicant.fullName": {"type": "text", "label": "Full Name"}}
        """
        self.form_id = form_id
        self.fields = fields


# Form schema definitions
FORM_SCHEMAS: Dict[str, FormSchema] = {
    "ds-160@v2025-10": FormSchema(
        form_id="ds-160@v2025-10",
        fields={
            "applicant.fullName": {"type": "text", "label": "Full Name"},
            "applicant.surname": {"type": "text", "label": "Surname"},
            "applicant.givenName": {"type": "text", "label": "Given Name"},
            "applicant.birth.date": {"type": "date", "label": "Date of Birth"},
            "applicant.birth.city": {"type": "text", "label": "City of Birth"},
            "applicant.birth.country": {"type": "text", "label": "Country of Birth"},
            "applicant.nationality": {"type": "text", "label": "Nationality"},
            "applicant.gender": {"type": "select", "label": "Gender"},
            "passport.number": {"type": "text", "label": "Passport Number"},
            "passport.issueDate": {"type": "date", "label": "Passport Issue Date"},
            "passport.expirationDate": {"type": "date", "label": "Passport Expiration Date"},
            "passport.issuingCountry": {"type": "text", "label": "Passport Issuing Country"},
            "contact.address.street": {"type": "text", "label": "Street Address"},
            "contact.address.city": {"type": "text", "label": "City"},
            "contact.address.state": {"type": "text", "label": "State/Province"},
            "contact.address.postalCode": {"type": "text", "label": "Postal Code"},
            "contact.address.country": {"type": "text", "label": "Country"},
            "contact.phone": {"type": "text", "label": "Phone Number"},
            "contact.email": {"type": "email", "label": "Email Address"},
            "travel.purpose": {"type": "select", "label": "Purpose of Trip"},
            "travel.arrivalDate": {"type": "date", "label": "Intended Arrival Date"},
            "travel.departureDate": {"type": "date", "label": "Intended Departure Date"},
            "travel.itinerary.returnDate": {"type": "date", "label": "Return Date"},
        }
    ),
    "passport@v1": FormSchema(
        form_id="passport@v1",
        fields={
            "fullName": {"type": "text", "label": "Full Name"},
            "surname": {"type": "text", "label": "Surname"},
            "givenNames": {"type": "text", "label": "Given Names"},
            "nationality": {"type": "text", "label": "Nationality"},
            "dateOfBirth": {"type": "date", "label": "Date of Birth"},
            "placeOfBirth": {"type": "text", "label": "Place of Birth"},
            "passportNumber": {"type": "text", "label": "Passport Number"},
            "issueDate": {"type": "date", "label": "Issue Date"},
            "expiryDate": {"type": "date", "label": "Expiry Date"},
            "issuingAuthority": {"type": "text", "label": "Issuing Authority"},
            "sex": {"type": "select", "label": "Sex"},
        }
    ),
    "resume@v1": FormSchema(
        form_id="resume@v1",
        fields={
            "personalInfo.fullName": {"type": "text", "label": "Full Name"},
            "personalInfo.email": {"type": "email", "label": "Email"},
            "personalInfo.phone": {"type": "text", "label": "Phone"},
            "personalInfo.address": {"type": "text", "label": "Address"},
            "personalInfo.linkedin": {"type": "url", "label": "LinkedIn"},
            "personalInfo.github": {"type": "url", "label": "GitHub"},
            "summary": {"type": "textarea", "label": "Professional Summary"},
            "education.degree": {"type": "text", "label": "Degree"},
            "education.institution": {"type": "text", "label": "Institution"},
            "education.graduationDate": {"type": "date", "label": "Graduation Date"},
            "skills": {"type": "array", "label": "Skills"},
        }
    ),
}


class FormMatcher:
    """Matches extracted fields to form schemas."""
    
    def __init__(self):
        self.schemas = FORM_SCHEMAS
    
    def match_fields(
        self,
        form_id: str,
        extracted_fields: Dict[str, ExtractedField],
        strict: bool = False
    ) -> FormMatchResponse:
        """
        Match extracted fields to a form schema.
        
        Args:
            form_id: Target form identifier
            extracted_fields: Dictionary of extracted fields
            strict: If True, require exact field name matches
            
        Returns:
            FormMatchResponse with mappings and unmapped fields
        """
        if form_id not in self.schemas:
            # Return empty response for unknown forms
            return FormMatchResponse(
                form_id=form_id,
                mapping=[],
                unmapped=[]
            )
        
        schema = self.schemas[form_id]
        mappings: List[FieldMapping] = []
        mapped_form_fields = set()
        
        # Try to match each extracted field to form fields
        for extracted_key, extracted_field in extracted_fields.items():
            best_match = self._find_best_match(
                extracted_key,
                schema.fields,
                strict=strict
            )
            
            if best_match:
                form_field, confidence_boost = best_match
                mapping_confidence = min(
                    extracted_field.confidence * confidence_boost,
                    1.0
                )
                
                mappings.append(FieldMapping(
                    form_field=form_field,
                    source_field=extracted_key,
                    confidence=mapping_confidence
                ))
                mapped_form_fields.add(form_field)
        
        # Find unmapped form fields
        unmapped = [
            field for field in schema.fields.keys()
            if field not in mapped_form_fields
        ]
        
        return FormMatchResponse(
            form_id=form_id,
            mapping=mappings,
            unmapped=unmapped
        )
    
    def _find_best_match(
        self,
        extracted_key: str,
        form_fields: Dict[str, Dict[str, str]],
        strict: bool = False
    ) -> Optional[tuple[str, float]]:
        """
        Find the best matching form field for an extracted field.
        
        Args:
            extracted_key: Extracted field key (e.g., "full_name")
            form_fields: Form schema fields
            strict: Require exact matches
            
        Returns:
            Tuple of (form_field_path, confidence_multiplier) or None
        """
        extracted_normalized = self._normalize_field_name(extracted_key)
        
        # Try exact match first
        for form_field in form_fields.keys():
            form_normalized = self._normalize_field_name(
                form_field.split('.')[-1]  # Use last segment for matching
            )
            
            if extracted_normalized == form_normalized:
                return (form_field, 1.0)
        
        if strict:
            return None
        
        # Try fuzzy matching
        best_match = None
        best_score = 0.0
        
        for form_field, metadata in form_fields.items():
            # Check field name similarity
            form_normalized = self._normalize_field_name(
                form_field.split('.')[-1]
            )
            name_score = self._similarity_score(extracted_normalized, form_normalized)
            
            # Check label similarity
            label = metadata.get("label", "")
            label_normalized = self._normalize_field_name(label)
            label_score = self._similarity_score(extracted_normalized, label_normalized)
            
            score = max(name_score, label_score)
            
            if score > best_score and score > 0.6:  # Threshold for fuzzy matching
                best_score = score
                best_match = form_field
        
        if best_match:
            return (best_match, best_score)
        
        return None
    
    @staticmethod
    def _normalize_field_name(name: str) -> str:
        """Normalize field name for comparison."""
        import re
        # Remove special characters, convert to lowercase
        normalized = re.sub(r'[^a-z0-9]', '', name.lower())
        return normalized
    
    @staticmethod
    def _similarity_score(s1: str, s2: str) -> float:
        """
        Calculate similarity score between two strings.
        
        Uses simple character overlap ratio. For production, consider
        more sophisticated algorithms like Levenshtein distance or
        semantic similarity.
        """
        if not s1 or not s2:
            return 0.0
        
        if s1 == s2:
            return 1.0
        
        # Check if one contains the other
        if s1 in s2 or s2 in s1:
            return 0.9
        
        # Character overlap
        set1 = set(s1)
        set2 = set(s2)
        overlap = len(set1 & set2)
        total = len(set1 | set2)
        
        if total == 0:
            return 0.0
        
        return overlap / total
    
    def add_schema(self, schema: FormSchema) -> None:
        """Add a new form schema."""
        self.schemas[schema.form_id] = schema
    
    def get_schema(self, form_id: str) -> Optional[FormSchema]:
        """Get a form schema by ID."""
        return self.schemas.get(form_id)


# Global form matcher instance
_form_matcher = FormMatcher()


def get_form_matcher() -> FormMatcher:
    """Get the global form matcher instance."""
    return _form_matcher
