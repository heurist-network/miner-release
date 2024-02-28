import requests
import logging
import time
import boto3
from .model_utils import execute_model

def post_request(url, data, miner_id=None):
    try:
        response = requests.post(url, json=data)
        # Directly return the response object
        return response
    except ValueError as ve:
        miner_id_info = f" for miner_id {miner_id}" if miner_id else ""
        logging.error(f"Failed to parse JSON response{miner_id_info}: {ve}")
    except requests.exceptions.RequestException as re:
        miner_id_info = f" for miner_id {miner_id}" if miner_id else ""
        logging.error(f"Request failed{miner_id_info}: {re}")
    return None

def log_response(response, miner_id=None):
    miner_id_info = f" for miner_id {miner_id}" if miner_id else ""
    if response:
        logging.info(f"Response from server{miner_id_info}: {response.text}")
        try:
            data = response.json()
            if isinstance(data, dict):
                return data
            else:
                return None
        except ValueError as ve:
            logging.error(f"Failed to parse JSON response{miner_id_info}: {ve}")
    return None


def submit_job_result(config, miner_id, job, temp_credentials):
    url = config.base_url + "/miner_submit"
    
    # Create an S3 client with the temporary credentials
    s3 = boto3.client('s3', 
                      aws_access_key_id=temp_credentials[0], 
                      aws_secret_access_key=temp_credentials[1], 
                      aws_session_token=temp_credentials[2])

    image_data = execute_model(config, job['model_id'], job['model_input']['SD']['prompt'], job['model_input']['SD']['neg_prompt'], job['model_input']['SD']['height'], job['model_input']['SD']['width'], job['model_input']['SD']['num_iterations'], job['model_input']['SD']['guidance_scale'], job['model_input']['SD']['seed'])

    # Upload the image to S3
    s3_key = f"{job['job_id']}.png"
    s3.put_object(Body=image_data.getvalue(), Bucket=config.s3_bucket, Key=s3_key)

    result = {
        "miner_id": miner_id,  # Use the provided miner_id for the submission
        "job_id": job['job_id'],
        "result": {"S3Key": s3_key},
    }
    response = requests.post(url, json=result)
    logging.info(f"miner_submit response from server for {miner_id}: {response.text}")
