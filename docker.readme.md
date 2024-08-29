# SD-Miner Docker Guide

This guide explains how to run the SD-Miner Docker container and how to create and share the Docker image.

## Running the SD-Miner Docker Container

To run the SD-Miner Docker container, follow these steps:

1. Pull the Docker image:
   ```bash
   docker pull your-username/sd-miner:v1.3.1
   ```

2. Run the container:
   ```bash
   docker run your-username/sd-miner:v1.3.1
   ```

3. To run with optional arguments:
   ```bash
   docker run your-username/sd-miner:v1.3.1 arg1 arg2 arg3
   ```

## Creating and Sharing the Docker Image

If you want to create and share your own version of the SD-Miner Docker image:

1. Build the Docker image:
   ```bash
   docker build -t your-username/sd-miner:v1.3.1 .
   ```

2. Log in to Docker Hub:
   ```bash
   docker login
   ```

3. Push the image to Docker Hub:
   ```bash
   docker push your-username/sd-miner:v1.3.1
   ```

Now others can pull and use your image as described in the "Running" section above.

Note: Replace `your-username` with your actual Docker Hub username.

## Requirements

- Docker installed on your system
- Docker Hub account (for sharing the image)

## Additional Notes

- Ensure you have the necessary CUDA drivers installed on your host system if using GPU acceleration.
- Adjust the tag (v1.3.1) as needed for different versions of SD-Miner.

## run locally 

Navigate to the directory containing the Dockerfile and run: 

docker build -t sd-miner:v1.3.1 .

This command builds the image and tags it as "sd-miner:v1.3.1".

Run the Docker container:

After the image is built, you can run it with:
docker run --gpus all -v $(pwd):/app sd-miner:v1.3.1

This command:
Uses --gpus all to make all GPUs available to the container
Uses -v $(pwd):/app to mount the current directory to /app in the container
Runs the sd-miner:v1.3.1 image
Note that you'll need to have Docker and NVIDIA Container Toolkit installed on your system to use GPU acceleration.
Also, make sure you have a .env file in your current directory with the necessary MINER_ID configurations, as referenced in the Dockerfile:

RUN apt-get update && apt-get install -y \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

If you want to pass optional arguments to the sd-miner script, you can do so by appending them to the docker run command. For example:

docker run --gpus all -v $(pwd):/app sd-miner:v1.3.1 --log-level DEBUG --auto-confirm yes

## 
python3 sd-miner-v1.3.1.py --skip-checksum --cuda-device-id 0 --model-id FLUX.1-dev --log-level DEBUG


## 
a. Using docker-compose:
up
b. Using docker run:
you
c. Create a file (let's call it env.list) with your environment variables:
0xYourSecondWalletAddressHere
Then run Docker using this file:
file
This approach allows you to pass the necessary variables to the Docker container without needing the .env file inside the container. The sd-miner script inside the container will be able to access these variables as environment variables.
Remember to replace 0xYourFirstWalletAddressHere and 0xYourSecondWalletAddressHere with your actual miner IDs, and add any additional environment variables that your sd-miner script needs.