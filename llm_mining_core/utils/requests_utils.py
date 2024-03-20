import time
import requests
from .cuda_utils import get_hardware_description

DEFAULT_MINER_ID = "default_miner_id"

def send_miner_request(config, miner_id):
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
        "model_ids": config.SUPPORTED_MODEL_IDS,
        "min_deadline": 1,
        "current_model_id": None
    }

    # Check and update the last heartbeat time for the specific miner_id
    current_time = time.time()
    if current_time - config.last_heartbeat_per_miner[miner_id] >= 60:
        request_data['hardware'] = get_hardware_description()
        config.last_heartbeat_per_miner[miner_id] = current_time

    response = requests.post(url, json=request_data)
    try:
        data = response.json()
        end_time = time.time()
        request_latency = end_time - current_time
        if isinstance(data, dict):
            return data, request_latency
        else:
            return None, None
    except Exception as e:
        print(f"Error parsing response: {e}")
        return None, None