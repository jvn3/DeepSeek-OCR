FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    CUDA_HOME=/usr/local/cuda \
    PATH=/usr/local/cuda/bin:$PATH \
    LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .
COPY vllm-0.8.5+cu118-cp38-abi3-manylinux1_x86_64.whl .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt && \
    pip3 install --no-cache-dir vllm-0.8.5+cu118-cp38-abi3-manylinux1_x86_64.whl

# Install additional production dependencies
RUN pip3 install --no-cache-dir \
    python-jose[cryptography] \
    httpx \
    python-multipart \
    prometheus-client \
    cryptography

# Copy source code
COPY src/ /app/src/
COPY DeepSeek-OCR-master/ /app/DeepSeek-OCR-master/

# Set Python path
ENV PYTHONPATH=/app/src:/app/DeepSeek-OCR-master/DeepSeek-OCR-vllm:$PYTHONPATH

# Create non-root user for security
RUN useradd -m -u 1000 ocruser && \
    chown -R ocruser:ocruser /app

USER ocruser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/v1/health || exit 1

# Run the application
CMD ["python3", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
