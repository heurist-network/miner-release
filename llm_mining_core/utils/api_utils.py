import os
from openai import OpenAI

def initialize_client(config, model_id):
    """
    Initializes and returns an API client based on the provided model ID. This function
    dynamically selects the appropriate API key based on the service endpoint associated
    with the model ID.

    Args:
        model_id (str): The model ID for which to initialize the API client.

    Returns:
        OpenAI: An initialized OpenAI client configured for the specific model's API, or
        None if the API key is not set or if the model ID is not recognized.
    """
    api_base_url = config.MODEL_TO_API_BASE_URL.get(model_id, None)
    if api_base_url is None:
        print(f"API base URL not found for model ID: {model_id}")
        return None

    return OpenAI(base_url=api_base_url, api_key="N/A")