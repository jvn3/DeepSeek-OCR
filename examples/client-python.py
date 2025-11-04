"""
Python client example for DeepSeek-OCR API with E2EE support
"""
import base64
import json
import requests
from typing import Optional, Dict, Any, Generator
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
import secrets


class DeepSeekOCRClient:
    """Python client for DeepSeek-OCR API with zero-knowledge E2EE."""
    
    def __init__(self, base_url: str, supabase_token: str):
        """
        Initialize client.
        
        Args:
            base_url: API base URL (e.g., http://localhost:8000)
            supabase_token: Supabase JWT token for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.token = supabase_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.token}'
        })
        
        # E2EE session state
        self.client_private_key: Optional[x25519.X25519PrivateKey] = None
        self.client_public_key: Optional[x25519.X25519PublicKey] = None
        self.server_public_key: Optional[x25519.X25519PublicKey] = None
        self.shared_secret: Optional[bytes] = None
    
    def init_session(self) -> None:
        """Initialize E2EE session with the server."""
        # Generate client X25519 key pair
        self.client_private_key = x25519.X25519PrivateKey.generate()
        self.client_public_key = self.client_private_key.public_key()
        
        # Fetch server's public key
        response = self.session.get(f'{self.base_url}/')
        response.raise_for_status()
        
        data = response.json()
        server_pubkey_b64 = data.get('e2ee', {}).get('server_pubkey')
        
        if server_pubkey_b64:
            server_pubkey_raw = base64.b64decode(server_pubkey_b64)
            self.server_public_key = x25519.X25519PublicKey.from_public_bytes(server_pubkey_raw)
            
            # Derive shared secret
            self.shared_secret = self.client_private_key.exchange(self.server_public_key)
            print("E2EE session initialized successfully")
        else:
            print("Server does not support E2EE")
    
    def _get_client_pubkey_header(self) -> Optional[str]:
        """Get client public key as base64 for header."""
        if not self.client_public_key:
            return None
        
        raw_bytes = self.client_public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        return base64.b64encode(raw_bytes).decode('utf-8')
    
    def _encrypt_data(self, plaintext: bytes) -> bytes:
        """Encrypt data using XChaCha20-Poly1305."""
        if not self.shared_secret:
            return plaintext
        
        nonce = secrets.token_bytes(24)
        cipher = ChaCha20Poly1305(self.shared_secret)
        ciphertext = cipher.encrypt(nonce, plaintext, None)
        
        # Prepend nonce
        return nonce + ciphertext
    
    def _decrypt_data(self, ciphertext: bytes) -> bytes:
        """Decrypt data using XChaCha20-Poly1305."""
        if not self.shared_secret:
            return ciphertext
        
        nonce = ciphertext[:24]
        encrypted = ciphertext[24:]
        
        cipher = ChaCha20Poly1305(self.shared_secret)
        plaintext = cipher.decrypt(nonce, encrypted, None)
        return plaintext
    
    def ocr_image(
        self,
        image_path: str,
        doc_type: str = 'auto',
        language_hint: Optional[str] = None,
        return_layout: bool = True,
        return_words: bool = True,
        page_index: int = 0,
        use_e2ee: bool = False
    ) -> Dict[str, Any]:
        """
        OCR a single image.
        
        Args:
            image_path: Path to image file
            doc_type: Document type hint
            language_hint: ISO 639-1 language code
            return_layout: Include layout information
            return_words: Include word-level details
            page_index: Page number
            use_e2ee: Encrypt the image payload
            
        Returns:
            OCR result dictionary
        """
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # Encrypt if E2EE is enabled
        headers = {}
        if use_e2ee and self.shared_secret:
            image_data = self._encrypt_data(image_data)
            headers['X-Client-Pubkey'] = self._get_client_pubkey_header()
        
        # Prepare multipart request
        files = {
            'image': ('image.png', image_data, 'image/png')
        }
        
        data = {
            'doc_type': doc_type,
            'return_layout': return_layout,
            'return_words': return_words,
            'page_index': page_index
        }
        
        if language_hint:
            data['language_hint'] = language_hint
        
        response = self.session.post(
            f'{self.base_url}/v1/ocr/image',
            files=files,
            data=data,
            headers=headers
        )
        response.raise_for_status()
        
        return response.json()
    
    def parse_semantic(
        self,
        text: str,
        layout: Optional[Dict] = None,
        hints: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Parse semantic content from OCR output.
        
        Args:
            text: Extracted text
            layout: Layout information
            hints: Additional hints (country, dateFormat, etc)
            
        Returns:
            Semantic parsing result
        """
        payload = {
            'doc_type': 'auto',
            'text': text
        }
        
        if layout:
            payload['layout'] = layout
        
        if hints:
            payload['hints'] = hints
        
        response = self.session.post(
            f'{self.base_url}/v1/parse/semantic',
            json=payload
        )
        response.raise_for_status()
        
        return response.json()
    
    def match_form(
        self,
        form_id: str,
        fields: Dict[str, Any],
        strict: bool = False
    ) -> Dict[str, Any]:
        """
        Match extracted fields to a form schema.
        
        Args:
            form_id: Form identifier (e.g., ds-160@v2025-10)
            fields: Extracted fields
            strict: Require exact matches
            
        Returns:
            Form matching result
        """
        response = self.session.post(
            f'{self.base_url}/v1/forms/match',
            json={
                'form_id': form_id,
                'fields': fields,
                'strict': strict
            }
        )
        response.raise_for_status()
        
        return response.json()
    
    def start_batch(
        self,
        pages: list[str],
        doc_type: str = 'auto',
        language_hint: Optional[str] = None,
        return_layout: bool = True,
        return_words: bool = True
    ) -> Dict[str, Any]:
        """
        Start a batch OCR job.
        
        Args:
            pages: List of base64-encoded images
            doc_type: Document type hint
            language_hint: Language code
            return_layout: Include layout
            return_words: Include words
            
        Returns:
            Job information with job_id and stream_url
        """
        response = self.session.post(
            f'{self.base_url}/v1/ocr/batch',
            json={
                'pages': pages,
                'doc_type': doc_type,
                'language_hint': language_hint,
                'return_layout': return_layout,
                'return_words': return_words
            }
        )
        response.raise_for_status()
        
        return response.json()
    
    def stream_batch_results(self, job_id: str) -> Generator[Dict[str, Any], None, None]:
        """
        Stream batch job results via SSE.
        
        Args:
            job_id: Job identifier
            
        Yields:
            Progress events
        """
        response = self.session.get(
            f'{self.base_url}/v1/ocr/stream/{job_id}',
            stream=True
        )
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data = json.loads(line_str[6:])
                    yield data
                    
                    if data.get('event_type') == 'job_completed':
                        break


def example_usage():
    """Example usage of the client."""
    # Initialize client
    client = DeepSeekOCRClient(
        base_url='http://localhost:8000',
        supabase_token='your-supabase-jwt-token'
    )
    
    # Optional: Initialize E2EE session
    client.init_session()
    
    # OCR a single image
    print("Processing single image...")
    ocr_result = client.ocr_image(
        image_path='document.png',
        doc_type='passport',
        return_layout=True,
        use_e2ee=True  # Enable E2EE
    )
    
    print(f"Text: {ocr_result['text'][:200]}...")
    print(f"Processing time: {ocr_result['time_ms']}ms")
    
    # Parse semantic content
    print("\nExtracting entities and fields...")
    semantic = client.parse_semantic(
        text=ocr_result['text'],
        layout={
            'blocks': ocr_result.get('blocks'),
            'lines': ocr_result.get('lines'),
            'words': ocr_result.get('words')
        },
        hints={'country': 'US', 'dateFormat': 'MDY'}
    )
    
    print(f"Document type: {semantic['detected_doc_type']['type']}")
    print(f"Entities found: {len(semantic['entities'])}")
    print(f"Fields extracted: {len(semantic['fields'])}")
    
    # Match to form
    if semantic['fields']:
        print("\nMatching to DS-160 form...")
        form_match = client.match_form(
            form_id='ds-160@v2025-10',
            fields=semantic['fields']
        )
        
        print(f"Mapped fields: {len(form_match['mapping'])}")
        print(f"Unmapped fields: {len(form_match['unmapped'])}")
    
    # Batch processing example
    print("\nStarting batch job...")
    with open('page1.png', 'rb') as f:
        page1_b64 = base64.b64encode(f.read()).decode('utf-8')
    
    with open('page2.png', 'rb') as f:
        page2_b64 = base64.b64encode(f.read()).decode('utf-8')
    
    batch_job = client.start_batch(pages=[page1_b64, page2_b64])
    print(f"Job ID: {batch_job['job_id']}")
    
    # Stream results
    print("Streaming results...")
    for event in client.stream_batch_results(batch_job['job_id']):
        if event.get('progress'):
            progress = event['progress']
            print(f"Progress: {progress['completed']}/{progress['total']} pages")
        
        if event.get('page_result'):
            page = event['page_result']
            print(f"Page {page['page_index']} completed")


if __name__ == '__main__':
    example_usage()
