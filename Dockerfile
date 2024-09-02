# Use NVIDIA CUDA base image
FROM nvidia/cuda:12.2.0-runtime-ubuntu20.04

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy just the requirements file first to leverage Docker cache
COPY requirements.txt /app/

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Install PyTorch with CUDA support
RUN pip3 install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu121

# Copy the rest of the application
COPY . /app

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the miner script
CMD ["python3", "sd-miner-v1.3.1.py"]