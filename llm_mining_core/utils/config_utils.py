import os
import re
from pathlib import Path
import subprocess
from llm_mining_core.config import BaseConfig, LLMServerConfig

def load_config(filename='config.toml'):
    """
    Loads the configuration settings from the specified TOML file.

    This function reads the configuration settings from the specified TOML file,
    creates instances of the BaseConfig and LLMServerConfig classes, and returns
    them as a tuple. If no filename is provided, it defaults to 'config.toml'.

    Parameters:
        filename (str, optional): The name of the TOML configuration file.
            Defaults to 'config.toml'.

    Returns:
        tuple: A tuple containing two objects:
            - base_config (BaseConfig): An instance of the BaseConfig class.
            - server_config (LLMServerConfig): An instance of the LLMServerConfig class.
    """
    base_dir = Path(__file__).resolve().parents[2]
    config_path = os.path.join(base_dir, filename)
    base_config = BaseConfig(config_path)
    server_config = LLMServerConfig(base_config)
    return base_config, server_config

def load_miner_ids():
    """
    Loads and validates the miner IDs from environment variables.
    This function searches for environment variables that match the pattern 'MINER_ID_\\d+' and extracts the miner IDs from them.
    It validates each miner ID to check if it is a valid EVM address with an optional suffix.
    If the miner ID is a valid EVM address without a suffix or with an empty suffix, it appends the GPU UUID to create a composite miner ID.
    Returns:
        list: A list of composite miner IDs extracted from the environment variables.
    """
    pattern = re.compile(r'MINER_ID_\d+')
    matching_env_vars = [var for var in os.environ if pattern.match(var)]
    highest_index = max(int(var.split('_')[-1]) for var in matching_env_vars) if matching_env_vars else 0
    miner_ids = [os.getenv(f'MINER_ID_{i}') for i in range(0, highest_index + 1)]
    
    composite_miner_ids = []
    evm_address_pattern = re.compile(r"^(0x[a-fA-F0-9]{40})(-[a-zA-Z0-9_]+)?$")

    for i, miner_id in enumerate(miner_ids):
        if miner_id is None:
            print(f"ERROR: Miner ID for GPU {i} not found in environment variables. Skipping...")
            continue
        
        match = evm_address_pattern.match(miner_id)
        if match:
            evm_address = match.group(1)
            suffix = match.group(2)
            
            if suffix:
                # Miner ID is a valid EVM address with a non-empty suffix
                composite_miner_ids.append(miner_id)
            else:
                # Miner ID is a valid EVM address without a suffix or with an empty suffix
                # Get the GPU UUID using nvidia-smi
                try:
                    output = subprocess.check_output(["nvidia-smi", "-L"]).decode("utf-8")
                    gpu_info = output.split("\n")[i].strip()
                    gpu_uuid_segment = gpu_info.split("GPU-")[1].split("-")[0]
                    short_uuid = gpu_uuid_segment[:6]
                    composite_miner_id = f"{evm_address}-{short_uuid}"
                    composite_miner_ids.append(composite_miner_id)
                except (subprocess.CalledProcessError, IndexError):
                    # nvidia-smi command failed or UUID not found
                    print(f"WARNING: Failed to retrieve GPU UUID for GPU {i}. Using original miner ID.")
                    composite_miner_ids.append(miner_id)
        else:
            # Miner ID is not a valid EVM address
            print(f"WARNING: Miner ID {miner_id} for GPU {i} is not a valid EVM address.")
            composite_miner_ids.append(miner_id)
    
    return composite_miner_ids