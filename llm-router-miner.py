import requests
import sys
import itertools
import time
import os
from collections import defaultdict
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

# TODO: Dockerize this application. reference: https://chat.openai.com/share/4041b4b0-ba95-4c36-981f-953be652fd53
# print environment variables
print("Environment variables:")
print(f"TEXT_MODEL_ID: {os.getenv('TEXT_MODEL_ID', None)}")

text_model_id = os.getenv('TEXT_MODEL_ID', None)

# miner_id = os.getenv('MINER_ID', None)
miner_ids = [id.strip() for id in os.getenv('MINER_IDS', '').split(',')]
print("Miner IDs:", miner_ids)
miner_ids_cycle = itertools.cycle(miner_ids)  # Create an iterator that cycles through the miner IDs

base_url = os.getenv('BASE_URL', None)
api_key = os.getenv('OPENAI_API_KEY', None)
openai_base_url = os.getenv('OPENAI_BASE_URL', None)

last_heartbeat = time.time() - 10000
# Initialize a dictionary to track the last heartbeat for each miner_id
last_heartbeat_per_miner = defaultdict(lambda: 0)

eos = "[DONE]"

if text_model_id is None or base_url is None or api_key is None or openai_base_url is None:
    print("One or more environment variables are not set.")
    sys.exit(1)

client = OpenAI(api_key=api_key, base_url=openai_base_url)

# A set of stop words to use - this is not a complete set, and you may want to
# add more given your observation.
stop_words = [
    "<|im_end|>",
    "[End]",
    "[end]",
    "\nReferences:\n",
    "\nSources:\n",
    "End.",
]

def get_hardware_description():
    return "NVIDIA RTX A6000"

def decode_prompt(encoded_prompt):
    # Markers for the start and end of instructions, and end of assistant message
    inst_start = "[INST]"
    inst_end = "[/INST]"
    assistant_end = "</s>"
    
    # Split the encoded prompt into segments based on the start marker
    segments = encoded_prompt.split(inst_start)
    
    messages = []
    for segment in segments[1:]:  # Start from 1 to skip the initial empty segment before the first [INST]
        if inst_end in segment:
            # Find the end of the instruction segment
            end_index = segment.find(inst_end)
            
            # Extract the user prompt
            user_prompt = segment[:end_index].strip()
            # Everything after the instruction end marker
            following_content = segment[end_index + len(inst_end):].strip()
            
            # Check if the assistant message ends with the </s> marker and remove it
            if assistant_end in following_content:
                assistant_message_end_index = following_content.find(assistant_end)
                assistant_message = following_content[:assistant_message_end_index].strip()
            else:
                assistant_message = following_content
            
            # Add the user prompt to the messages list
            messages.append({"role": "user", "content": user_prompt})
            
            # If there's an assistant message, add it to the messages list
            if assistant_message:
                messages.append({"role": "assistant", "content": assistant_message})
    
    return messages

def generate(miner_id, job_id, prompt, temperature, max_tokens, seed, stop, use_stream_flag):
    print(f"Processing job {job_id} for miner {miner_id}...")

    # Prepare headers for submitting results back to the server
    headers = {
        'job_id': str(job_id),
        'miner_id': str(miner_id),
        'Content-Type': 'application/json'  # Use 'text/event-stream' if streaming
    }

    if use_stream_flag:
        print("Streaming mode enabled")
        stream = client.chat.completions.create(
            messages=decode_prompt(prompt),
            model=text_model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop,
            seed=seed,
            stream=True,
        )

        def generate_data(stream):
            for chunk in stream:
                if chunk.choices[0].delta is not None:
                    yield chunk.choices[0].delta
                    if any(word in chunk.choices[0].delta for word in stop):
                        print("Received stop word from server. Exiting...")
                        yield eos
                        break
            yield eos  # Ensure EOS is sent when the stream ends

        # Stream the data to the server
        with requests.Session() as session:
            response = session.post(
                f"{base_url}/miner_submit_stream", 
                headers=headers, 
                data=generate_data(stream), 
                stream=True
            )
            response.raise_for_status()
    else:
        print("Non-streaming mode")
        # Non-streaming logic
        response = client.chat.completions.create(
            messages=[
                {"role": "user", "content": prompt}
            ],
            model=text_model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop,
            seed=seed
        )
        res = response.choices[0].message.content
        # if the words is in stop_words, truncate the result
        for word in stop:
            if word in res:
                res = res[:res.index(word)]
                break
        url = base_url + "/miner_submit"
        result = {
            "miner_id": miner_id,
            "job_id": job_id,
            "result": {"Text": res},
        }
        response = requests.post(url, json=result)
        print(f"Response from server for {miner_id}: {response.text}")

def send_miner_request(miner_id):
    global last_heartbeat_per_miner
    url = base_url + "/miner_request"
    request_data = {
        "miner_id": miner_id,
        "model_ids": [text_model_id],
        "min_deadline": 1,
        "current_model_id": text_model_id
    }

    # Check and update the last heartbeat time for the specific miner_id
    current_time = time.time()
    if current_time - last_heartbeat_per_miner[miner_id] >= 60:
        request_data['hardware'] = get_hardware_description()  # Assume this function is defined elsewhere
        last_heartbeat_per_miner[miner_id] = current_time

    response = requests.post(url, json=request_data)
    print(f"Response from server for miner {miner_id}: {response.text}")
    try:
        data = response.json()
        if isinstance(data, dict):
            return data
        else:
            return None
    except Exception as e:
        print(f"Error parsing response: {e}")
        return None

def main_loop():
    while True:
        miner_id = next(miner_ids_cycle)  # Get the next miner ID in a round-robin manner
        try:
            job = send_miner_request(miner_id)
            if job is not None:
                print(f"Processing job {job['job_id']} for miner {miner_id}...")
                prompt = job['model_input']['LLM']['prompt']
                temperature = job['model_input']['LLM']['temperature']
                max_tokens = job['model_input']['LLM']['max_tokens']
                seed = job['model_input']['LLM']['seed']
                use_stream = job['model_input']['LLM']['use_stream']
                if seed == -1:  # Handling for seed if specified as -1
                    seed = None
                stop = stop_words  # Assuming stop_words are defined earlier in the script
                
                # Process the job with the miner
                generate(miner_id, job['job_id'], prompt, temperature, max_tokens, seed, stop, use_stream)
            else:
                print(f"No job received for miner {miner_id}. Waiting for the next round...")
        except Exception as e:
            print(f"Error occurred for miner {miner_id}: {e}")
            # Implement your error handling logic here. For example, logging the error, retry mechanisms, etc.
            
        time.sleep(2)  # Adjust the sleep time as needed to manage job processing rate and server load

if __name__ == "__main__":
    main_loop()
