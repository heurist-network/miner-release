#!/bin/bash

# Check and stop any running Docker containers started by this script
echo "Checking for any running Docker containers started by this script..."
running_containers=$(sudo docker ps -q -f label=started_by=llm-miner-starter)
if [ -n "$running_containers" ]; then
    echo "Stopping running Docker containers started by this script..."
    sudo docker stop $running_containers
else
    echo "No Docker containers started by this script are currently running."
fi

echo "Starting Docker container for LLM server..."

# Run Docker command with a label
sudo docker run --gpus all --shm-size 1g -p 8081:80 -v $HOME/.cache/heurist:/data -v $PWD/config:/config --label started_by=llm-miner-starter ghcr.io/huggingface/text-generation-inference:1.4 --model-id TheBloke/OpenHermes-2.5-Mistral-7B-GPTQ --revision gptq-8bit-32g-actorder_True --quantize gptq --max-input-length 2048 --max-total-tokens 4096 --max-batch-prefill-tokens 4096 --tokenizer-config-path /config/openhermes_2.5_mistral_7b_tokenizer_config.json &

echo "Initializing docker container..."
sleep 10

echo "Setting up Python virtual environment and installing dependencies..."

# Create a virtual environment
python3 -m venv llm-venv

# Activate the virtual environment
source llm-venv/bin/activate

# Install dependencies
pip3 install requests torch python-dotenv toml openai numpy

# Verify installation
echo "Dependencies installed: $(pip freeze)"

echo "Running Python miner program..."

python3 llm-miner-v0.0.1.py

deactivate

echo "Script execution completed."
