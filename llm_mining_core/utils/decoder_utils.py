import re
import json

def decode_prompt_json(prompt_json):
    try:
        return json.loads(prompt_json)
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode prompt JSON: {e}")
        return None