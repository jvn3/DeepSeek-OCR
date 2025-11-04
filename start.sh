#!/bin/bash
# Quick start script for DeepSeek-OCR API

set -e

echo "🚀 Starting DeepSeek-OCR API Server"
echo "===================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file. Please edit it with your Supabase credentials."
    echo ""
    echo "Required variables:"
    echo "  - SUPABASE_URL"
    echo "  - SUPABASE_JWT_SECRET"
    echo ""
    read -p "Press Enter after editing .env to continue..."
fi

# Load environment variables
set -a
source .env 2>/dev/null || true
set +a

# Check if running in Docker or local
if [ -f /.dockerenv ]; then
    echo "📦 Running in Docker container"
else
    echo "💻 Running locally"
    
    # Check Python version
    python_version=$(python3 --version 2>&1 | awk '{print $2}')
    echo "🐍 Python version: $python_version"
    
    # Check if dependencies are installed
    if ! python3 -c "import fastapi" 2>/dev/null; then
        echo "📥 Installing dependencies..."
        pip3 install -r src/requirements.txt
        
        if [ -f vllm-0.8.5+cu118-cp38-abi3-manylinux1_x86_64.whl ]; then
            echo "📥 Installing vLLM..."
            pip3 install vllm-0.8.5+cu118-cp38-abi3-manylinux1_x86_64.whl
        fi
    fi
fi

# Check GPU availability
if command -v nvidia-smi &> /dev/null; then
    echo "🎮 GPU detected:"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1
else
    echo "⚠️  No GPU detected. Using CPU (may be slow)."
    export DEVICE=cpu
fi

# Start the server
echo ""
echo "🌐 Starting server on ${HOST}:${PORT}"
echo "📚 API docs will be available at http://${HOST}:${PORT}/docs"
echo ""

cd src
python3 -m uvicorn main:app --host ${HOST} --port ${PORT} --reload
