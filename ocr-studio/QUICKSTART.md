# DeepSeek OCR Studio - Quick Start

This is a **standalone Next.js 15 web application** for OCR and document understanding. It processes PDFs and images entirely client-side and communicates with the DeepSeek-OCR API server.

## 🚀 Quick Start (5 minutes)

### 1. Install & Configure

```bash
cd ocr-studio
chmod +x setup.sh
./setup.sh
```

The script will:
- Install all npm dependencies
- Create `.env.local` from example
- Check if OCR server is running

### 2. Update Environment

Edit `.env.local`:

```bash
NEXT_PUBLIC_OCR_BASE_URL=http://localhost:8000
NEXT_PUBLIC_OCR_API_KEY=dev-abc123  # Optional, if server requires auth
```

### 3. Start OCR Server

In a separate terminal:

```bash
# From DeepSeek-OCR root
cd src
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Or use the task runner:

```bash
# From DeepSeek-OCR root
tmux new-session -A -s deepseek_api './scripts/run_api_server.sh'
```

### 4. Run Development Server

```bash
npm run dev
```

Open **http://localhost:3000**

## 📋 What You Can Do

1. **Upload** - Drop a PDF or images
2. **Process** - OCR runs automatically with progress tracking
3. **Review** - Interactive word overlays, edit extracted fields
4. **Export** - Download as JSON, CSV, or filled PDF

## 🎯 Key Features

- **Multi-format**: PDF, PNG, JPEG, TIFF
- **Real-time**: SSE streaming for batch jobs
- **Client-side**: All rendering and processing in browser
- **Form matching**: Auto-map to DS-160, W-2, passport schemas
- **Zero persistence**: No cloud storage, optional local downloads only

## 📁 Project Structure

```
ocr-studio/
├── app/              # Next.js 15 routes (/, /import, /process, /review, /export)
├── components/       # React components (Uploader, ProgressBar, etc.)
├── lib/              # Utilities (ocrClient, pdf, images, download)
├── store/            # Zustand state management
├── schemas/          # Form definitions (DS-160, W-2, passport)
└── public/samples/   # Demo PDFs
```

## 🔧 Available Scripts

```bash
npm run dev          # Development server (port 3000)
npm run build        # Production build
npm start            # Run production build
npm run lint         # ESLint
npm run type-check   # TypeScript validation
npm test             # Jest tests
```

## 🌐 API Integration

This app talks to the OCR server via REST:

- `POST /v1/ocr/image` - OCR single page
- `POST /v1/parse/semantic` - Extract entities/fields
- `POST /v1/forms/match` - Match to form schema
- `POST /v1/ocr/batch` - Start multi-page job
- `GET /v1/ocr/stream/{jobId}` - SSE results

See `lib/ocrClient.ts` for implementation.

## ⚙️ Configuration

Environment variables (`.env.local`):

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_OCR_BASE_URL` | OCR API endpoint | `http://localhost:8000` |
| `NEXT_PUBLIC_OCR_API_KEY` | API key (if required) | - |
| `NEXT_PUBLIC_MAX_PAGE_EDGE` | Max page dimension (px) | `1800` |
| `NEXT_PUBLIC_CONCURRENCY` | Parallel OCR requests | `3` |
| `NEXT_PUBLIC_PDF_SCALE` | PDF render quality | `2.0` |

## 🐛 Troubleshooting

### "Connection refused"

OCR server isn't running. Start it:
```bash
cd ../src
python -m uvicorn main:app --port 8000
```

### PDF rendering fails

Install PDF.js worker:
```bash
cp node_modules/pdfjs-dist/build/pdf.worker.min.js public/
```

Update `lib/pdf.ts`:
```typescript
pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.js'
```

### CORS errors

Add frontend URL to OCR server's `.env`:
```bash
CORS_ORIGINS=http://localhost:3000
```

## 📚 Documentation

- Full README: `README.md`
- OCR server API: `../API_README.md`
- Server setup: `../SUPABASE_INTEGRATION.md`

## 🚢 Production Deployment

### Vercel

```bash
vercel
```

Set environment variables in dashboard.

### Docker

```bash
docker build -t ocr-studio .
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_OCR_BASE_URL=https://your-server.com \
  ocr-studio
```

## 📄 License

MIT

---

**Ready to process documents!** 🎉

Open http://localhost:3000 and drop a PDF to get started.
