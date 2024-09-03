# ⚙️ Heurist Miner Setup Guide
## Table of Contents
1. [Introduction](#introduction)
2. [System Requirements](#system-requirements)
3. [Quick Start Guide](#quick-start-guide)
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

Welcome to the Heurist Miner, a cutting-edge tool for participating in the Heurist testnet mining program. Whether you're an experienced miner or new to the world of AI and cryptocurrency, this guide will help you get started.

### What is Heurist Miner?

Heurist Miner is a software that allows you to contribute your GPU's computing power to perform AI inference tasks on the Heurist network. By running this miner, you're not just earning rewards – you're also playing a crucial role in advancing decentralized AI technology.

### Key Features

- **Dual Mining Capabilities**: Support for both Stable Diffusion (image generation) and Large Language Models (text processing).
- **Flexible Setup**: Run on Windows or Linux, with support for multiple GPUs.
- **Secure Rewards**: Utilizes a dual-wallet system for enhanced security and accurate reward distribution.
- **Community-Driven**: Be part of a growing network of AI enthusiasts and miners.

### How It Works

1. **Setup**: Install the miner on your system and configure your wallet.
2. **Contribution**: Your GPU processes AI tasks as requested by the network.
3. **Rewards**: Earn points for each successfully completed task.
4. **Scaling**: Optionally, run multiple miners on different GPUs to increase your contribution and rewards.

## System Requirements

Before you begin, ensure your system meets the following requirements:

### Hardware
- **GPU**: NVIDIA GPU with at least 8GB VRAM (12GB+ recommended for optimal performance)
- **CPU**: Multi-core processor (4+ cores recommended)
- **RAM**: 16GB+ system RAM
- **Storage**: At least 50GB free space (SSD recommended for faster model loading)

### Software
- **Operating System**: 
  - Windows 10/11 (64-bit)
  - Linux (Ubuntu 20.04 LTS or later recommended)
- **CUDA**: Version 11.7, 12.1, or 12.2
- **Python**: Version 3.10 or 3.11
- **Git**: For cloning the repository

### Network
- Stable internet connection (5 Mbps+ recommended)
- Ability to access HuggingFace and GitHub repositories

### Additional Notes
- Some models (especially larger LLMs) may require more VRAM. Check the model-specific requirements in the detailed setup sections.
- Ensure your system is up-to-date with the latest GPU drivers.

## Quick Start Guide

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
5. **Choose Your Miner**
- For Stable Diffusion:
```bash
python sd-miner-v1.3.1.py
```
- For Large Language Models:
```bash
./llm-miner-starter.sh <model_id>
```
For detailed instructions, troubleshooting, and advanced configuration, please refer to the sections below.


## Detailed Setup Instructions

### Configuring Miner ID and Identity Wallet

Heurist Miner uses a dual-wallet system for security and reward distribution:

1. **Identity Wallet**: Used for authentication, stored locally. Do not store funds here.
2. **Reward Wallet (Miner ID)**: Receives points and potential rewards.

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

## Stable Diffusion Miner Setup

### Windows Setup

1. **Install Miniconda**:
   - Download from Miniconda website
   - Choose the latest Windows 64-bit version for Python 3.11
2. **Create Conda Environment**:
   ```bash
   conda create --name gpu-3-11 python=3.11
   conda activate gpu-3-11
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
   python3 sd-miner-v1.3.1.py
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
   conda create --name gpu-3-11 python=3.11
   conda activate gpu-3-11
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
   python3 sd-miner-v1.3.1.py
   ```

## Large Language Model Miner Setup

### Setup Process

1. **Ensure CUDA Driver is Installed**:
   - Check with `nvidia-smi`
2. **Select a Model ID**:
   - Choose based on your GPU's VRAM capacity
   - Example models:
     - `openhermes-2.5-mistral-7b-gptq` (10GB VRAM)
     - `mistralai/mixtral-8x7b-instruct-v0.1` (28GB VRAM)
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

When running the SD miner, you can use various CLI options to customize its behavior:

1. **Log Level**
   - Set the verbosity of log messages:
     ```bash
     python3 sd-miner-v1.3.1.py --log-level DEBUG
     ```
   - Options: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)

2. **Auto-Confirm**
   - Automatically confirm model downloads:
     ```bash
     python3 sd-miner-v1.3.1.py --auto-confirm yes
     ```
   - Options: yes, no (default: no)

3. **Exclude SDXL**
   - Exclude SDXL models to reduce VRAM usage:
     ```bash
     python3 sd-miner-v1.3.1.py --exclude-sdxl
     ```

4. **Specify Model ID**
   - Run the miner with a specific model:
     ```bash
     python3 sd-miner-v1.3.1.py --model-id <model_id>
     ```

5. **CUDA Device ID**
   - Specify which GPU to use:
     ```bash
     python3 sd-miner-v1.3.1.py --cuda-device-id 0
     ```

#### Large Language Model Miner

For LLM miner, use the following CLI options to customize its behavior:

1. **Specify Model ID**
   - Run the miner with a specific model (mandatory):
     ```bash
     ./llm-miner-starter.sh <model_id>
     ```
   - Example: `openhermes-2.5-mistral-7b-gptq` (requires 12GB VRAM)

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
     ./llm-miner-starter.sh openhermes-2.5-mistral-7b-gptq --miner-id-index 1 --port 8001 --gpu-ids 1
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

### Installation Issues

1. **CUDA not found**
   - Ensure CUDA is properly installed
   - Check if the CUDA version matches PyTorch requirements
   - Solution: Reinstall CUDA or update PyTorch

2. **Dependencies installation fails**
   - Check your Python version (should be 3.10 or 3.11)
   - Ensure you're in the correct Conda environment
   - Solution: Create a new Conda environment and reinstall dependencies

### Runtime Issues

1. **CUDA out of memory error**
   - Check available GPU memory using `nvidia-smi`
   - Reduce batch size or use a smaller model
   - Solution: Add `--exclude-sdxl` flag for SD miner or choose a smaller LLM

2. **Miner not receiving tasks**
   - Check your internet connection
   - Verify your Miner ID is correctly set in the `.env` file
   - Solution: Restart the miner and check logs for connection issues

3. **Model loading takes too long**
   - This is normal for large models, especially on first run
   - Check disk space and internet speed
   - Solution: Be patient, or choose a smaller model

## FAQ

1. **Q: Can I run both SD and LLM miners simultaneously?**
   A: Yes, but ensure you have sufficient GPU memory and use different CUDA device IDs.

2. **Q: How do I know if I'm earning rewards?**
   A: Check the miner logs for successful task completions. Rewards are tracked on our backend.

3. **Q: What's the difference between Identity Wallet and Reward Wallet?**
   A: The Identity Wallet is for authentication, while the Reward Wallet (Miner ID) receives points and potential rewards.

4. **Q: Can I use my gaming PC for mining when I'm not gaming?**
   A: Yes, just make sure to stop the miner before starting resource-intensive games.

5. **Q: How often should I update the miner software?**
   A: Check our Discord channel or GitHub repository regularly for updates. We recommend updating whenever a new version is released.

6. **Q: What should I do if my antivirus flags the miner?**
   A: This is likely a false positive. Add an exception for the miner in your antivirus software, or verify the download from our official GitHub repository.

## Support and Community

### Discord Channel
Join our vibrant community on Discord for real-time support, discussions, and updates:
[Heurist Discord #miner-chat channel](https://discord.com/channels/1183784452674039919/1203508038246600744)

### Reporting Issues
1. Check the Troubleshooting section and FAQ first
2. If the issue persists, report it on our GitHub Issues page:
   [Heurist Miner Issues](https://github.com/heurist-network/miner-release/issues)
3. Provide detailed information including:
   - Miner version
   - Operating System
   - Full error message
   - Steps to reproduce the issue

### Updates and Announcements
Stay informed about the latest updates and announcements through:
1. Our official GitHub repository: [Heurist Miner Releases](https://github.com/heurist-network/miner-release/releases)
2. The #announcements channel on our Discord server
3. Follow us on Twitter: [@HeuristAI](https://x.com/heurist_ai)

For any additional questions or support, don't hesitate to reach out to our community managers on Discord.