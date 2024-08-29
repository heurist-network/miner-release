# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install CUDA (this is a simplified version, you might need to adjust based on your CUDA requirements)
RUN wget https://developer.download.nvidia.com/compute/cuda/11.8.0/local_installers/cuda_11.8.0_520.61.05_linux.run \
    && chmod +x cuda_11.8.0_520.61.05_linux.run \
    && ./cuda_11.8.0_520.61.05_linux.run --toolkit --silent \
    && rm cuda_11.8.0_520.61.05_linux.run

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 80

# Use ENTRYPOINT with CMD to allow passing arguments
ENTRYPOINT ["python", "sd-miner-v1.3.1.py"]
CMD []