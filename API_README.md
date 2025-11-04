# DeepSeek-OCR Production API

A production-grade OCR microservice built around DeepSeek-OCR with zero-knowledge end-to-end encryption (E2EE), document understanding, and form auto-fill capabilities.

## 🎯 Features

### Core OCR Capabilities
- **High-accuracy OCR** with layout preservation (blocks, lines, words + bounding boxes)
- **Multi-page batch processing** with parallel execution and progress streaming
- **Document type classification** (passport, resume, invoice, forms, etc.)
- **Entity extraction** (names, dates, emails, addresses, etc.)
- **Structured field extraction** with confidence scores and provenance

### Zero-Knowledge Architecture
- **Client-side decryption only** - PDFs rendered to images in browser
- **Ephemeral X25519 session keys** for E2EE channel on top of TLS
- **No persistent storage** - all processing in-memory only
- **Optional payload encryption** using XChaCha20-Poly1305 AEAD
- **Results re-encrypted** in browser before storage

### Security & Authentication
- **Supabase JWT authentication** with JWKS discovery
- **Per-user and per-IP rate limiting**
- **Configurable E2EE enforcement**
- **PII redaction masks** support
- **Secure memory wiping** for sensitive data

### Production Features
- **RESTful API** with OpenAPI 3.1 spec
- **Server-Sent Events (SSE)** for batch job streaming
- **Prometheus metrics** exposition
- **Health and readiness** endpoints
- **Docker & GPU support**
- **Comprehensive error handling** with machine-readable codes

### Form Auto-Fill
- **Form schema matching** for DS-160, passports, resumes, etc.
- **Field mapping with confidence scores**
- **Extensible schema definitions**

## 🚀 Quick Start

### Using Docker Compose (Recommended)

1. **Clone and configure:**
```bash
git clone <repository>
cd DeepSeek-OCR
cp .env.example .env
# Edit .env with your Supabase credentials
```

2. **Start the service:**
```bash
docker-compose up -d ocr-api
```

3. **Check health:**
```bash
curl http://localhost:8000/v1/health
```

### Manual Installation

1. **Install dependencies:**
```bash
pip install -r src/requirements.txt
pip install vllm-0.8.5+cu118-cp38-abi3-manylinux1_x86_64.whl
```

2. **Set environment variables:**
```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_JWT_SECRET="your-secret"
export MODEL_PATH="deepseek-ai/DeepSeek-OCR"
```

3. **Run the server:**
```bash
cd src
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## 📡 API Endpoints

### Authentication
All endpoints require a Supabase JWT token:
```bash
Authorization: Bearer <your-supabase-jwt>
```

### Core Endpoints

#### 1. OCR Single Image
```http
POST /v1/ocr/image
Content-Type: multipart/form-data

Parameters:
- image: File (PNG/JPEG/TIFF)
- doc_type: auto|passport|resume|generic (default: auto)
- language_hint: en|es|fr|... (optional)
- return_layout: boolean (default: true)
- return_words: boolean (default: true)
- page_index: integer (default: 0)

Headers:
- X-Client-Pubkey: base64 (optional, for E2EE)

Response: OCRImageResponse
{
  "page_index": 0,
  "text": "...",
  "blocks": [...],
  "lines": [...],
  "words": [{"text": "...", "bbox": [x1,y1,x2,y2], "conf": 0.99}],
  "language": "en",
  "time_ms": 142.5,
  "provenance": {"engine": "deepseek-ocr", "version": "1.0.0"}
}
```

#### 2. Semantic Parsing
```http
POST /v1/parse/semantic
Content-Type: application/json

{
  "doc_type": "auto",
  "text": "...",
  "layout": {"blocks": [...], "lines": [...], "words": [...]},
  "hints": {"country": "US", "dateFormat": "MDY"}
}

Response: SemanticParseResponse
{
  "detected_doc_type": {"type": "passport", "score": 0.96},
  "entities": [
    {"label": "PERSON", "text": "John Doe", "conf": 0.98, ...}
  ],
  "fields": {
    "full_name": {"value": "John Doe", "conf": 0.98, "source": {...}},
    "dob": {"value": "1990-01-01", "conf": 0.97, "source": {...}}
  }
}
```

#### 3. Form Matching
```http
POST /v1/forms/match
Content-Type: application/json

{
  "form_id": "ds-160@v2025-10",
  "fields": {...},
  "strict": false
}

Response: FormMatchResponse
{
  "form_id": "ds-160@v2025-10",
  "mapping": [
    {"form_field": "applicant.fullName", "source_field": "full_name", "confidence": 0.97}
  ],
  "unmapped": ["travel.itinerary.returnDate"]
}
```

#### 4. Batch OCR
```http
POST /v1/ocr/batch
Content-Type: application/json

{
  "pages": ["base64-image-1", "base64-image-2", ...],
  "doc_type": "auto",
  "return_layout": true,
  "return_words": true
}

Response: BatchOCRResponse
{
  "job_id": "uuid",
  "total_pages": 10,
  "stream_url": "/v1/ocr/stream/{job_id}"
}
```

#### 5. Stream Batch Results
```http
GET /v1/ocr/stream/{job_id}
Accept: text/event-stream

Server-Sent Events:
data: {"job_id": "...", "event_type": "progress", "progress": {"completed": 5, "total": 10}}
data: {"job_id": "...", "event_type": "page_completed", "page_result": {...}}
data: {"job_id": "...", "event_type": "job_completed", "progress": {...}}
```

### Monitoring

#### Health Check
```bash
curl http://localhost:8000/v1/health
```

#### Readiness Check
```bash
curl http://localhost:8000/v1/ready
```

#### Prometheus Metrics
```bash
curl http://localhost:8000/metrics
```

## 🔐 Zero-Knowledge E2EE Flow

### Client-Side (Browser)

1. **Initialize session:**
```typescript
// Generate client X25519 key pair
const clientKeyPair = generateX25519KeyPair();

// Fetch server's public key
const { e2ee: { server_pubkey } } = await fetch('/').then(r => r.json());

// Derive shared secret
const sharedSecret = deriveSharedSecret(clientKeyPair.privateKey, server_pubkey);
```

2. **Encrypt image:**
```typescript
// Client decrypts PDF → renders pages → encrypts each page
const pdfPages = await renderPDFToImages(encryptedPDF);
const encryptedPage = await encryptWithXChaCha20Poly1305(
  pdfPages[0],
  sharedSecret
);
```

3. **Send OCR request:**
```typescript
const formData = new FormData();
formData.append('image', encryptedPage);

const response = await fetch('/v1/ocr/image', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${supabaseToken}`,
    'X-Client-Pubkey': base64Encode(clientKeyPair.publicKey)
  },
  body: formData
});
```

4. **Re-encrypt results:**
```typescript
const ocrResult = await response.json();
// Re-encrypt with vault key before storing in Supabase
const encrypted = await encryptWithVaultKey(ocrResult);
await supabase.from('documents').insert({ data: encrypted });
```

### Server-Side

The server:
- Receives encrypted payload
- Derives same shared secret from client's public key
- Decrypts image in-memory
- Processes with DeepSeek-OCR
- Returns plaintext JSON (client re-encrypts)
- Never stores images or text

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | 0.0.0.0 | Server host |
| `PORT` | 8000 | Server port |
| `MODEL_PATH` | deepseek-ai/DeepSeek-OCR | HuggingFace model path |
| `USE_MOCK_ADAPTER` | false | Use mock adapter for testing |
| `SUPABASE_URL` | - | Supabase project URL (required) |
| `SUPABASE_JWT_SECRET` | - | JWT secret (required if not using JWKS) |
| `REQUIRE_E2EE` | false | Enforce E2EE for all requests |
| `MAX_FILE_SIZE_MB` | 20 | Max file size in MB |
| `MAX_PAGES` | 100 | Max pages per batch |
| `MAX_CONCURRENCY` | 10 | Concurrent processing limit |
| `ENABLE_SSE` | true | Enable Server-Sent Events |
| `ALLOW_PDF_UPLOADS` | false | Allow PDF uploads (use false for ZK) |

See `.env.example` for complete list.

## 📊 Monitoring with Prometheus & Grafana

The service exposes Prometheus metrics at `/metrics`:

- `ocr_requests_total` - Total requests by endpoint and status
- `ocr_request_duration_seconds` - Request latency histogram
- `ocr_processing_time_ms` - OCR processing time
- `ocr_queue_depth` - Current batch queue depth
- `ocr_active_jobs` - Active batch jobs

### Start monitoring stack:
```bash
docker-compose up -d prometheus grafana
```

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

## 🧪 Testing

### Unit Tests
```bash
cd src
pytest tests/
```

### Integration Tests
```bash
pytest tests/integration/
```

### Load Testing
```bash
# Install locust
pip install locust

# Run load test
locust -f tests/load/locustfile.py --host http://localhost:8000
```

## 📝 Client Examples

### Python
See `examples/client-python.py`:
```python
from client import DeepSeekOCRClient

client = DeepSeekOCRClient('http://localhost:8000', supabase_token)
client.init_session()  # E2EE

result = client.ocr_image('document.png', use_e2ee=True)
semantic = client.parse_semantic(result['text'])
form_match = client.match_form('ds-160@v2025-10', semantic['fields'])
```

### TypeScript
See `examples/client-typescript.ts`:
```typescript
import { DeepSeekOCRClient } from './client';

const client = new DeepSeekOCRClient('http://localhost:8000', token);
await client.initSession();

const result = await client.ocrImage(imageFile, { docType: 'passport' }, true);
const semantic = await client.parseSemantic(result.text);
```

## 🏗️ Architecture

```
┌─────────────┐
│   Browser   │
│  (Next.js)  │
│             │
│ • Decrypt   │
│   PDF       │
│ • Render    │
│   Canvas    │
│ • Encrypt   │
│   Images    │
└──────┬──────┘
       │ E2EE (XChaCha20)
       ▼
┌─────────────┐      ┌──────────────┐
│  OCR API    │─────▶│ DeepSeek-OCR │
│  (FastAPI)  │      │    Model     │
│             │      └──────────────┘
│ • Decrypt   │
│ • Process   │
│ • No Store  │
└──────┬──────┘
       │ Plaintext JSON
       ▼
┌─────────────┐
│   Browser   │
│             │
│ • Re-encrypt│
│   with Vault│
│ • Store in  │
│   Supabase  │
└─────────────┘
```

## 🔧 Development

### Project Structure
```
DeepSeek-OCR/
├── src/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── auth/
│   │   └── supabase.py      # JWT auth
│   ├── crypto/
│   │   └── e2ee.py          # E2EE utilities
│   ├── inference/
│   │   └── adapter.py       # OCR adapters
│   ├── models/
│   │   └── schemas.py       # Pydantic models
│   └── forms/
│       └── matcher.py       # Form matching
├── examples/
│   ├── client-python.py
│   └── client-typescript.ts
├── tests/
├── Dockerfile
├── docker-compose.yml
└── README.md
```

### Adding a Form Schema

Edit `src/forms/matcher.py`:

```python
FORM_SCHEMAS["new-form@v1"] = FormSchema(
    form_id="new-form@v1",
    fields={
        "field.path": {"type": "text", "label": "Field Label"},
        # ...
    }
)
```

## 🚨 Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `RATE_LIMITED` | 429 | Rate limit exceeded |
| `UNSUPPORTED_MEDIA_TYPE` | 415 | Invalid file type |
| `PAYLOAD_TOO_LARGE` | 413 | File too large |
| `E2EE_REQUIRED` | 400 | E2EE enforcement enabled |
| `MODEL_UNAVAILABLE` | 503 | Model not loaded |
| `DECRYPTION_FAILED` | 400 | E2EE decryption error |
| `INVALID_REQUEST` | 400 | Malformed request |
| `UNAUTHORIZED` | 401 | Invalid JWT |

## 📄 License

[Your License]

## 🤝 Contributing

Contributions welcome! Please read CONTRIBUTING.md first.

## 📞 Support

- Issues: GitHub Issues
- Discussions: GitHub Discussions
- Email: [your-email]

---

**Built with ❤️ for zero-knowledge document processing**
