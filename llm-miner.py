import os
import sys
import time
import signal
import atexit
import random
import logging
import requests
import threading
import json
from auth.generator import WalletGenerator
from multiprocessing import Process, set_start_method
from openai.types.chat import ChatCompletion

from llm_mining_core.utils import (
    load_config, load_miner_ids,
    send_miner_request,
    configure_logging,
    get_metric_value,
    check_vllm_server_status,
    send_model_info_signal
)

from llm_mining_core.config.server import LLMServerConfig

def decode_prompt_json(prompt_json):
    try:
        return json.loads(prompt_json)
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode prompt JSON: {e}")
        return None

def generate(base_config, server_config, miner_id, job_id, decoded_prompt, temperature, max_tokens, seed, stop, use_stream_flag, model_id, request_latency, decoded_tools=None, extra_body=None):
    logging.info(f"Processing Request ID: {job_id}. Model ID: {model_id}. Miner ID: {miner_id}")

    client = server_config.initialize_client()
    if client is None:
        logging.error(f"Failed to initialize API client for model {model_id}.")
        return

    if max_tokens > 4096:
        max_tokens = 4096

    try:
        if use_stream_flag:
            logging.info("Streaming mode enabled")
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
                        logging.error("No initial data received from the stream. Exiting...")
                        return
                    initial_data = second_data

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
                                        yield base_config.eos # Ensure EOS is sent when the stream ends
                                        break

                    if buffer:  # If there's anything left in the buffer, yield it as well
                        yield buffer + " "
                    yield base_config.eos  # Ensure EOS is sent when the stream ends
                except StopIteration:
                    if buffer:  # Ensure the last partial word is sent before ending
                        yield buffer + " "
                    yield base_config.eos
            
            # Make a POST request to the server after initial data is received
            with requests.Session() as session:
                try:
                    headers = {
                        'job_id': str(job_id),
                        'miner_id': str(miner_id),
                        'Content-Type': 'text/event-stream'    
                    }
                    response = session.post(
                        f"{base_config.base_url}/miner_submit_stream",
                        headers=headers,
                        data=generate_data(stream),
                        stream=True
                    )
                    response.raise_for_status()
                except requests.RequestException as e:
                    logging.error(f"Failed to submit stream: {e}")

        else:
            logging.info("Non-streaming mode")
            # Non-streaming logic
            start_time = time.time()
            
            # Create a dictionary of parameters for the API call
            params = {
                "messages": decoded_prompt,
                "model": model_id,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stop": stop,
                "seed": seed,
            }
            
            # Add extra_body parameters if provided
            if extra_body:
                params["extra_body"] = extra_body
            
            # Only add tools and tool_choice if tools are provided
            if decoded_tools:
                params["tools"] = decoded_tools
                params["tool_choice"] = "auto"
            
        
            response = client.chat.completions.create(**params)

            # Convert the response to a ChatCompletion object
            chat_completion = ChatCompletion(**response.model_dump())
            
            # Extract the choices array
            result_choices = chat_completion.choices

            end_time = time.time()
            inference_latency = end_time - start_time
            

            total_tokens = response.usage.total_tokens
            logging.info(f"Completed processing {total_tokens} tokens. Time: {inference_latency}s. Tokens/s: {total_tokens / inference_latency}")

            url = base_config.base_url + "/miner_submit"
            result = {
                "miner_id": miner_id.lower(),
                "job_id": job_id,
                "result": {"Text": json.dumps([choice.model_dump() for choice in result_choices])},
                "request_latency": request_latency,
                "inference_latency": inference_latency
            }
            if not base_config.skip_signature:
                identity_address, signature = base_config.wallet_generator.generate_signature(miner_id)
                result["signature"] = signature
                result["identity_address"] = identity_address
            res = base_config.session.post(url, json=result)

            if(res.status_code == 200):
                logging.info(f"Result submitted successfully for job_id: {job_id}")
            else:
                logging.error(f"Failed to submit result for job_id: {job_id} with status code: {res.status_code}")
    except Exception as e:
        logging.error(f"Error during text generation request: {str(e)}")
        return
    
def worker(miner_id):
    base_config, server_config = load_config()
    configure_logging(base_config, miner_id)

    while True:
        if not check_vllm_server_status():
            logging.error(
                f"vLLM server process for model {server_config.served_model_name} is not running. Exiting the llm miner program."
            )
            sys.exit(1)
        try:
            # Check if the number of running requests exceeds the maximum concurrent requests
            num_requests = get_metric_value("num_requests_running", base_config)
            if num_requests is None:
                num_requests = 0  # Set to 0 if None
            if num_requests >= base_config.concurrency_soft_limit:
                time.sleep(base_config.sleep_duration)
                continue

            # **Add job fetching and processing here**
            job, request_latency = send_miner_request(
                base_config, miner_id, base_config.served_model_name
            )
            if job is not None:
                job_start_time = time.time()
                # Extract job parameters
                model_id = job['model_id']
                prompt = job['model_input']['LLM']['prompt']
                temperature = job['model_input']['LLM']['temperature']
                max_tokens = job['model_input']['LLM']['max_tokens']
                seed = job['model_input']['LLM']['seed']
                use_stream = job['model_input']['LLM']['use_stream']
                if seed == -1:
                    seed = None
                stop = base_config.stop_words
                # If function calling is enabled, pass tools to generate()
                decoded_prompt = decode_prompt_json(prompt)
                if decoded_prompt is None:
                    logging.error(f"Failed to decode prompt for model {model_id}. Exiting.")
                    return
                
                tools = None
                decoded_tools = None
                extra_body = None 

                if job['model_input']['LLM'].get('tools', None):
                    tools = job['model_input']['LLM']['tools']
                    decoded_tools = decode_prompt_json(tools)

                # Call the generate function
                extra_body = job['model_input']['LLM'].get('extra_body', None)
                if extra_body:
                    extra_body = json.loads(extra_body)
                generate(
                    base_config, server_config, miner_id, job['job_id'], decoded_prompt,
                    temperature, max_tokens, seed, stop, use_stream, model_id,
                    request_latency, decoded_tools, extra_body
                )
                job_end_time = time.time()
                total_processing_time = job_end_time - job_start_time
                if total_processing_time > base_config.llm_timeout_seconds:
                    print(
                        "Warning: the previous request timed out. You will not earn points. Please check miner configuration or network connection."
                    )
            else:
                pass

        except Exception as e:
            logging.error(f"Error occurred for miner {miner_id}: {e}")
            import traceback
            traceback.print_exc()

        time.sleep(base_config.sleep_duration)

def periodic_send_model_info_signal(base_config, miner_id, last_signal_time):
    while True:
        last_signal_time = send_model_info_signal(base_config, miner_id, last_signal_time)
        time.sleep(base_config.signal_interval) # Adjust the sleep interval based on your desired frequency

def main_loop():
    processes = []
    def signal_handler(signum, frame):
        for p in processes:
            p.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    set_start_method('spawn', force=True)

    base_config, server_config = load_config()
    miner_ids = load_miner_ids()
    
    # Do health check every 10 seconds, until it returns true
    # TODO: refactor: model_id should be a config.toml item or .env item
    while not server_config.health_check():
        time.sleep(10)

    try:
        # Explicitly use only the first miner_id; ensure config.miner_ids[0] exists
        if not miner_ids:
            logging.error("No miner_ids provided in .env file")
            sys.exit(1)
        
        miner_id_index = int(sys.argv[6])
        if miner_id_index >= len(miner_ids):
            logging.warn("Invalid miner_id_index. Using the first miner_id found")
            miner_id = miner_ids[0]
        else:
            miner_id = miner_ids[miner_id_index]
        if miner_id is None or not miner_id.startswith("0x"):
            logging.warning(f"Warning: Configure your ETH address correctly in the .env file. Current value: {miner_id}")
        configure_logging(base_config, miner_id)

        for _ in range(base_config.num_child_process):
            process = Process(target=worker, args=(miner_id,))
            random_number = random.randint(0, base_config.sleep_duration)
            time.sleep(random_number) # Sleep for a while to avoid all processes starting at the same time
            process.start()
            processes.append(process)

        logging.info("LLM miner started")

        # Start the periodic function in a separate thread
        last_signal_time = time.time()
        periodic_thread = threading.Thread(target=periodic_send_model_info_signal, args=(base_config, miner_id, last_signal_time))
        periodic_thread.start()

        # Wait for all processes to finish
        for process in processes:
            process.join()

    except KeyboardInterrupt:
        print("Main process interrupted. Terminating child processes.")
        for p in processes:
            p.terminate()
            p.join()

if __name__ == "__main__":
    base_config, server_config = load_config()
    llm_server_process = server_config.start_llm_server()
    atexit.register(server_config.terminate_llm_server, llm_server_process)

    def signal_handler(signum, frame):
        server_config.terminate_llm_server(llm_server_process)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Give the server some time to start
    time.sleep(10)  # Consider using wait_for_server_ready here instead to ensure the server is ready
    main_loop()