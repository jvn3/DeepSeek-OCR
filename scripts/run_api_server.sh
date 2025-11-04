#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/.."
VENV_PATH="${PROJECT_ROOT}/venv"

if [[ -d "${VENV_PATH}" && -f "${VENV_PATH}/bin/activate" ]]; then
    source "${VENV_PATH}/bin/activate"
elif [[ -d "${VENV_PATH}" && -d "${VENV_PATH}/bin" ]]; then
    export PATH="${VENV_PATH}/bin:${PATH}"
elif command -v conda >/dev/null 2>&1; then
    eval "$(conda shell.bash hook)"
    conda activate deepseek-ocr
else
    echo "Unable to locate Python environment. Expected virtualenv at ${VENV_PATH} or conda env 'deepseek-ocr'." >&2
    exit 1
fi

cd "${PROJECT_ROOT}/DeepSeek-OCR-master/DeepSeek-OCR-vllm"
exec uvicorn api_server:app --host 0.0.0.0 --port 8080
