import os
import sys
import time
import toml
from collections import defaultdict
from auth.generator import WalletGenerator
from dotenv import load_dotenv
load_dotenv()

class BaseConfig:
    def __init__(self, config_file):
        # Load configuration from a TOML file
        self.config = toml.load(config_file)

        # General configurations
        self.base_url = self.config['service']['base_url']
        self.llm_url = self.config['service']['llm_url']
        self.signal_url = self.config['service']['signal_url']

        self.llm_timeout_seconds = self.config['service']['llm_timeout_seconds']
        self.port = sys.argv[7]
        self.log_filename = self.config['logging']['llm_log_filename']
        self.version = self.config['versions'].get('llm_version', 'unknown')
        self.api_base_url = f"{self.llm_url}:{self.port}/v1"
        self.served_model_name = sys.argv[3] # This is Heurist model name defined in https://github.com/heurist-network/heurist-models/blob/main/models.json
        self.signal_interval = self.config['system']['signal_interval']
        # Heartbeat and process management
        self.last_heartbeat = time.time() - 10000  # Set a default past timestamp
        self.last_heartbeat_per_miner = defaultdict(lambda: 0)  # Tracks heartbeats per miner_id
        self.sleep_duration = self.config['system']['sleep_duration']
        self.num_child_process = self.config['system']['num_child_process']
        self.gpu_to_use = sys.argv[8]
        self.concurrency_soft_limit = self.config['processing_limits']['concurrency_soft_limit']

        self.eos = "[DONE]"
        # A set of stop words to use - this is not a complete set, and you may want to
        # add more given your observation.
        self.stop_words = [
            "[End]",
            "[end]",
            "<|im_start|>",
            "<|im_end|>",
        ]
        # Create an instance of WalletGenerator
        abi_file = os.path.join(os.path.dirname(__file__), '..', '..', 'auth', 'abi.json')
        self.wallet_generator = WalletGenerator(config_file, abi_file)