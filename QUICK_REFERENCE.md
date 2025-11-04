# Quick Reference Guide - DeepSeek-OCR API

## 🚀 Quick Start Commands

### Local Development
```bash
# Setup
cp .env.example .env
# Edit .env with your Supabase credentials
./start.sh
```

### Docker
```bash
# Build and run
docker-compose up -d ocr-api

# View logs
docker-compose logs -f ocr-api

# Stop
docker-compose down
```

### With Mock Adapter (No GPU Required)
```bash
export USE_MOCK_ADAPTER=true
./start.sh
```

## 🔧 Common API Calls

### 1. Health Check
```bash
curl http://localhost:8000/v1/health
```

### 2. OCR Single Image
```bash
curl -X POST http://localhost:8000/v1/ocr/image \
  -H "Authorization: Bearer YOUR_SUPABASE_JWT" \
  -F "image=@document.png" \
  -F "doc_type=passport" \
  -F "return_layout=true"
```

### 3. Extract Entities
```bash
curl -X POST http://localhost:8000/v1/parse/semantic \
  -H "Authorization: Bearer YOUR_SUPABASE_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "John Doe, born 01/15/1990",
    "doc_type": "auto"
  }'
```

### 4. Match to Form
```bash
curl -X POST http://localhost:8000/v1/forms/match \
  -H "Authorization: Bearer YOUR_SUPABASE_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "form_id": "ds-160@v2025-10",
    "fields": {
      "full_name": {"value": "John Doe", "conf": 0.95, "source": {"page": 0, "word_ids": [0,1]}}
    }
  }'
```

## 📊 Available Form Schemas

- `ds-160@v2025-10` - US Visa Application Form
- `passport@v1` - International Passport
- `resume@v1` - Resume/CV

## 🔐 E2EE Setup (Browser)

```javascript
// 1. Generate client keys
const clientKeys = await generateX25519KeyPair();

// 2. Get server public key
const { e2ee } = await fetch('/').then(r => r.json());

// 3. Derive shared secret
const sharedSecret = await deriveSharedSecret(
  clientKeys.privateKey, 
  e2ee.server_pubkey
);

// 4. Encrypt image
const encrypted = await encryptXChaCha20(imageBytes, sharedSecret);

// 5. Send request
await fetch('/v1/ocr/image', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'X-Client-Pubkey': base64(clientKeys.publicKey)
  },
  body: formData
});
```

## 🎯 Environment Variables Cheat Sheet

**Minimal Setup:**
```bash
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_JWT_SECRET=your-secret
MODEL_PATH=deepseek-ai/DeepSeek-OCR
```

**Testing (No GPU):**
```bash
USE_MOCK_ADAPTER=true
```

**Production:**
```bash
REQUIRE_E2EE=true
ALLOW_PDF_UPLOADS=false
MAX_REQUESTS_PER_MINUTE=60
```

## 🐛 Troubleshooting

### "Model not available"
- Check GPU: `nvidia-smi`
- Use mock: `export USE_MOCK_ADAPTER=true`

### "Unauthorized"
- Verify Supabase JWT token is valid
- Check `SUPABASE_URL` and `SUPABASE_JWT_SECRET`

### "Rate limited"
- Wait 60 seconds or adjust `MAX_REQUESTS_PER_MINUTE`

### Out of memory
- Reduce `GPU_MEMORY_UTILIZATION` (default 0.9)
- Lower `MAX_CONCURRENCY`

## 📦 Package Structure

```
src/
├── main.py           # FastAPI app & endpoints
├── config.py         # Environment config
├── auth/
│   └── supabase.py   # JWT verification
├── crypto/
│   └── e2ee.py       # E2EE utilities
├── inference/
│   └── adapter.py    # OCR adapters
├── models/
│   └── schemas.py    # Pydantic models
└── forms/
    └── matcher.py    # Form matching
```

## 🧪 Testing

```bash
# Unit tests
cd /data/DeepSeek-OCR
pytest tests/

# Specific test
pytest tests/test_crypto.py -v

# With coverage
pytest --cov=src tests/
```

## 📈 Monitoring

- **Metrics:** http://localhost:8000/metrics
- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3000

## 🔗 Useful Links

- API Docs: http://localhost:8000/docs
- Redoc: http://localhost:8000/redoc
- Health: http://localhost:8000/v1/health
- Readiness: http://localhost:8000/v1/ready
