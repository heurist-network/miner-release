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
        "openhermes-2.5-mistral-7b-gptq": "http://localhost:8000/v1",
    }

    def __init__(self, config_file):
        self.config = toml.load(config_file)

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
            "<|im_start|>",
            "<|im_end|>",
        ]
