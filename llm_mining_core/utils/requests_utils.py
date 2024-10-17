import time
import psutil
import logging
import requests
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
from .cuda_utils import get_hardware_description

DEFAULT_MINER_ID = "default_miner_id"

def check_vllm_server_status():
    """
    Checks if the vLLM server process is currently running.
    This function iterates over the running processes and checks if any process
    matches the criteria for the vLLM server process. It looks for a process
    with 'python' as the first argument, '-m' as one of the arguments, and
    'vllm.entrypoints.openai.api_server' as another argument.
    Returns:
        bool: True if the vLLM server process is running, False otherwise.
    """
    for proc in psutil.process_iter(['pid', 'cmdline']):
        cmdline = proc.info['cmdline']
        if cmdline and 'python' in cmdline[0] and '-m' in cmdline and 'vllm.entrypoints.openai.api_server' in cmdline:
            return True
    return False

def send_miner_request(config, miner_id, model_id):
    """
    Sends a request for a new mining job to the server using the given configuration.

    Parameters:
        config (BaseConfig): The configuration instance containing necessary settings.
        miner_id (str): The ID of the miner requesting a job.

    Returns:
        dict or None: The job details as a dictionary if available, otherwise None.
    """
    url = f"{config.base_url}/miner_request"
    if miner_id is None:
        miner_id = DEFAULT_MINER_ID

    request_data = {
        "miner_id": miner_id,
        "model_id": model_id,
        "min_deadline": 1
    }

    # Check and update the last heartbeat time for the specific miner_id
    current_time = time.time()
    if current_time - config.last_heartbeat_per_miner[miner_id] >= 60:
        request_data['hardware'] = get_hardware_description()
        request_data['version'] = config.version
        config.last_heartbeat_per_miner[miner_id] = current_time

    try:
        response = config.session.post(url, json=request_data)
        # Assuming response.text contains the full text response from the server
        warning_indicator = "Warning:"
        if response and warning_indicator in response.text:
            # Extract the warning message and use strip() to remove any trailing quotation marks
            warning_message = response.text.split(warning_indicator)[1].strip('"')
            print(f"WARNING: {warning_message}")
            return None, None

        try:
            data = response.json()
            end_time = time.time()
            request_latency = end_time - current_time
            if isinstance(data, dict):
                return data, request_latency
            else:
                return None, None
        except Exception as e:
            # fail silently
            # print(f"Error parsing response: {e}")
            return None, None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending request: {e}")
        return None, None
    
def get_metric_value(metric_name, base_config):
    """
    Fetches the value of a specific metric from the llm endpoint.

    Args:
        metric_name (str): The name of the metric to fetch.
        base_config (BaseConfig): The base configuration object.

    Returns:
        float or None: The value of the metric if found, None otherwise.
    """
    try:
        url = f"{base_config.llm_url}:{base_config.port}/metrics"
        #Call the metrics endpoint to get the metric value
        response = requests.get(url)
        response_text = response.text
        lines = response_text.split('\n')
        for line in lines:
            if line.startswith(f"vllm:{metric_name}"):
                parts = line.split(' ')
                if len(parts) >= 2:
                    value = float(parts[1])
                    return value
    except Exception as e:
        # fail silently
        logging.error(f"Error occurred while finding metric value: {str(e)}")
        return None
    return None

def send_model_info_signal(config, miner_id, last_signal_time):
    """
    Parameters:
    - base_config (dict): A dictionary containing the configuration settings for the
                           periodic signal, including the signal interval.
    - miner_id (str): The unique identifier for the miner sending the signal.
    - last_signal_time (float): The timestamp of the last signal sent, used to calculate the
                                 next signal time.
    """
    current_time = time.time()
    # Only proceed if it's been at least signal_interval in seconds
    if current_time - last_signal_time >= config.signal_interval:
        response = post_request(config, config.signal_url + "/miner_signal", {
            "miner_id": miner_id,
            "model_type": "LLM",
            "version": config.version, # format is like "llm-v1.2.0"
            "model_id": config.served_model_name
        }, miner_id)

        # Process the response only if it's valid
        if response and response.status_code == 200:
            last_signal_time = current_time
        else:
            logging.error(f"Failed to get a valid response from /miner_signal for miner_id {miner_id}.")
        
    return last_signal_time if current_time - last_signal_time < config.signal_interval else current_time

def post_request(config, url, data, miner_id=None):
    try:
        response = config.session.post(url, json=data)
        logging.debug(f"Request sent to {url} with data {data} received response: {response.status_code}")
        # Directly return the response object
        return response
    except ValueError as ve:
        miner_id_info = f" for miner_id {miner_id}" if miner_id else ""
        logging.error(f"Failed to parse JSON response{miner_id_info}: {ve}")
    except requests.exceptions.RequestException as re:
        miner_id_info = f" for miner_id {miner_id}" if miner_id else ""
        logging.error(f"Request failed{miner_id_info}: {re}")
    return None
