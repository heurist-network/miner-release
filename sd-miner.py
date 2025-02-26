import os
import re
import sys
import time
import torch
import logging
import signal
import threading
import subprocess
import json
import asyncio
from pathlib import Path
from itertools import cycle
from dotenv import load_dotenv
from multiprocessing import Process, set_start_method
from auth.generator import WalletGenerator
from sd_mining_core.stats import SDMinerStats

from sd_mining_core.base import BaseConfig, ModelUpdater
from sd_mining_core.utils import (
    check_cuda, get_hardware_description,
    fetch_and_download_config_files, get_local_model_ids,
    post_request, log_response, submit_job_result,
    initialize_logging_and_args,
    load_default_model, reload_model,
)

class MinerConfig(BaseConfig):
    def __init__(self, config_file, cuda_device_id=0):
        super().__init__(config_file, cuda_device_id)
        if not self.skip_signature:
            self.wallet_generator = WalletGenerator(config_file, abi_file = os.path.join(os.path.dirname(__file__), 'auth', 'abi.json'))
        load_dotenv()  # Load the environment variables
        
        miner_ids = self._load_and_validate_miner_ids()
        self.miner_id = self._assign_miner_id(miner_ids, cuda_device_id)
        self.stats_manager = SDMinerStats()

    def _load_and_validate_miner_ids(self):
        miner_ids = [os.getenv(f'MINER_ID_{i}') for i in range(self.num_cuda_devices)]
        if not self.skip_signature:
            self.wallet_generator.validate_miner_keys(miner_ids)

        composite_miner_ids = []
        evm_address_pattern = re.compile(r"^(0x[a-fA-F0-9]{40})(-[a-zA-Z0-9_]+)?$")
        for i, miner_id in enumerate(miner_ids):
            if miner_id is None:
                raise ValueError(f"Miner ID for GPU {i} not found in .env.")
            
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

    def _assign_miner_id(self, miner_ids, cuda_device_id):
        if self.num_cuda_devices > 1 and miner_ids[cuda_device_id]:
            return miner_ids[cuda_device_id]
        elif miner_ids[0]:
            return miner_ids[0]
        else:
            raise ValueError("miner_id not found in .env.")

def load_config(filename='config.toml', cuda_device_id=0):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, filename)
    return MinerConfig(config_path, cuda_device_id)

def send_miner_request(config, model_id, min_deadline):
    request_data = {
        "miner_id": config.miner_id,
        "model_id": model_id,
        "min_deadline": min_deadline
    }
    if time.time() - config.last_heartbeat >= 60:
        request_data['hardware'] = get_hardware_description(config)
        request_data['version'] = config.version
        config.last_heartbeat = time.time()
        logging.debug(f"Heartbeat updated at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(config.last_heartbeat))} with hardware '{request_data['hardware']}' and version {config.version} for miner ID {config.miner_id}.")
    
    start_time = time.time()
    response = post_request(config, config.base_url + "/miner_request", request_data, config.miner_id)
    end_time = time.time()
    request_latency = end_time - start_time

    # Assuming response.text contains the full text response from the server
    warning_indicator = "Warning:"
    if response and warning_indicator in response.text:
        # Extract the warning message and use strip() to remove any trailing quotation marks
        warning_message = response.text.split(warning_indicator)[1].strip('"')
        print(f"WARNING: {warning_message}")

    response_data = log_response(response, config.miner_id)

    try:
        # Check if the response contains a valid job and print the friendly message
        if response_data and 'job_id' in response_data and 'model_id' in response_data:
            job_id = response_data['job_id']
            model_id = response_data['model_id']
    except Exception as e:
        logging.error(f"Failed to process response data: {e}")

    return response_data, request_latency

def check_and_reload_model(config, last_signal_time):
    current_time = time.time()
    # Only proceed if it's been at least 600 seconds
    if current_time - last_signal_time >= config.reload_interval:
        model_id = list(config.loaded_loras.keys())[0] if config.loaded_loras else list(config.loaded_models.keys())[0] if config.loaded_models else None
        if model_id is None:
            logging.warning("No loaded models found. Posting to miner_signal to load a new model.")
            # continue to get the next signal
        
        request_data = {
            "miner_id": config.miner_id,
            "model_type": "SD",
            "model_id": model_id,
            "hardware": get_hardware_description(config),
            "version": config.version, # format is like "sd-v1.2.0"
            "options": {"exclude_sdxl": config.exclude_sdxl}
        }

        # Add skip_update if a specific model is set
        if config.specified_model_id:
            request_data["skip_update"] = True

        response = post_request(config, config.signal_url + "/miner_signal", request_data, config.miner_id)

        # Process the response only if it's valid
        if response and response.status_code == 200:
            model_id_from_signal = response.json().get('model_id')
            # Proceed if the model is in local storage and not already loaded
            if model_id_from_signal in get_local_model_ids(config) and model_id_from_signal not in config.loaded_models and model_id_from_signal not in config.loaded_loras:
                reload_model(config, model_id_from_signal)
                last_signal_time = current_time  # Update last_signal_time after reloading model
        else:
            logging.error(f"Failed to get a valid response from /miner_signal for miner_id {config.miner_id}.")
    
    # Return the updated or unchanged last_signal_time
    return last_signal_time if current_time - last_signal_time < config.reload_interval else current_time


async def update_job_stats(config, model_id, success=True):
    """Update the job statistics for the given model ID."""
    try:
        await config.stats_manager.update_model_stats(model_id, successful=success)
        logging.debug(f"Updated stats for model {model_id}: {'successful' if success else 'failed'} job")
    except Exception as e:
        logging.error(f"Failed to update job statistics: {e}")

def process_jobs(config):
    current_model_id = next(iter(config.loaded_models), None)
    current_lora_id = next(iter(config.loaded_loras), None)
    model_ids = get_local_model_ids(config)
    if not model_ids:
        logging.debug("No models found. Exiting...")
        sys.exit(0)

    model_id_to_send = current_lora_id if current_lora_id is not None else current_model_id
    job, request_latency = send_miner_request(config, model_id_to_send, config.min_deadline)
    if not job:
        logging.info("No job received.")
        return False

    job_start_time = time.time()
    logging.info(f"Processing Request ID: {job['job_id']}. Model ID: {job['model_id']}.")
    
    success = True
    try:
        submit_job_result(config, config.miner_id, job, job['temp_credentials'], job_start_time, request_latency)
    except Exception as e:
        logging.error(f"Error processing job: {e}")
        success = False
    asyncio.run(update_job_stats(config, job['model_id'], success))
    
    return True

def main(cuda_device_id):
    try:
        torch.cuda.set_device(cuda_device_id)
        config = load_config(cuda_device_id=cuda_device_id)
        config = initialize_logging_and_args(config, cuda_device_id, miner_id=config.miner_id)
        
        # The parent process should have already downloaded the model files
        # Now we just need to load them into memory
        fetch_and_download_config_files(config)

        # Load the default model before entering the loop
        load_default_model(config)

        last_signal_time = time.time()
        while True:
            try:
                if not config.specified_model_id:
                    last_signal_time = check_and_reload_model(config, last_signal_time)
                executed = process_jobs(config)
            except Exception as e:
                logging.error("Error occurred:", exc_info=True)
                executed = False
            if not executed:
                time.sleep(config.sleep_duration)
            
    except Exception as e:
        print(f"Error in main function for cuda_device_id {cuda_device_id}: {str(e)}")
        raise  # Re-raise the exception to see the full traceback

if __name__ == "__main__":
    processes = []
    def signal_handler(signum, frame):
        for p in processes:
            p.terminate()
            p.join()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    set_start_method('spawn', force=True)
    
    config = load_config()
    config = initialize_logging_and_args(config, miner_id=config.miner_id)

    if config.num_cuda_devices > torch.cuda.device_count():
        print("Number of CUDA devices specified in config is greater than available. Exiting...")
        sys.exit(1)
    check_cuda()

    fetch_and_download_config_files(config)

    # Initialize and start model updater before processing tasks
    model_updater = ModelUpdater(config=config.__dict__)  # Assuming config.__dict__ provides necessary settings
    if not config.skip_checksum:
        model_updater.compare_model_checksums()
    # Start the model updater in a separate thread
    if not config.specified_model_id:
        updater_thread = threading.Thread(target=model_updater.start_scheduled_updates)
        updater_thread.start()
    
    # TODO: There appear to be 1 leaked semaphore objects to clean up at shutdown
    # Launch a separate process for each CUDA device
    try:
        if config.specified_device_id is None:
            print(f"Creating processes for {config.num_cuda_devices} CUDA devices")
            for i in range(config.num_cuda_devices):
                print(f"Creating process for CUDA device {i}")
                p = Process(target=main, args=(i,))
                p.start()
                processes.append(p)

            for p in processes:
                p.join()
        else:
            print(f"Creating process for specified CUDA device {config.specified_device_id}")
            p = Process(target=main, args=(config.specified_device_id,))
            p.start()
            processes.append(p)
            p.join()
    except Exception as e:
        print(f"Error in process creation: {str(e)}")
        raise  # Re-raise the exception to see the full traceback
