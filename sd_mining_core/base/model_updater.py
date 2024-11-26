import os
import time
import hashlib
import logging
import requests
import schedule
from tqdm import tqdm
from pathlib import Path
from ..utils.file_utils import download_file

class ModelUpdater:
    def __init__(self, config, update_interval_seconds=60):
        self.config = config
        self.models_directory = Path(self.config['base_dir'])
        self.model_config_url = self.config['model_config_url']
        self.vae_config_url = self.config['vae_config_url']
        self.lora_config_url = self.config['lora_config_url']
        self.update_interval_seconds = update_interval_seconds
        self.session = requests.Session()  # Use a session for connection pooling

    def calculate_model_checksum(self, file_path):
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read and update hash string value in blocks of 4K
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def compare_model_checksums(self):
        """Compare the checksums of locally installed models with the checksums from the remote model list."""
        heurist_cache_dir = os.path.expanduser(self.config['base_dir'])
        if not os.path.exists(heurist_cache_dir):
            raise ValueError(f"Heurist cache directory does not exist: {heurist_cache_dir}")

        remote_checksums = {model_info['name']: model_info.get('checksum') for model_info in self.fetch_remote_model_list()}

        if self.config['specified_model_id'] is not None:
            local_files = [f"{self.config['specified_model_id']}.safetensors"]
            print(f"Validating checksum for specified model: {self.config['specified_model_id']}")
        else:
            local_files = [file_name for file_name in os.listdir(heurist_cache_dir) if file_name.endswith(".safetensors")]
            print("Checksum validation in progress (might take a few minutes)...")

        successful_count = 0
        valid_models_count = 0

        for index, file_name in enumerate(local_files, start=1):
            model_name = file_name[:-len(".safetensors")]
            model_path = os.path.join(heurist_cache_dir, file_name)

            if not os.path.exists(model_path):
                logging.warning(f"Model file not found: {file_name}")
                continue

            if model_name not in remote_checksums:
                logging.warning(f"Model not found in remote model list: {model_name}")
                continue

            valid_models_count += 1
            local_checksum = self.calculate_model_checksum(model_path)
            remote_checksum = remote_checksums[model_name]

            if not remote_checksum:
                logging.warning(f"No checksum found in remote model list for model: {model_name}")
            elif local_checksum.lower() == remote_checksum.lower():
                successful_count += 1
                print(f"{index}/{len(local_files)} Successful checksum match for {model_name}... \033[92m✓\033[0m")
            else:
                logging.warning(f"Checksum mismatch for model: {model_name}")

        if self.config['specified_model_id'] is None:
            print(f"Checksum validation completed. {successful_count}/{valid_models_count} models validated successfully.")
        elif valid_models_count == 0:
            print("Specified model not found or not in the remote model list.")
        # Note: For a single specified model, the success message is already printed in the loop

    def fetch_remote_model_list(self):
        """Fetch the combined list of models and VAEs from the configured URLs."""
        combined_models = []
        urls = [self.model_config_url, self.vae_config_url, self.lora_config_url]
        for url in urls:
            try:
                response = self.session.get(url)
                response.raise_for_status()  # Raises HTTPError for bad responses
                models = response.json()
                if isinstance(models, list):  # Ensure the response is a list
                    combined_models.extend(models)
                else:
                    logging.warning(f"Unexpected format received from {url}")
            except requests.exceptions.RequestException as e:
                print(f"Failed to fetch data from {url}: {e}")
                return None
        return combined_models

    def is_update_required(self, remote_model_list):
        """Check if the remote model list contains models that are not present locally."""
        # Get the list of local files without the '.safetensors' extension
        local_files = os.listdir(self.models_directory)
        local_model_names = {file_name.rsplit('.', 1)[0] for file_name in local_files if file_name.endswith('.safetensors')}

        # Incorporate exclusion logic for certain model types (e.g., "sdxl")
        remote_model_names = {
            model_info['name'] for model_info in remote_model_list
            if (('type' in model_info and ('sd' in model_info['type'] or 'vae' in model_info['type']))
             or 'lora' == model_info['type'])
            and (not self.config['exclude_sdxl'] or 'xl' not in model_info['type'])
        }
        # Determine if there are any models that are in the remote list but not locally
        missing_models = remote_model_names - local_model_names
        
        if missing_models:
            print(f"Missing models that require download: {missing_models}")
            return True
  
        return False  # No update required if all models are present

    def download_new_models(self, remote_model_list):
        """Download new models from the remote list that are not present in the local directory."""
        for model_info in remote_model_list:
            if not (('type' in model_info and ('sd' in model_info['type'] or 'vae' in model_info['type']))
                    or 'lora' == model_info['type']):
                continue
            # Using 'name' and 'file_url' keys to identify and download models
            model_name = model_info['name']
            model_url = model_info['file_url']
            file_name = f"{model_name}.safetensors"

            # The path where the model will be saved
            model_path = os.path.join(self.models_directory, file_name)
            
            # Only download if the model file doesn't already exist
            if not os.path.exists(model_path):
                print(f"Downloading new model: {model_name}")
                download_file(self.models_directory, model_url, file_name)
    
    def update_configs(self, remote_model_list):
        """Update local configuration with new models from the remote list."""
        # Iterate through the remote model list and update config.model_configs
        for model_info in remote_model_list:
            model_name = model_info['name']
            # Check if it's a model or a VAE based on some criteria, for example, the presence of a specific key
            if 'vae' in model_info['type']:
                # It's a VAE, update vae_configs
                if model_name not in self.config['vae_configs']:
                    self.config['vae_configs'][model_name] = model_info
                    # Assuming 'base_type' presence indicates a LoRa configuration
            elif 'lora' == model_info['type']:
                # It's a LoRa configuration, update lora_configs
                if model_name not in self.config['lora_configs']:
                    self.config['lora_configs'][model_name] = model_info
            elif 'sd' in model_info['type']:
                # It's a regular model, update model_configs
                if model_name not in self.config['model_configs']:
                    self.config['model_configs'][model_name] = model_info

    def update_models(self):
        """Update models by checking for new models and downloading them if necessary."""
        remote_model_list = self.fetch_remote_model_list()
        if not remote_model_list:
            print("Could not fetch remote model list. Skipping update.")
            return

        if self.is_update_required(remote_model_list):
            self.download_new_models(remote_model_list)
            self.update_configs(remote_model_list)
            print("Model updates completed.")
        else:
            logging.debug("No model updates required.")

    def start_scheduled_updates(self):
        """Start periodic model updates based on the specified interval."""
        schedule.every(self.update_interval_seconds).seconds.do(self.update_models)
        print(f"Scheduled model updates every {self.update_interval_seconds} seconds.")
        while True:
            schedule.run_pending()
            time.sleep(1)