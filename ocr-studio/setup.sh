#!/bin/bash
#
# DeepSeek OCR Studio - Development Setup Script
#

set -e

echo "🚀 Setting up DeepSeek OCR Studio..."

# Check Node version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js 18+ required. Current version: $(node -v)"
    exit 1
fi

echo "✅ Node.js version: $(node -v)"

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Create .env.local if it doesn't exist
if [ ! -f .env.local ]; then
    echo "📝 Creating .env.local from .env.example..."
    cp .env.example .env.local
    echo ""
    echo "⚠️  Please update .env.local with your actual OCR server URL:"
    echo "   NEXT_PUBLIC_OCR_BASE_URL=http://localhost:8000"
    echo "   NEXT_PUBLIC_OCR_API_KEY=your-api-key"
fi

# Check if OCR server is running
echo ""
echo "🔍 Checking OCR server..."
OCR_URL="${NEXT_PUBLIC_OCR_BASE_URL:-http://localhost:8000}"
if curl -s -f "$OCR_URL/v1/health" > /dev/null 2>&1; then
    echo "✅ OCR server is running at $OCR_URL"
else
    echo "⚠️  OCR server not detected at $OCR_URL"
    echo "   Start the server before running this app:"
    echo "   cd ../src && python -m uvicorn main:app --port 8000"
fi

# Create sample directory
echo ""
echo "📁 Setting up sample files..."
mkdir -p public/samples

echo ""
echo "✨ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Update .env.local with your OCR server URL"
echo "  2. Start development server: npm run dev"
echo "  3. Open http://localhost:3000"
echo ""
echo "For production build:"
echo "  npm run build"
echo "  npm start"
echo ""
