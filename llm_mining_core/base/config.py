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
    ]

    MODEL_TO_API_BASE_URL = {
        "openhermes-2.5-mistral-7b-gptq": "http://localhost:8081/v1",
    }

    def __init__(self, config_file):
        self.config = toml.load(config_file)
        self.num_cuda_devices = int(self.config['general'].get('num_cuda_devices', 1))
        self.miner_ids = [os.getenv(f'MINER_ID_{i}') for i in range(self.num_cuda_devices)]
        self.miner_ids_cycle = itertools.cycle(self.miner_ids)  # Create an iterator that cycles through the miner IDs

        self.base_url = self.config['general']['base_url']
        self.log_filename = self.config['general']['llm_log_filename']

        self.last_heartbeat = time.time() - 10000
        # Initialize a dictionary to track the last heartbeat for each miner_id
        self.last_heartbeat_per_miner = defaultdict(lambda: 0)
        self.sleep_duration = self.config['general']['sleep_duration']
        self.num_child_process = self.config['general']['num_child_process']

        self.eos = "[DONE]"

        # A set of stop words to use - this is not a complete set, and you may want to
        # add more given your observation.
        self.stop_words = [
            "[End]",
            "[end]",
            "\nReferences:\n",
            "\nSources:\n",
            "<|im_start|>",
            "<|im_end|>",
        ]
