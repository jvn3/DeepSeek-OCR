# Supabase Integration Guide

## 🔗 How to Connect Your OCR Server to Supabase

This guide shows you how to integrate the DeepSeek-OCR API server with your Supabase project.

---

## 1️⃣ Setup Supabase Project

### Get Your Credentials

1. Go to https://app.supabase.com
2. Select your project
3. Navigate to **Settings** → **API**
4. Copy these values:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **JWT Secret**: Found under "Project JWT secret"

---

## 2️⃣ Configure OCR Server

### Update Environment Variables

Edit `/data/DeepSeek-OCR/.env`:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_JWT_SECRET=your-jwt-secret-here

# Security
REQUIRE_E2EE=false
USE_JWKS=true  # Recommended: Uses JWKS discovery for JWT verification
```

### Restart the Server

```bash
cd /data/DeepSeek-OCR/src
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 3️⃣ Frontend Integration (Next.js)

### Install Dependencies

```bash
npm install @supabase/supabase-js
# or
yarn add @supabase/supabase-js
```

### Environment Variables

Create `.env.local` in your Next.js project:

```bash
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_OCR_API_URL=http://localhost:8000
```

### Example Hook (useOCR.ts)

```typescript
// hooks/useOCR.ts
import { createClient } from '@supabase/supabase-js';
import { useState } from 'react';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

const OCR_API_URL = process.env.NEXT_PUBLIC_OCR_API_URL || 'http://localhost:8000';

export function useOCR() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ocrImage = async (imageFile: File) => {
    setLoading(true);
    setError(null);

    try {
      // Get Supabase session token
      const { data: { session } } = await supabase.auth.getSession();
      
      if (!session) {
        throw new Error('Please sign in first');
      }

      // Create form data
      const formData = new FormData();
      formData.append('image', imageFile);
      formData.append('doc_type', 'auto');
      formData.append('return_layout', 'true');

      // Call OCR API with Supabase JWT
      const response = await fetch(`${OCR_API_URL}/v1/ocr/image`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error('OCR failed');
      }

      return await response.json();

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return null;
    } finally {
      setLoading(false);
    }
  };

  return { ocrImage, loading, error };
}
```

### Example Component

```typescript
// components/OCRUploader.tsx
'use client';

import { useOCR } from '@/hooks/useOCR';
import { useState } from 'react';

export function OCRUploader() {
  const { ocrImage, loading, error } = useOCR();
  const [result, setResult] = useState<any>(null);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const ocrResult = await ocrImage(file);
    if (ocrResult) {
      setResult(ocrResult);
      console.log('OCR Result:', ocrResult);
    }
  };

  return (
    <div>
      <input
        type="file"
        accept="image/*"
        onChange={handleUpload}
        disabled={loading}
      />
      
      {loading && <p>Processing...</p>}
      {error && <p className="text-red-500">Error: {error}</p>}
      
      {result && (
        <div>
          <h3>Extracted Text:</h3>
          <pre>{result.text}</pre>
        </div>
      )}
    </div>
  );
}
```

---

## 4️⃣ Authentication Flow

### How it Works

```
User → Signs in with Supabase Auth
     ↓
Frontend → Gets session.access_token (JWT)
     ↓
Frontend → Calls OCR API with Authorization: Bearer <token>
     ↓
OCR Server → Verifies JWT with Supabase (JWKS)
     ↓
OCR Server → Processes image & returns results
     ↓
Frontend → Receives results (optionally saves to Supabase)
```

### Example: Full Workflow

```typescript
// Complete example with entity extraction and form matching
async function processDocument(imageFile: File) {
  const { data: { session } } = await supabase.auth.getSession();
  
  if (!session) {
    throw new Error('Not authenticated');
  }

  const token = session.access_token;

  // Step 1: OCR the image
  const formData = new FormData();
  formData.append('image', imageFile);
  
  const ocrResponse = await fetch(`${OCR_API_URL}/v1/ocr/image`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData,
  });
  
  const ocrResult = await ocrResponse.json();

  // Step 2: Extract entities and fields
  const semanticResponse = await fetch(`${OCR_API_URL}/v1/parse/semantic`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      text: ocrResult.text,
      layout: { 
        blocks: ocrResult.blocks,
        lines: ocrResult.lines,
        words: ocrResult.words
      },
      hints: { country: 'US' }
    }),
  });
  
  const semantic = await semanticResponse.json();

  // Step 3: Match to form schema (e.g., DS-160)
  const formResponse = await fetch(`${OCR_API_URL}/v1/forms/match`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      form_id: 'ds-160@v2025-10',
      fields: semantic.fields,
    }),
  });
  
  const formMatch = await formResponse.json();

  // Step 4: Save to Supabase
  await supabase.from('documents').insert({
    user_id: session.user.id,
    ocr_text: ocrResult.text,
    entities: semantic.entities,
    fields: semantic.fields,
    form_mapping: formMatch.mapping,
    created_at: new Date().toISOString(),
  });

  return { ocrResult, semantic, formMatch };
}
```

---

## 5️⃣ Database Schema (Optional)

### Create a Table in Supabase

Run this SQL in your Supabase SQL editor:

```sql
-- Create documents table
CREATE TABLE documents (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  ocr_text TEXT,
  entities JSONB,
  fields JSONB,
  form_mapping JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Create policy: Users can only see their own documents
CREATE POLICY "Users can view own documents"
  ON documents FOR SELECT
  USING (auth.uid() = user_id);

-- Create policy: Users can insert their own documents
CREATE POLICY "Users can insert own documents"
  ON documents FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Create index for faster queries
CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);
```

---

## 6️⃣ Testing the Integration

### Test with curl

```bash
# 1. Get a Supabase JWT token (from your frontend or Supabase dashboard)
TOKEN="your-supabase-jwt-token"

# 2. Test OCR endpoint
curl -X POST http://localhost:8000/v1/ocr/image \
  -H "Authorization: Bearer $TOKEN" \
  -F "image=@test-document.png" \
  -F "doc_type=passport"

# 3. Test health check
curl http://localhost:8000/v1/health
```

### Get a Test Token

In your Next.js app:

```typescript
// Get current user's JWT token
const { data: { session } } = await supabase.auth.getSession();
console.log('JWT Token:', session?.access_token);
```

---

## 7️⃣ Deployment Options

### Option A: Same Server as Next.js

```bash
# Run OCR server on port 8000
# Run Next.js on port 3000
# Use nginx to route /api/ocr/* to port 8000
```

### Option B: Separate Server

```bash
# Deploy OCR server to separate instance with GPU
# Update NEXT_PUBLIC_OCR_API_URL to point to it
# Enable CORS in OCR server
```

### Option C: Docker Compose

```yaml
services:
  nextjs:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_OCR_API_URL=http://ocr-api:8000
  
  ocr-api:
    build: ./DeepSeek-OCR
    ports:
      - "8000:8000"
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_JWT_SECRET=${SUPABASE_JWT_SECRET}
```

---

## 8️⃣ Security Considerations

### Enable E2EE (Optional)

For sensitive documents, enable end-to-end encryption:

```bash
# In .env
REQUIRE_E2EE=true
```

Then in your frontend, implement X25519 key exchange (see `examples/client-typescript.ts`).

### Rate Limiting

Configure rate limits to prevent abuse:

```bash
MAX_REQUESTS_PER_MINUTE=60
MAX_REQUESTS_PER_MINUTE_PER_IP=100
```

### CORS

For production, restrict CORS origins:

```bash
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

---

## 9️⃣ Troubleshooting

### "Unauthorized" Error

- Check that `SUPABASE_JWT_SECRET` matches your Supabase project
- Ensure user is signed in and session is valid
- Try setting `USE_JWKS=true` for automatic JWT verification

### "Connection Refused"

- Verify OCR server is running: `curl http://localhost:8000/v1/health`
- Check firewall rules if deploying to separate server

### CORS Errors

- Add your frontend URL to `CORS_ORIGINS` in `.env`
- Restart the OCR server after changing CORS settings

---

## 📚 API Reference

See `API_README.md` for complete API documentation.

### Quick Reference

- `POST /v1/ocr/image` - OCR single image
- `POST /v1/parse/semantic` - Extract entities
- `POST /v1/forms/match` - Match to forms
- `POST /v1/ocr/batch` - Batch processing
- `GET /v1/ocr/stream/{job_id}` - Stream results

---

**Ready to integrate!** 🚀

The OCR server is now configured to work with your Supabase project. All API calls will be authenticated using Supabase JWT tokens.
