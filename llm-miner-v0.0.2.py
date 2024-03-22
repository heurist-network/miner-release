import os
import re
import requests
import sys
import time
from multiprocessing import Process, set_start_method
import signal
import subprocess
import atexit

from llm_mining_core.base import BaseConfig
from llm_mining_core.utils import (
    initialize_client,
    decode_prompt_llama, decode_prompt_mistral, decode_prompt_chatml,
    send_miner_request
)

MODEL_ID = "TheBloke/OpenHermes-2.5-Mistral-7B-GPTQ"
MODEL_REVISION = "gptq-8bit-32g-actorder_True"
MODEL_QUANTIZATION = "gptq"
MAX_MODEL_LEN = 18000
SERVED_MODEL_NAME= "openhermes-2.5-mistral-7b-gptq"
CHAT_TEMPLATE = "{% for message in messages %}{{'<|im_start|>' + message['role'] + '\n' + message['content'] + '<|im_end|>' + '\n'}}{% endfor %}{% if add_generation_prompt %}{{ '<|im_start|>assistant\n' }}{% endif %}"

# Function to start the LLM server
def start_llm_server():
    # Note: for option "max-model-len", if not specified, it may resulte in error below
    # "ValueError: The model's max seq len (32768) is larger than the maximum number of tokens 
    # that can be stored in KV cache (18336). Try increasing `gpu_memory_utilization` or decreasing `max_model_len` 
    # when initializing the engine.""

    cmd = [
        "python", "-m", "vllm.entrypoints.openai.api_server",
        "--model", MODEL_ID,
        "--served-model-name", SERVED_MODEL_NAME,
        "--revision", MODEL_REVISION,
        "--quantization", MODEL_QUANTIZATION,
        "--max-model-len", str(MAX_MODEL_LEN),
        "--chat-template", CHAT_TEMPLATE,
        "--disable-log-requests"
    ]
    
    # Start the server in the background and return the process referenced
    process = subprocess.Popen(cmd)
    return process

# Function to terminate the LLM server process
def terminate_llm_server(process):
    if process:
        print("Terminating LLM server process...")
        process.terminate()
        try:
            process.wait(timeout=10)  # Wait for the process to terminate
        except subprocess.TimeoutExpired:
            process.kill()  # Force kill if not terminated within timeout
        print("LLM server process terminated.")

# Function to wait for the LLM server to be ready
def wait_for_server_ready(config, timeout=120, interval=10):
    start_time = time.time()
    while time.time() - start_time < timeout:
        if health_check(config, MODEL_ID):
            print("Server is ready.")
            return True
        else:
            print("Server not ready yet, waiting...")
            time.sleep(interval)
    print("Timeout waiting for server to be ready.")
    return False



def load_config(filename='config.toml'):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, filename)
    return BaseConfig(config_path)

def load_miner_ids():
    pattern = re.compile(r'MINER_ID_\d+')
    
    # Find all environment variables that match the pattern
    matching_env_vars = [var for var in os.environ if pattern.match(var)]
    
    # Extract the highest index from the matching environment variables
    highest_index = max(int(var.split('_')[-1]) for var in matching_env_vars) if matching_env_vars else 0
    
    # Use the highest index to dynamically generate the list of miner IDs
    miner_ids = [os.getenv(f'MINER_ID_{i}') for i in range(0, highest_index + 1)]

    return miner_ids

def generate(config, miner_id, job_id, prompt, temperature, max_tokens, seed, stop, use_stream_flag, model_id, request_latency):
    print(f"Processing Request ID: {job_id}. Model ID: {model_id}. Miner ID: {miner_id}")

    client = initialize_client(config, model_id)
    if client is None:
        print(f"Failed to initialize API client for model {model_id}.")
        return
    
    decoded_prompt = None
    if "openhermes" in model_id:
        decoded_prompt = decode_prompt_chatml(prompt)
    elif "llama" in model_id:
        decoded_prompt = decode_prompt_llama(prompt)
    elif "mistral" in model_id:
        decoded_prompt = decode_prompt_mistral(prompt)
    else:
        print(f"Model {model_id} not supported.")
        return

    if use_stream_flag:
        print("Streaming mode enabled")
        stream = client.chat.completions.create(
            messages=decoded_prompt,
            model=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop,
            seed=seed,
            stream=True,
        )

        first_chunk = next(stream)
        initial_data = None
        if first_chunk.choices[0].delta is not None:
            initial_data = first_chunk.choices[0].delta.content
                
        if not initial_data:
            second_chunk = next(stream)
            if second_chunk.choices[0].delta is not None:
                second_data = second_chunk.choices[0].delta.content
                if not second_data:
                    print("No initial data received from the stream. Exiting...")
                    return

        def generate_data(stream):
            yield initial_data

            buffer = ''  # Initialize a buffer to accumulate characters into words
            try:
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        data = chunk.choices[0].delta.content
                        buffer += data  # Add the new data to the buffer

                        # If the data contains a word boundary (e.g., space, punctuation followed by a space),
                        # split the buffer into words and yield them except for the last partial word.
                        if ' ' in buffer or '\n' in buffer:
                            words = buffer.split(' ')
                            for word in words[:-1]:  # Yield all but the last item, which might be incomplete
                                complete_word = word
                                yield complete_word + " "
                            buffer = words[-1]  # Keep the last item as the start of the next word

                        # Check for stop words in the buffer. If any, remove the stop word and any texts after the stop word.
                        if any(word in buffer for word in stop):
                            for word in stop:
                                if word in buffer:
                                    stop_index = buffer.index(word)
                                    buffer = buffer[:stop_index]
                                    # If the buffer is not empty, yield it
                                    if buffer:
                                        yield buffer + " "
                                    yield config.eos # Ensure EOS is sent when the stream ends
                                    break

                if buffer:  # If there's anything left in the buffer, yield it as well
                    yield buffer + " "
                yield config.eos  # Ensure EOS is sent when the stream ends
            except StopIteration:
                if buffer:  # Ensure the last partial word is sent before ending
                    yield buffer + " "
                yield config.eos
        
        # Make a POST request to the server after initial data is received
        with requests.Session() as session:
            try:
                headers = {
                    'job_id': str(job_id),
                    'miner_id': str(miner_id),
                    'Content-Type': 'text/event-stream'    
                }
                response = session.post(
                    f"{config.base_url}/miner_submit_stream",
                    headers=headers,
                    data=generate_data(stream),
                    stream=True
                )
                response.raise_for_status()
            except requests.RequestException as e:
                print(f"Failed to submit stream: {e}")

    else:
        print("Non-streaming mode")
        # Non-streaming logic
        start_time = time.time()
        response = client.chat.completions.create(
            messages=decoded_prompt,
            model=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop,
            seed=seed
        )
        end_time = time.time()
        inference_latency = end_time - start_time
        res = response.choices[0].message.content
        total_tokens = response.usage.total_tokens
        print(f"Completed processing {total_tokens} tokens. Time: {inference_latency}s. Tokens/s: {total_tokens / inference_latency}")
        # if the words is in stop_words, truncate the result
        for word in stop:
            if word in res:
                res = res[:res.index(word)]
                break
        url = config.base_url + "/miner_submit"
        result = {
            "miner_id": miner_id,
            "job_id": job_id,
            "result": {"Text": res},
            "request_latency": request_latency,
            "inference_latency": inference_latency
        }
        requests.post(url, json=result)
        
def health_check(config, model_id):
    try:
        client = initialize_client(config, model_id)

        print("Initialized client for model:", model_id)

        start_time = time.time()
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": "write a 200-word essay on the topic of the future of Ethereum"}],
            model=model_id,
            max_tokens=200,
        )
        end_time = time.time()
        inference_latency = end_time - start_time
        total_tokens = response.usage.total_tokens
        print(f"Test prompt with {model_id}. Completed processing {total_tokens} tokens. Time: {inference_latency}s. Tokens/s: {total_tokens / inference_latency}")
        if total_tokens / inference_latency < 5:
            print(f"Warning: Inference speed is too slow for model {model_id}.")
        return True
    except Exception as e:
        print(f"Model {model_id} is not ready. Waiting for LLM Server to finish loading the model to start.")
        return False

def worker(miner_id):
    config = load_config()
    while True:
        try:
            job, request_latency = send_miner_request(config, miner_id)
            if job is not None:
                model_id = job['model_id'] # Extract model_id from the job
                prompt = job['model_input']['LLM']['prompt']
                temperature = job['model_input']['LLM']['temperature']
                max_tokens = job['model_input']['LLM']['max_tokens']
                seed = job['model_input']['LLM']['seed']
                use_stream = job['model_input']['LLM']['use_stream']
                if seed == -1: # Handling for seed if specified as -1
                    seed = None
                stop = config.stop_words # Assuming stop_words are defined earlier in the script
                
                # Process the job with the miner
                generate(config, miner_id, job['job_id'], prompt, temperature, max_tokens, seed, stop, use_stream, model_id, request_latency)
            else:
                #print(f"No job received for miner {miner_id}. Waiting for the next round...")
                pass
        except Exception as e:
            print(f"Error occurred for miner {miner_id}: {e}")
            import traceback
            traceback.print_exc()
        
        time.sleep(config.sleep_duration)

def main_loop():
    processes = []
    def signal_handler(signum, frame):
        for p in processes:
            p.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    set_start_method('spawn', force=True)

    config = load_config()
    miner_ids = load_miner_ids()
    
    # Do health check every 10 seconds, until it returns true
    # TODO: refactor: model_id should be a config.toml item or .env item
    while not health_check(config, config.SUPPORTED_MODEL_IDS[0]):
        time.sleep(10)

    try:
        # Explicitly use only the first miner_id; ensure config.miner_ids[0] exists
        if not miner_ids:
            print("No miner_ids provided in .env file")
            sys.exit(1)
        
        miner_id = miner_ids[0]  # Only the first miner_id is used for processing
        if miner_id is None or not miner_id.startswith("0x"):
            print("Warning: Configure your ETH address correctly in the .env file. Current value:", miner_id)
            #sys.exit(1) 

        for _ in range(config.num_child_process):
            process = Process(target=worker, args=(miner_id,))
            process.start()
            processes.append(process)

        print("LLM miner started")

        # Wait for all processes to finish
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        print("Main process interrupted. Terminating child processes.")
        for p in processes:
            p.terminate()
            p.join()

if __name__ == "__main__":
    llm_server_process = start_llm_server()
    atexit.register(terminate_llm_server, llm_server_process)

    def signal_handler(signum, frame):
        terminate_llm_server(llm_server_process)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Give the server some time to start
    time.sleep(10)  # Consider using wait_for_server_ready here instead to ensure the server is ready
    main_loop()