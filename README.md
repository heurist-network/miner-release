# ⚙️ Heurist Miner Setup Guide

![miner](https://github.com/user-attachments/assets/efd35068-13a6-454c-b16a-6392d51e2557)

## Table of Contents
1. [Introduction](#introduction)
2. [System Requirements](#system-requirements)
3. [Quick Start Guide](#quick-start-guide)
   - [Docker Setup](#docker-setup)
   - [Local Setup](#local-setup)
4. [Detailed Setup Instructions](#detailed-setup-instructions)
   - [Configuring Miner ID and Identity Wallet](#configuring-miner-id-and-identity-wallet)
   - [Stable Diffusion Miner Setup](#stable-diffusion-miner-setup)
     - [Windows Setup](#windows-setup)
     - [Linux Setup](#linux-setup)
   - [Large Language Model Miner Setup](#large-language-model-miner-setup)
5. [Advanced Configuration](#advanced-configuration)
   - [Command Line Interface (CLI) Options](#command-line-interface-cli-options)
     - [Stable Diffusion Miner](#stable-diffusion-miner)
     - [Large Language Model Miner](#large-language-model-miner)
   - [Multiple GPU Configuration](#multiple-gpu-configuration)
6. [Troubleshooting](#troubleshooting)
7. [FAQ](#faq)
8. [Support and Community](#support-and-community)

## Introduction

Welcome to the Heurist Miner, the entrance to decentralized generative AI. Whether you have a high-end gaming PC with NVIDIA GPU or you're a datacenter owner ready to explore the world of AI and cryptocurrency, this guide will help you get started on an exciting journey!

### What is Heurist Miner? 

Heurist Miner allows you to contribute your GPU to perform AI inference tasks on the Heurist network. By running this miner, you'll earn rewards by hosting AI models and supporting various applications in Heurist ecosystem.

### Key Features ✨

- 🖼️ **Dual Mining Capabilities**: Support for both image generation models and Large Language Models.
- 🖥️ **Flexible Setup**: Run on Windows or Linux, with support for multiple GPUs.
- 🔐 **Secure Rewards**: Utilizes a dual-wallet system for enhanced security.
- 🌐 **Open Source**: The code is fully open and transparent. Download and run with ease.

## System Requirements

Before you begin, ensure your system meets the following requirements:

### Hardware 🖥️
- **GPU**: NVIDIA GPU with at least 12GB VRAM (24GB+ recommended for optimal performance)
- **CPU**: Multi-core processor (4+ cores recommended)
- **RAM**: 16GB+ system RAM
- **Storage**: At least 50GB free space (NVMe recommended for faster model loading)

### Software 💾
- **Operating System**: 
  - Windows 10/11 (64-bit)
  - Linux (Ubuntu 20.04 LTS or later recommended)
- **CUDA**: Version 12.1, or 12.2
- **Python**: Version 3.10 or 3.11
- **Git**: For cloning the repository

### Network 🌐
- Stable internet connection (100 Mbps+ recommended)
- Ability to access HuggingFace and GitHub repositories

### Additional Notes ℹ️
- Some models (especially larger LLMs) may require more VRAM. Check the model-specific requirements in the detailed setup sections.
- Ensure your system is up-to-date with the latest NVIDIA GPU drivers.
- Stable Diffusion models need at least 8-10GB VRAM, while LLMs can require 16GB to 40GB+ depending on the model size.

## Quick Start Guide

### Local Setup

For experienced users, here's a quick overview to get you mining:

1. **Clone the Repository**
```bash
git clone https://github.com/heurist-network/miner-release.git
cd miner-release
```
2. **Set Up Environment**
- Install Miniconda (if not already installed)
- Create and activate a new conda environment:
```bash
conda create --name heurist-miner python=3.11
conda activate heurist-miner
```
3. **Install Dependencies**
```bash
pip install -r requirements.txt
```
4. **Configure Miner ID**
- Create a `.env` file in the root directory
- Add your Ethereum wallet address:
```bash
MINER_ID_0=0xYourWalletAddressHere
```

Follow "Multiple GPU Configuration" section if you have multiple GPUs.

5. **Choose Your Miner**
- For Stable Diffusion:
```bash
python sd-miner.py
```
- For LLM:
```bash
./llm-miner-starter.sh <model_id>
```
For detailed instructions, troubleshooting, and advanced configuration, please refer to the sections below.

### Docker Setup
(current version only supports Flux model)

For users who prefer using Docker, follow these steps:

1. **Build the Docker Image**
```bash
docker build -t heurist-miner:latest .
```
2. **Run the Docker Container**

Single GPU:

```bash
sudo docker run -d --gpus all \
  -e MINER_ID_0=0xWalletAddressHere \
  -e LOG_LEVEL=INFO \
  -v $HOME/.cache/heurist:/app/.cache/heurist \
  heurist-miner:latest
```

Replace `0xYourWalletAddressHere` with your wallet address to receive rewards.

Multiple GPUs:

```bash
sudo docker run -d --gpus all \
  -e MINER_ID_0=0xYourFirstWalletAddressHere \
  -e MINER_ID_1=0xYourSecondWalletAddressHere \
  -e MINER_ID_2=0xYourThirdWalletAddressHere \
  -e LOG_LEVEL=INFO \
  -v $HOME/.cache/heurist:/app/.cache/heurist \
  heurist-miner:latest
```

Replace `0xYourFirstWalletAddressHere`, `0xYourSecondWalletAddressHere`, and `0xYourThirdWalletAddressHere` with your actual wallet addresses.

This command:
- Runs the container in detached mode (`-d`)
- Allows access to all GPUs (`--gpus all`)
- Sets environment variables for miner IDs and log level
- Mounts a volume for persistent cache storage
- Uses the image we just built (`heurist-miner:latest`)

Note: Ensure you have the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) installed for GPU support in Docker.

## Detailed Setup Instructions

### Configuring Miner ID and Identity Wallet

Heurist Miner uses a dual-wallet system for security and reward distribution:

1. **Identity Wallet**: Used for authentication, stored locally. Do not store funds here.
2. **Reward Wallet (Miner ID)**: Receives points, Heurist Token rewards, potential ecosystem benefits.

#### Setting Up Your Wallets

1. Create a `.env` file in the root directory of your miner installation.
2. Add your Ethereum wallet address(es) as Miner ID(s):
   ```
   MINER_ID_0=0xYourFirstWalletAddressHere
   MINER_ID_1=0xYourSecondWalletAddressHere
   ```
3. (Optional) Add custom tags for tracking:
   ```
   MINER_ID_0=0xYourFirstWalletAddressHere-GamingPC4090
   MINER_ID_1=0xYourSecondWalletAddressHere-GoogleCloudT4
   ```
4. Generate or import identity wallets:
   ```bash
   python3 ./auth/generator.py
   ```
   Follow the prompts to create new wallets or import existing ones.

## Stable Diffusion Miner Detailed Setup

### Windows Setup

1. **Install Miniconda**:
   - Download from Miniconda website
   - Choose the latest Windows 64-bit version for Python 3.11
2. **Create Conda Environment**:
   ```bash
   conda create --name heurist-miner python=3.11
   conda activate heurist-miner
   ```
3. **Install CUDA Toolkit**:
   - Download CUDA 12.1 from NVIDIA website
   - Follow the installation prompts
4. **Install PyTorch with GPU Support**:
   ```bash
   conda install pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia
   ```
5. **Clone Miner Repository and Install Dependencies**:
   ```bash
   git clone https://github.com/heurist-network/miner-release
   cd miner-release
   pip install -r requirements.txt
   ```
6. **Run the Miner**:
   ```bash
   python3 sd-miner.py
   ```

### Linux Setup

1. **Update GPU Drivers (if necessary)**:
   ```bash
   sudo apt update
   sudo ubuntu-drivers autoinstall
   ```
2. **Install Miniconda**:
   ```bash
   wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
   bash Miniconda3-latest-Linux-x86_64.sh
   ```
3. **Create Conda Environment**:
   ```bash
   conda create --name heurist-miner python=3.11
   conda activate heurist-miner
   ```
4. **Install CUDA Toolkit**:
- Follow instructions on NVIDIA CUDA Installation Guide
5. **Install PyTorch with GPU Support**:
   ```bash
   conda install pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia
   ```
6. **Clone Miner Repository and Install Dependencies**:
   ```bash
   git clone https://github.com/heurist-network/miner-release
   cd miner-release
   pip install -r requirements.txt
   ```
7. **Run the Miner**:
   ```bash
   python3 sd-miner.py
   ```

## Large Language Model Miner Detailed Setup

### Setup Process

1. **Ensure CUDA Driver is Installed**:
   - Check with `nvidia-smi`
2. **Select a Model ID**:
   - Choose based on your GPU's VRAM capacity
   - Example models:
     - `dolphin-2.9-llama3-8b` (24GB VRAM)
     - `openhermes-mixtral-8x7b-gptq` (40GB VRAM)
3. **Run the Setup Script**:
   ```bash
   chmod +x llm-miner-starter.sh
   ./llm-miner-starter.sh <model_id> --miner-id-index 0 --port 8000 --gpu-ids 0
   ```
   Options:
- `--miner-id-index`: Index of miner_id in `.env` (default: 0)
- `--port`: Port for vLLM process (default: 8000)
- `--gpu-ids`: GPU ID to use (default: 0)
4. **Wait for Model Download**:
- First run will download the model (can take time)
- Models are saved in `$HOME/.cache/huggingface`

Note: 8x7b, 34b, and 70b models may take up to an hour to load on some devices.


## Advanced Configuration for Heurist Miners

### Command Line Interface (CLI) Options

#### Stable Diffusion Miner

When running the SD miner, you can use various CLI options to customize its behavior. You can combine multiple flags.

1. **Log Level**
   - Set the verbosity of log messages:
     ```bash
     python3 sd-miner.py --log-level DEBUG
     ```
   - Options: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)

2. **Auto-Confirm**
   - Automatically confirm model downloads:
     ```bash
     python3 sd-miner.py --auto-confirm yes
     ```
   - Options: yes, no (default: no)

3. **Exclude SDXL**
   - Exclude SDXL models to reduce VRAM usage:
     ```bash
     python3 sd-miner.py --exclude-sdxl
     ```

4. **Specify Model ID**
   - Run the miner with a specific model:
     ```bash
     python3 sd-miner.py --model-id <model_id>
     ```
   - For example, run FLUX.1-dev model with:
     ```bash
     python3 sd-miner.py --model-id FLUX.1-dev --skip-checksum
     ```

5. **CUDA Device ID**
   - Specify which GPU to use:
     ```bash
     python3 sd-miner.py --cuda-device-id 0
     ```
6. **Skip checksum to speed up miner start-up time**
   - This skips checking the validity of model files. However, if incompleted files are present on the disk, the miner process will crash without this check.
     ```bash
     python3 sd-miner.py --skip-checksum
     ```

#### Large Language Model Miner

For LLM miner, use the following CLI options to customize its behavior:

1. **Specify Model ID**
   - Run the miner with a specific model (mandatory):
     ```bash
     ./llm-miner-starter.sh <model_id>
     ```
   - Example: `dolphin-2.9-llama3-8b` (requires 24GB VRAM)

2. **Miner ID Index**
   - Specify which miner ID from the `.env` file to use:
     ```bash
     ./llm-miner-starter.sh <model_id> --miner-id-index 1
     ```
   - Default: 0 (uses the first address configured)

3. **Port**
   - Set the port for communication with the vLLM process:
     ```bash
     ./llm-miner-starter.sh <model_id> --port 8001
     ```
   - Default: 8000

4. **GPU IDs**
   - Specify which GPU(s) to use:
     ```bash
     ./llm-miner-starter.sh <model_id> --gpu-ids 1
     ```
   - Default: 0

   - Example combining multiple options:
     ```bash
     ./llm-miner-starter.sh dolphin-2.9-llama3-8b --miner-id-index 1 --port 8001 --gpu-ids 1
     ```

   - Advanced usage: To deploy large models using multiple GPUs on the same machine.
      ```bash
      ./llm-miner-starter.sh openhermes-mixtral-8x7b-gptq --miner-id-index 0 --port 8000 --gpu-ids 0,1
      ```

### Multiple GPU Configuration

To utilize multiple GPUs:

1. Assign unique Miner IDs in your `.env` file:
   ```
   MINER_ID_0=0xWalletAddress1
   MINER_ID_1=0xWalletAddress2
   ```
2. Set `num_cuda_devices` in `config.toml`:
   ```toml
   [system]
   num_cuda_devices = 2
   ```
3. Run the miner without specifying a CUDA device ID to use all available GPUs.


## Troubleshooting

Running into issues? Don't worry, we've got you covered! Here are some common problems and their solutions:

### Installation Issues

1. 🚨 **CUDA not found**
   - Ensure CUDA is properly installed
   - Check if the CUDA version matches PyTorch requirements<br>
   ✅ Solution: Reinstall CUDA or update PyTorch to match your CUDA version

2. 🚨 **Dependencies installation fails**
   - Check your Python version (should be 3.10 or 3.11)
   - Ensure you're in the correct Conda environment<br>
   ✅ Solution: Create a new Conda environment and reinstall dependencies

### Runtime Issues 

1. 🚨 **CUDA out of memory error**
   - Check available GPU memory using `nvidia-smi`
   - Stop other programs occupying VRAM, or use a smaller model<br>
   ✅ Solution: Add `--exclude-sdxl` flag for SD miner or choose a smaller LLM

2. 🚨 **Miner not receiving tasks**
   - Check your internet connection
   - Verify your Miner ID is correctly set in the `.env` file<br>
   ✅ Solution: Restart the miner and check logs for connection issues

3. 🚨 **Model loading takes too long**
   - This is normal for large models, especially on first run
   - Check disk space and internet speed<br>
   ✅ Solution: Be patient (grab a coffee! ☕), or choose a smaller model

### Additional Tips

- 🔍 Always check the console output for specific error messages
- 🔄 Ensure you're using the latest version of the miner software
- 💬 If problems persist, don't hesitate to ask for help in our Discord community!

## FAQ

Got questions? We've got answers!

1️⃣ **Can I run both SD and LLM miners simultaneously?** 🖥️🖥️<br>
   🅰️ Absolutely! Just make sure you have enough GPU memory and use different CUDA device IDs.

2️⃣ **How do I know if I'm earning rewards?** 💰<br>
   🅰️ Keep an eye on your miner logs for successful task completions. We're tracking your rewards behind the scenes, and updates should be reflected on https://heurist.ai/portal within minutes.

3️⃣ **What's the difference between Identity Wallet and Reward Wallet?** 🎭💼<br>
   🅰️ Think of the Identity Wallet as your miner's passport (for authentication), and the Reward Wallet (Miner ID) as its piggy bank (for receiving points and rewards).

4️⃣ **Can I use my gaming PC for mining when I'm not gaming?** 🎮➡️💻<br>
   🅰️ Yes! Just remember to pause mining before starting the games. Your GPU can't be in two places at once!

5️⃣ **How often should I update the miner software?** 🔄<br>
   🅰️ Stay tuned to our Discord miner-announcement channel and GitHub for the latest updates. We recommend updating whenever a new version drops.

## Support and Community

### Discord Channel
Join our lively community on Discord - it's where all the cool miners hang out!
🔗 [Heurist Discord #dev-chat channel](https://discord.gg/heuristai)

### Reporting Issues
1. 📚 Check our Troubleshooting guide and FAQ - you might find a quick fix!
2. 🆘 Still stuck? Head over to our GitHub Issues page:
   🔗 [Heurist Miner Issues](https://github.com/heurist-network/miner-release/issues)
3. 📝 When reporting, remember to include:
   - Miner version
   - Model
   - Operating System
   - Console error messages and log files
   - Steps to reproduce

### Stay in the Loop
Keep up with the latest Heurist happenings:
1. 📖 Medium: [Heurist Blogs](https://medium.com/@heuristai)
2. 📣 Discord: Tune into our #miner-announcements channel
3. 🐦 X/Twitter: Follow [Heurist](https://x.com/heurist_ai) for the latest updates
