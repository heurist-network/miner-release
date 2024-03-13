import os
import sys
import toml
import time

class BaseConfig:
    def __init__(self, config_file, cuda_device_id=0, log_level="INFO", auto_confirm=False):
        self.config = toml.load(config_file)
        self.cuda_device_id = cuda_device_id
        self.num_cuda_devices = int(self.config['general'].get('num_cuda_devices', 1))
        self.log_filename = self.config['general'].get('log_filename', 'miner.log')
        self.base_url = self.config['general']['base_url']
        self.s3_bucket = self.config['general']['s3_bucket']
        self.model_config_url = self.config['general']['model_config_url']
        self.vae_config_url = self.config['general']['vae_config_url']
        self.base_dir = os.path.expanduser(self.config['general'].get('base_dir', '.'))
        os.makedirs(self.base_dir, exist_ok=True)
        self.min_deadline = int(self.config['general'].get('min_deadline', 60))
        self.last_heartbeat = time.time() - 10000
        self.loaded_models = {}
        self.model_configs = {}
        self.vae_configs = {}
        self.log_level = log_level
        self.auto_confirm = auto_confirm
        self.sleep_duration = self.config['general']['sleep_duration']
        self.version = self.config['general']['version']    
