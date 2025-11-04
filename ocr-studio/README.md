# DeepSeek OCR Studio

Production-ready Next.js 15 web application for OCR and document understanding powered by Deep Deep-OCR.

## Features

- 📄 **Multi-format support**: PDF, PNG, JPEG, TIFF
- 🔍 **Advanced OCR**: Text, layout, entities, and field extraction
- 📋 **Form matching**: Auto-map to schemas (DS-160, W-2, passport, etc.)
- ✏️ **Interactive review**: Word-level overlays, confidence scores, inline corrections
- 💾 **Export options**: JSON, CSV, filled PDF preview
- 🎯 **Zero persistence**: All processing in-browser, no cloud storage
- ⚡ **Real-time streaming**: SSE for batch processing progress

## Prerequisites

- **Node.js** 18+ 
- **DeepSeek-OCR server** running (see [server setup](#ocr-server))

## Quick Start

### 1. Install Dependencies

```bash
cd ocr-studio
npm install
```

### 2. Configure Environment

Create `.env.local`:

```bash
# Copy from example
cp .env.example .env.local

# Edit these values:
NEXT_PUBLIC_OCR_BASE_URL=http://localhost:8000
NEXT_PUBLIC_OCR_API_KEY=your-api-key-here
```

### 3. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### 4. Build for Production

```bash
npm run build
npm start
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_OCR_BASE_URL` | OCR server endpoint | `http://localhost:8000` |
| `NEXT_PUBLIC_OCR_API_KEY` | API authentication key | - |
| `NEXT_PUBLIC_MAX_PAGE_EDGE` | Max page dimension (px) | `1800` |
| `NEXT_PUBLIC_CONCURRENCY` | Parallel OCR requests | `3` |
| `NEXT_PUBLIC_MAX_FILE_SIZE_MB` | Max file size | `50` |
| `NEXT_PUBLIC_MAX_PAGES` | Max pages per session | `100` |
| `NEXT_PUBLIC_PDF_SCALE` | PDF render quality (1.0-3.0) | `2.0` |

## OCR Server

This UI requires a running DeepSeek-OCR API server.

### Option A: Use Included Server

```bash
cd ../src  # From DeepSeek-OCR root
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Option B: Docker

```bash
docker-compose up deepseek-ocr
```

### Required Endpoints

The server must implement:

- `POST /v1/ocr/image` - OCR single page
- `POST /v1/parse/semantic` - Extract entities/fields
- `POST /v1/forms/match` - Map to form schema
- `POST /v1/ocr/batch` - Start batch job
- `GET /v1/ocr/stream/{jobId}` - SSE results stream
- `GET /v1/health` - Health check

## Usage Workflows

### Single PDF

1. **Upload** → Drop PDF on landing page
2. **Import** → Preview pages, exclude unwanted pages
3. **Process** → OCR runs automatically (progress bar shows status)
4. **Review** → See text overlays, edit fields, adjust confidence
5. **Export** → Download JSON, CSV, or filled PDF

### Multiple Images

1. Upload PNG/JPEG files
2. Same flow as PDF (images treated as pages)
3. Reorder pages if needed

### Form Matching

1. After OCR completes, go to **Review** tab
2. Select form schema from dropdown (DS-160, W-2, etc.)
3. Click "Auto-map fields"
4. Review mapped fields, fix mismatches
5. Export filled PDF with form structure

## Project Structure

```
ocr-studio/
├── app/                    # Next.js 15 app router
│   ├── page.tsx           # Landing
│   ├── import/page.tsx    # Upload & preview
│   ├── process/page.tsx   # OCR queue
│   ├── review/page.tsx    # Results & correction
│   └── export/page.tsx    # Download
├── components/            # React components
│   ├── Uploader.tsx       # Drag & drop
│   ├── PdfPreview.tsx     # PDF.js renderer
│   ├── ImageGrid.tsx      # Page thumbnails
│   ├── ProgressBar.tsx    # Progress tracking
│   ├── PageCanvas.tsx     # Word overlays
│   ├── FieldsEditor.tsx   # Field corrections
│   ├── ExportButtons.tsx  # Download controls
│   ├── FormSelector.tsx   # Schema picker
│   └── ui/                # shadcn/ui components
├── lib/                   # Utilities
│   ├── ocrClient.ts       # API client
│   ├── pdf.ts             # PDF.js helpers
│   ├── images.ts          # Image processing
│   ├── download.ts        # Export utils
│   └── bbox.ts            # Bounding box math
├── store/                 # State management
│   └── useAppStore.ts     # Zustand store
├── public/
│   └── samples/           # Demo files
└── schemas/               # Form definitions
    ├── ds-160.json
    ├── w-2.json
    └── passport.json
```

## API Integration

### OCR Client

```typescript
import { ocrImage, parseSemantic, formsMatch } from '@/lib/ocrClient'

// OCR single page
const page = await ocrImage(blob, {
  docType: 'passport',
  languageHint: 'en',
  returnLayout: true,
  returnWords: true
})

// Extract entities
const semantic = await parseSemantic({
  text: page.text,
  layout: { blocks: page.blocks, lines: page.lines, words: page.words },
  hints: { country: 'US' }
})

// Match to form
const mapping = await formsMatch({
  formId: 'ds-160@v2025-10',
  fields: semantic.fields
})
```

### Batch Processing

```typescript
import { startBatchJob, streamBatchResults } from '@/lib/ocrClient'

const { jobId } = await startBatchJob(pageBlobs, { languageHint: 'en' })

const cleanup = streamBatchResults(
  jobId,
  (result) => console.log('Page done:', result.pageIndex),
  () => console.log('All pages complete'),
  (err) => console.error(err)
)
```

## State Management

Zustand store (`useAppStore`) holds:

```typescript
{
  files: File[]                  // Original uploads
  pageImages: PageImage[]        // Rendered PNGs
  ocr: OcrResults                // Text, words, layout
  semantic: SemanticResults      // Entities, fields
  mapping: FormMapping           // Form schema mapping
  processingStatus: 'idle' | 'rendering' | ...
  pageStatuses: PageStatus[]     // Per-page progress
}
```

## Components

### Core UI

- **Uploader** - File drop zone with validation
- **PdfPreview** - Renders PDF pages to canvas
- **ImageGrid** - Thumbnails with include/exclude toggles
- **ProgressBar** - Overall + per-page status
- **PageCanvas** - Interactive word overlays
- **FieldsEditor** - Editable fields with provenance
- **ExportButtons** - JSON, CSV, PDF download
- **FormSelector** - Pick form schema

### shadcn/ui

Pre-configured components:
- Button, Input, Card, Progress, Tabs, Toast, Dialog

## Testing

```bash
# Run tests
npm test

# Watch mode
npm run test:watch

# Type checking
npm run type-check
```

## Performance Tips

### PDF Rendering

- Default scale: 2.0 (balance quality/speed)
- Max edge: 1800px (prevents huge payloads)
- Uses Web Workers for heavy transforms

### OCR Processing

- Concurrency limit: 3 pages at a time
- Batch mode for 10+ pages (uses SSE streaming)
- AbortController for cancellation

### Memory Management

- `URL.revokeObjectURL()` called on cleanup
- Canvas elements reused when possible
- Store reset on "Start over"

## Troubleshooting

### "Connection refused" error

Server not running. Start OCR server:
```bash
cd ../src
python -m uvicorn main:app --port 8000
```

### PDF rendering fails

Check PDF.js worker URL in `lib/pdf.ts`. You may need to:
```bash
npm install pdfjs-dist
# Copy worker to public/
cp node_modules/pdfjs-dist/build/pdf.worker.min.js public/
```

Then update `lib/pdf.ts`:
```typescript
pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.js'
```

### TypeScript errors

```bash
npm install --save-dev @types/node
npm run type-check
```

### CORS errors

Add your frontend URL to OCR server's `CORS_ORIGINS`:
```bash
# In OCR server .env
CORS_ORIGINS=http://localhost:3000
```

## Deployment

### Vercel

```bash
npm install -g vercel
vercel
```

Set environment variables in Vercel dashboard.

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

Build and run:
```bash
docker build -t ocr-studio .
docker run -p 3000:3000 -e NEXT_PUBLIC_OCR_BASE_URL=https://your-ocr-server.com ocr-studio
```

### Static Export

For fully static deployment:
```bash
# next.config.js
module.exports = {
  output: 'export'
}

npm run build
# Deploy `out/` folder to CDN
```

## Architecture

### Client-side Processing

- PDF rendering: PDF.js in browser
- Image normalization: Canvas API + EXIF rotation
- No server-side storage: all state in Zustand + browser memory

### Server Communication

- REST for single operations
- SSE for batch streaming
- Optional API key authentication

### Data Flow

```
User uploads PDF
  → PDF.js renders to PNGs
  → Send PNG to /v1/ocr/image
  → Get OCR results (words, lines, blocks)
  → Send combined text to /v1/parse/semantic
  → Get entities and fields
  → (Optional) Send fields to /v1/forms/match
  → Get form mapping
  → User reviews/edits
  → Export JSON/CSV/PDF
```

## License

MIT

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## Support

- Server API docs: `../API_README.md`
- Server integration: `../SUPABASE_INTEGRATION.md`
- Issues: [GitHub Issues](https://github.com/your-repo/issues)

---

**Built with Next.js 15, TypeScript, Tailwind CSS, shadcn/ui, Zustand, React Query, and PDF.js**
