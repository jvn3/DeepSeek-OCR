#!/bin/bash
#
# DeepSeek OCR Studio - Installation Verification
#

echo "========================================="
echo "🔍 DeepSeek OCR Studio - File Check"
echo "========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "${RED}✗${NC} $1 ${RED}(MISSING)${NC}"
        return 1
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1/"
        return 0
    else
        echo -e "${RED}✗${NC} $1/ ${RED}(MISSING)${NC}"
        return 1
    fi
}

total=0
passed=0

echo "📁 Configuration Files:"
files=(
    "package.json"
    "tsconfig.json"
    "tailwind.config.ts"
    "next.config.js"
    "postcss.config.js"
    ".env.example"
    ".gitignore"
)

for file in "${files[@]}"; do
    ((total++))
    check_file "$file" && ((passed++))
done

echo ""
echo "📁 Application Files:"
app_files=(
    "app/layout.tsx"
    "app/page.tsx"
    "app/providers.tsx"
    "app/globals.css"
)

for file in "${app_files[@]}"; do
    ((total++))
    check_file "$file" && ((passed++))
done

echo ""
echo "📁 State & Utilities:"
lib_files=(
    "store/useAppStore.ts"
    "lib/ocrClient.ts"
    "lib/pdf.ts"
    "lib/images.ts"
    "lib/download.ts"
    "lib/bbox.ts"
    "lib/utils.ts"
)

for file in "${lib_files[@]}"; do
    ((total++))
    check_file "$file" && ((passed++))
done

echo ""
echo "📁 Components:"
component_files=(
    "components/Uploader.tsx"
    "components/ProgressBar.tsx"
    "components/ui/button.tsx"
    "components/ui/input.tsx"
    "components/ui/card.tsx"
    "components/ui/progress.tsx"
    "components/ui/tabs.tsx"
    "components/ui/toast.tsx"
    "components/ui/toaster.tsx"
    "hooks/use-toast.ts"
)

for file in "${component_files[@]}"; do
    ((total++))
    check_file "$file" && ((passed++))
done

echo ""
echo "📁 Form Schemas:"
schema_files=(
    "schemas/ds-160.json"
    "schemas/passport.json"
    "schemas/w-2.json"
)

for file in "${schema_files[@]}"; do
    ((total++))
    check_file "$file" && ((passed++))
done

echo ""
echo "📁 Documentation:"
doc_files=(
    "README.md"
    "QUICKSTART.md"
    "PROJECT_SUMMARY.md"
    "FILE_INDEX.md"
)

for file in "${doc_files[@]}"; do
    ((total++))
    check_file "$file" && ((passed++))
done

echo ""
echo "📁 Scripts:"
check_file "setup.sh" && ((passed++))
((total++))

echo ""
echo "========================================="
echo "📊 Results: ${passed}/${total} files present"
echo "========================================="

if [ $passed -eq $total ]; then
    echo -e "${GREEN}✓ All core files present!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. npm install"
    echo "  2. Copy .env.example to .env.local"
    echo "  3. Update NEXT_PUBLIC_OCR_BASE_URL"
    echo "  4. npm run dev"
    exit 0
else
    missing=$((total - passed))
    echo -e "${YELLOW}⚠ ${missing} files missing${NC}"
    echo ""
    echo "Some files are missing. This may be expected if:"
    echo "  - You haven't run 'npm install' yet"
    echo "  - You're implementing remaining pages"
    echo "  - You're adding additional components"
    exit 1
fi
