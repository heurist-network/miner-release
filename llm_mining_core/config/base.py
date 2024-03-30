import os
import time
import toml
import itertools
from collections import defaultdict
from dotenv import load_dotenv
load_dotenv()

class BaseConfig:
    SUPPORTED_MODEL_IDS = [
        "openhermes-2.5-mistral-7b-gptq",
        "openhermes-2-pro-mistral-7b",
        "mistralai/mistral-7b-instruct-v0.2",
        "mistralai/mixtral-8x7b-instruct-v0.1",
        "meta-llama/llama-2-70b-chat",
        "openhermes-mixtral-8x7b-gptq"
    ]

    def __init__(self, config_file):
        # Load configuration from a TOML file
        self.config = toml.load(config_file)

        # General configurations
        self.base_url = self.config['service']['base_url']
        self.llm_url = self.config['service']['llm_url']
        self.port = self.config['service'].get('vllm_port', 8000)  # Allows for a configurable port with a default of 8000
        self.log_filename = self.config['logging']['llm_log_filename']
        
        # Dynamic API base URLs based on SUPPORTED_MODEL_IDS and configurable port
        self.MODEL_TO_API_BASE_URL = {model_id: f"{self.llm_url}:{self.port}/v1" for model_id in self.SUPPORTED_MODEL_IDS}

        # Heartbeat and process management
        self.last_heartbeat = time.time() - 10000  # Set a default past timestamp
        self.last_heartbeat_per_miner = defaultdict(lambda: 0)  # Tracks heartbeats per miner_id
        self.sleep_duration = self.config['system']['sleep_duration']
        self.num_child_process = self.config['system']['num_child_process']
        self.gpu_to_use = self.config['system']['gpu_ids']

        self.eos = "[DONE]"
        # A set of stop words to use - this is not a complete set, and you may want to
        # add more given your observation.
        self.stop_words = [
            "[End]",
            "[end]",
            "<|im_start|>",
            "<|im_end|>",
        ]