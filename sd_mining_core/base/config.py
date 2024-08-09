import os
import sys
import toml
import time
import requests
import argparse
from auth.generator import WalletGenerator

class BaseConfig:
    def __init__(self, config_file, cuda_device_id=0):
        try:
            self.config = toml.load(config_file)
        except Exception as e:
            raise FileNotFoundError(f"Failed to load configuration file: {config_file}. Error: {e}")

        # Parse all arguments
        args = self.parse_args()

        self.cuda_device_id = cuda_device_id
        self.num_cuda_devices = int(self.config['system'].get('num_cuda_devices', 1))
        self.log_filename = self.config['logging'].get('sd_log_filename', 'sd_miner.log')
        self.base_url = self.config['service']['base_url']
        self.signal_url = self.config['service']['signal_url']
        self.sd_timeout_seconds = self.config['service']['sd_timeout_seconds']
        self.s3_bucket = self.config['storage']['s3_bucket']
        self.base_dir = os.path.expanduser(self.config['storage'].get('base_dir', '.'))
        self.keys_dir = os.path.expanduser(self.config['storage'].get('keys_dir', '.'))
        self.model_config_url = self.config['model_config']['model_config_url']
        self.vae_config_url = self.config['model_config']['vae_config_url']
        self.lora_config_url = self.config['model_config']['lora_config_url']
        self.default_model_id = self.config['model_config']['default_sd_model_index']
        self.flux_dev_file_downloads = self.config['model_config']['flux_dev_file_downloads']

        os.makedirs(self.base_dir, exist_ok=True)

        self.min_deadline = int(self.config['system'].get('min_deadline', 60))
        self.sleep_duration = int(self.config['system'].get('sleep_duration', 2))
        self.reload_interval = int(self.config['system'].get('reload_interval', 600))

        self.last_heartbeat = time.time() - 10000
        self.loaded_models = {}
        self.loaded_loras = {}
        self.model_configs = {}
        self.vae_configs = {}
        self.lora_configs = {}

        self.log_level = args["log_level"]
        self.auto_confirm = args["auto_confirm"]
        self.exclude_sdxl = args["exclude_sdxl"]
        self.skip_signature = args["skip_signature"]
        self.skip_checksum = args["skip_checksum"]
        self.specified_model_id = args["model_id"]
        self.specified_device_id = args["cuda_device_id"]

        self.version = self.config['versions'].get('sd_version', 'unknown')
        self.session = requests.Session()

        # Create an instance of WalletGenerator
        abi_file = os.path.join(os.path.dirname(__file__), '..', '..', 'auth', 'abi.json')
        self.wallet_generator = WalletGenerator(config_file, abi_file)

    def parse_args(self):
        parser = argparse.ArgumentParser(description="Run the miner with configurable settings.")
        parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], type=str.upper, help="Set the logging level (default: INFO)")
        parser.add_argument("--auto-confirm", default="no", choices=["y", "yes", "no"], type=str.lower, help="Automatically proceed with the download without confirmation ('y', 'yes' to confirm, 'no' otherwise)")
        parser.add_argument("--exclude-sdxl", action="store_true", help="Exclude the sdxl model from downloading")
        parser.add_argument("--skip-signature", action="store_true", help="Skip signature verification")
        parser.add_argument("--skip-checksum", action="store_true", help="Skip checksum validation")
        parser.add_argument("--model-id", type=str, help="Specify the model ID to host (default: None)")
        parser.add_argument("--cuda-device-id", type=int, help="Specify the CUDA device ID to run SD miner (default: None)")
        args = parser.parse_args()

        # Convert auto-confirm argument to a boolean flag
        auto_confirm = True if args.auto_confirm in ["y", "yes"] else False
        exclude_sdxl = args.exclude_sdxl  # This will be True if the flag is used, False otherwise
        skip_signature = args.skip_signature  # This will be True if the flag is used, False otherwise
        skip_checksum = args.skip_checksum  # This will be True if the flag is used, False otherwise

        # Return a dictionary for easier access to each argument
        return {
            "log_level": args.log_level,
            "auto_confirm": auto_confirm,
            "exclude_sdxl": exclude_sdxl,
            "skip_signature": skip_signature,
            "skip_checksum": skip_checksum,
            "model_id": args.model_id,
            "cuda_device_id": args.cuda_device_id
        }