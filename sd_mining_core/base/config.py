import os
import sys
import toml
import time
from auth.generator import WalletGenerator

class BaseConfig:

    def __init__(self, config_file, cuda_device_id=0, log_level="INFO", auto_confirm=False, exclude_sdxl=False):
        try:
            self.config = toml.load(config_file)
        except Exception as e:
            raise FileNotFoundError(f"Failed to load configuration file: {config_file}. Error: {e}")

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
        self.log_level = log_level
        self.auto_confirm = auto_confirm
        self.exclude_sdxl = exclude_sdxl
        self.version = self.config['versions'].get('sd_version', 'unknown')

        # Create an instance of WalletGenerator
        abi_file = os.path.join(os.path.dirname(__file__), '..', '..', 'auth', 'abi.json')
        self.wallet_generator = WalletGenerator(config_file, abi_file)