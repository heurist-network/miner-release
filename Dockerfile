# Use a single stage build
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

WORKDIR /app

# Install Python and required libraries
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-dev \
    python3-pip \
    libexpat1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir -r requirements.txt

# Install PyTorch with CUDA support
RUN pip3 install torch==2.4.0 torchvision==0.19.0+cu121 torchaudio==2.4.0+cu121 --extra-index-url https://download.pytorch.org/whl/cu121

# Copy the application code
COPY . /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV NVIDIA_VISIBLE_DEVICES=all

# Set default values for arguments
ENV LOG_LEVEL="INFO"
ENV AUTO_CONFIRM="no"
ENV EXCLUDE_SDXL=""
ENV SKIP_SIGNATURE=""
ENV SKIP_CHECKSUM=""
ENV MODEL_ID=""
ENV CUDA_DEVICE_ID=""

# Create a non-root user and switch to it
RUN useradd -m appuser
USER appuser

# Set up volumes with correct paths
VOLUME ["/home/appuser/.heurist-keys", "/home/appuser/.cache"]

# Verify PyTorch installation
RUN python3 -c "import torch; print(torch.__version__)"

# Run the miner script
CMD python3 sd-miner-v1.3.1.py \
    --log-level $LOG_LEVEL \
    --auto-confirm $AUTO_CONFIRM \
    $EXCLUDE_SDXL \
    $SKIP_SIGNATURE \
    $SKIP_CHECKSUM \
    --model-id $MODEL_ID \
    --cuda-device-id $CUDA_DEVICE_ID