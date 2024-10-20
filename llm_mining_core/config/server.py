import os
import sys
import time
import logging
import subprocess
from openai import OpenAI

class LLMServerConfig:
    MAX_MODEL_LEN = 8192

    def __init__(self, base_config):
        self.base_config = base_config
        self.num_gpus = len(self.base_config.gpu_to_use.split(','))
        os.environ["CUDA_VISIBLE_DEVICES"] = self.base_config.gpu_to_use

        self.model_id = sys.argv[1]  # HF Model ID from the first argument
        self.model_quantization = None if sys.argv[2] == 'None' else sys.argv[2]  # Model quantization from the second argument
        self.served_model_name = sys.argv[3]  # Served model name from the third argument
        self.gpu_memory_util  = sys.argv[4] # GPU memory utilization ratio for vllm
        self.model_revision = None if len(sys.argv) <= 5 or sys.argv[5] == 'None' else sys.argv[5]  # Model revision from the fourth argument, if present
        self.tool_call_parser = None if len(sys.argv) <= 10 or sys.argv[10] == 'None' else sys.argv[10]
        self.process = None
    
    def initialize_client(self):
        return OpenAI(base_url=self.base_config.api_base_url, api_key="N/A")

    def start_llm_server(self):
        """
        Start the LLM server with the provided model details.
        """
        cmd = [
            "python", "-m", "vllm.entrypoints.openai.api_server",
            "--model", self.model_id,
            "--served-model-name", self.served_model_name,
            "--max-model-len", str(self.MAX_MODEL_LEN),
            "--uvicorn-log-level", "warning",
            "--disable-log-requests",
            "--dtype", "half",
            "--port", str(self.base_config.port),
            "--tensor-parallel-size",str(self.num_gpus),
            "--gpu-memory-utilization", self.gpu_memory_util,
        ]

        if self.tool_call_parser:
            cmd.extend(["--tool-call-parser", self.tool_call_parser, "--enable-auto-tool-choice"])
        if self.model_revision:
            cmd.extend(["--revision", self.model_revision])
        if self.model_quantization:
            cmd.extend(["--quantization", self.model_quantization])

        self.process = subprocess.Popen(cmd)
        return self.process

    def terminate_llm_server(self):
        if self.process:
            logging.info("Terminating LLM server process...")
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
            logging.info("LLM server process terminated.")

    def wait_for_server_ready(self, timeout=120, interval=10):
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.health_check():
                logging.info("Server is ready.")
                return True
            else:
                logging.info("Server not ready yet, waiting...")
                time.sleep(interval)
        logging.error("Timeout waiting for server to be ready.")
        return False

    def health_check(self):
        try:
            client = self.initialize_client()
            print("Initialized client for model:", self.served_model_name)

            start_time = time.time()
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": "write a 200-word essay on the topic of the future of Ethereum"}],
                model=self.served_model_name,
                max_tokens=200,
            )
            end_time = time.time()
            inference_latency = end_time - start_time
            total_tokens = response.usage.total_tokens
            print(f"Test prompt with {self.served_model_name}. Completed processing {total_tokens} tokens. Time: {inference_latency}s. Tokens/s: {total_tokens / inference_latency}")
            if total_tokens / inference_latency < 5:
                print(f"Warning: Inference speed is too slow for model {self.served_model_name}.")
            return True
        except Exception as e:
            print(f"Model {self.served_model_name} is not ready. Waiting for LLM Server to finish loading the model to start.")
            return False