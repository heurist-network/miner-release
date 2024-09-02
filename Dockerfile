# Use NVIDIA CUDA base image
FROM nvidia/cuda:12.2.0-runtime-ubuntu20.04

# Set the working directory
WORKDIR /app

# Install system dependencies and specific Python version
RUN apt-get update && apt-get install -y \
    software-properties-common \
    curl \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y \
    python3.10 \
    python3.10-dev \
    python3.10-distutils \
    git \
    && rm -rf /var/lib/apt/lists/*

# Update alternatives to set python3.10 as the default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

# Install pip for Python 3.10
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && python3.10 get-pip.py && rm get-pip.py

# Copy just the requirements file first to leverage Docker cache
COPY requirements.txt /app/

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Install PyTorch with CUDA support
RUN pip3 install torch==2.4.0 torchvision==0.19.0+cu121 torchaudio==2.4.0+cu121 --extra-index-url https://download.pytorch.org/whl/cu121

# Copy the rest of the application
COPY . /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV NVIDIA_VISIBLE_DEVICES=all

# Set up volumes
VOLUME ["/root/.heurist-keys", "/root/.cache"]

# Run the miner script
CMD ["python3", "sd-miner-v1.3.1.py", "--skip-checksum", "--cuda-device-id", "0", "--model-id", "MagusDevon", "--log-level", "DEBUG"]
