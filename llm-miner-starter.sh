#!/bin/bash

echo "Setting up Python virtual environment and installing dependencies..."

# Check if Python 3.8 to 3.11 is already installed
if ! python3 --version | grep -E '3\.[89]|3\.[1-9][0-9]|3\.1[0-1]' >/dev/null 2>&1; then
    # Update package lists
    echo "Updating package lists..."
    sudo apt update

    # Install Miniconda
    echo "Installing Miniconda..."
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh
    bash ~/miniconda.sh -b -p $HOME/miniconda
    export PATH="$HOME/miniconda/bin:$PATH"
    rm ~/miniconda.sh

    # Install Python 3.9 using Conda
    echo "Installing Python 3.9..."
    conda install python=3.9 -y

    # Create a virtual environment
    echo "Creating a virtual environment..."
    conda create -n llm-venv python=3.9 -y
    conda activate llm-venv
else
    echo "Python 3.8 to 3.11 is already installed. Skipping installation."
    # Assuming Python 3.9 is installed, create a virtual environment
    python3 -m venv llm-venv
    source llm-venv/bin/activate
fi

# Install dependencies
pip install vllm python-dotenv toml openai triton==2.1.0

# Verify installation
echo "Dependencies installed: $(pip freeze)"

echo "Running Python miner program..."

# Find one Python file starting with "llm-miner-*.py" and execute it
python $(ls llm-miner-*.py)

deactivate

echo "Script execution completed."