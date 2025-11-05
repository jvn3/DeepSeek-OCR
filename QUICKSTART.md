# DeepSeek OCR Studio - Quick Start Guide

## Overview

This repository contains a complete OCR solution with:
- **Backend**: FastAPI server with DeepSeek OCR model (vLLM-powered)
- **Frontend**: Next.js 15 OCR Studio web application

## Prerequisites

- Python 3.12+
- Node.js 18+
- CUDA-capable GPU (recommended)
- Conda or Python virtual environment

## Quick Start

### Using VS Code Tasks (Recommended)

1. **Open the project in VS Code**
   ```bash
   code /path/to/DeepSeek-OCR
   ```

2. **Setup conda environment and install all dependencies**
   - Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
   - Type: "Tasks: Run Task"
   - Select: "Install All Dependencies"
   
   This will:
   - Create a conda environment at `{workspace}/venv` (if it doesn't exist)
   - Install all Python dependencies
   - Install all npm dependencies

3. **Run the full stack**
   - Press `Ctrl+Shift+B` (or `Cmd+Shift+B` on Mac)
   - Or: `Ctrl+Shift+P` → "Tasks: Run Build Task"
   
   This starts both:
   - Backend server at `http://localhost:8000`
   - Frontend at `http://localhost:3000`

4. **Open the application**
   - Navigate to `http://localhost:3000`
   - Upload a document (PDF, image, etc.)
   - Process with DeepSeek OCR

### Manual Setup

#### Backend Setup

1. **Activate environment**
   ```bash
   conda activate ./venv
   # Or if using absolute path:
   # source ./venv/bin/activate
   ```

2. **Install dependencies**
   ```bash
   cd app
   pip install -r requirements.txt
   ```

3. **Start backend server**
   ```bash
   python ocr_server.py
   ```
   Server runs at: `http://localhost:8000`

#### Frontend Setup

1. **Install dependencies**
   ```bash
   cd ocr-studio
   npm install
   ```

2. **Start dev server**
   ```bash
   npm run dev
   ```
   Application runs at: `http://localhost:3000`

## Project Structure

```
DeepSeek-OCR/
├── app/                              # Backend
│   ├── ocr_server.py                # Main OCR API server
│   ├── DeepSeek-OCR-master/        # Model implementation
│   └── requirements.txt             # Python dependencies
│
├── ocr-studio/                      # Frontend
│   ├── app/                        # Next.js pages
│   │   ├── page.tsx               # Landing page
│   │   ├── import/                # Document import
│   │   ├── process/               # OCR processing
│   │   ├── review/                # Results review
│   │   └── export/                # Export options
│   ├── components/                 # React components
│   ├── lib/                        # Utilities
│   └── package.json
│
└── .vscode/
    └── tasks.json                  # Automated tasks
```

## Available VS Code Tasks

Access via `Ctrl+Shift+P` → "Tasks: Run Task":

| Task | Description |
|------|-------------|
| **Run Full Stack** | Start both backend and frontend (default: Ctrl+Shift+B) |
| **Setup Conda Environment** | Create conda env in workspace if not exists |
| Install All Dependencies | Setup conda env + install backend + frontend dependencies |
| Install Backend Dependencies | Install Python packages only (auto-runs setup) |
| Install Frontend Dependencies | Install npm packages only |
| Run Backend Server | Start OCR backend (port 8000) |
| Run Frontend Dev Server | Start Next.js frontend (port 3000) |
| Build Frontend for Production | Create production build |
| Kill Backend Server | Stop OCR backend |
| Kill All Servers | Stop all running servers |

## Usage Workflow

1. **Upload Documents**
   - Drag and drop or select files (PDF, images)
   - Supports multiple files

2. **Select Pages**
   - Preview all pages
   - Select which pages to process

3. **Process with OCR**
   - Real-time processing with progress
   - Streaming results from DeepSeek model

4. **Review Results**
   - View extracted text and markdown
   - Edit if needed

5. **Export**
   - Download as JSON, CSV, or PDF
   - Copy to clipboard

## API Endpoints

Backend server (`http://localhost:8000`):

- `GET /health` - Health check
- `POST /v1/ocr/image` - OCR single image
- `POST /v1/ocr/pdf` - OCR PDF file
- `GET /docs` - Interactive API documentation

## Troubleshooting

### Backend won't start
```bash
# Check if conda environment is activated
conda activate ./venv
# Or: source ./venv/bin/activate

# Kill existing processes
pkill -9 -f "ocr_server.py"

# Restart
cd app && python ocr_server.py
```

### Frontend won't start
```bash
# Clear cache and reinstall
cd ocr-studio
rm -rf node_modules .next
npm install
npm run dev
```

### Port conflicts
- Backend: Default port 8000, check `app/ocr_server.py`
- Frontend: Default port 3000, check `ocr-studio/package.json`

## Environment Variables

Create `.env` in the root directory:

```env
# Backend
CUDA_VISIBLE_DEVICES=0
VLLM_USE_V1=0

# Optional
MODEL_PATH=deepseek-ai/DeepSeek-OCR
MAX_MODEL_LEN=8192
GPU_MEMORY_UTILIZATION=0.90
```

## Performance Tips

- **GPU Memory**: Adjust `gpu_memory_utilization` in `ocr_server.py` (default: 0.90)
- **Batch Processing**: Process multiple pages for better throughput
- **Model Caching**: First inference may be slow, subsequent requests are faster

## Development

### Frontend Development
```bash
cd ocr-studio
npm run dev          # Development server
npm run build        # Production build
npm run lint         # Lint code
```

### Backend Development
```bash
cd app
python ocr_server.py                    # Main server
python simple_server.py                 # Mock server for testing
```

## License

See [LICENSE](LICENSE) file for details.

## Support

- GitHub Issues: [Report bugs](https://github.com/deepseek-ai/DeepSeek-OCR/issues)
- Documentation: [API_README.md](API_README.md)
- Model Card: [Hugging Face](https://huggingface.co/deepseek-ai/DeepSeek-OCR)
