import os
import requests
import logging
import time
import boto3
from .model_utils import execute_model

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
            pass
    else:
        logging.warning(f"No response received{miner_id_info}")
    return None

def upload_image_to_s3(s3_client, image_data, bucket, key):
    """Uploads the generated image to S3."""
    try:
        s3_client.put_object(Body=image_data.getvalue(), Bucket=bucket, Key=key)
        logging.debug(f"Image uploaded to S3 bucket {bucket} with key {key}.")
    except Exception as e:
        logging.error(f"Failed to upload image to S3: {e}")

def execute_inference_and_upload(config, miner_id, job, temp_credentials):
    """Executes model inference and uploads the result to S3, returning inference time."""
    s3 = boto3.client('s3', 
                      aws_access_key_id=temp_credentials[0], 
                      aws_secret_access_key=temp_credentials[1], 
                      aws_session_token=temp_credentials[2])

    image_data, inference_latency, loading_latency = execute_model(config, job['model_id'], job['model_input']['SD']['prompt'], job['model_input']['SD']['neg_prompt'], job['model_input']['SD']['height'], job['model_input']['SD']['width'], job['model_input']['SD']['num_iterations'], job['model_input']['SD']['guidance_scale'], job['model_input']['SD']['seed'])
    
    s3_key = f"{job['job_id']}-{miner_id}.png"
    start_time = time.time() 
    upload_image_to_s3(s3, image_data, config.s3_bucket, s3_key)
    end_time = time.time()
    upload_latency = end_time - start_time

    return s3_key, inference_latency, loading_latency, upload_latency

def submit_job_result(config, miner_id, job, temp_credentials, job_start_time, request_latency):
    """Submits the job result after processing and logs the total and inference times."""
    s3_key, inference_latency, loading_latency, upload_latency = execute_inference_and_upload(config, miner_id, job, temp_credentials)
    # Construct result payload with latency data
    result = {
        "miner_id": miner_id.lower(),
        "job_id": job['job_id'],
        "result": {
            "S3Key": s3_key,
        },
        "request_latency": request_latency,
        "loading_latency": loading_latency,
        "inference_latency": inference_latency,
        "upload_latency": upload_latency,
    }
    if not config.skip_signature:
        identity_address, signature = config.wallet_generator.generate_signature(miner_id)
        result["signature"] = signature
        result["identity_address"] = identity_address
    try:
        start_time = time.time()  # Start measuring time for miner_submit call
        response = requests.post(config.base_url + "/miner_submit", json=result)
        response.raise_for_status()
        end_time = time.time()  # End measuring time

        submit_latency = end_time - start_time

        job_end_time = time.time()
        total_time = job_end_time - job_start_time
        if total_time > config.sd_timeout_seconds:
            print("Warning: the previous request timed out. You will not earn points. Please check miner configuration or network connection.")
        
        # Log job completion
        logging.info(f"Request ID {job['job_id']} completed. Total time: {total_time:.2f} s")
        
        # Log latencies
        latency_descriptions = [
            f"Request: {request_latency:.3f} s",
            f"Loading: {loading_latency:.3f} s" if loading_latency is not None else "Loading: N/A",
            f"Inference: {inference_latency:.3f} s",
            f"Upload: {upload_latency:.3f} s",
            f"Submit: {submit_latency:.3f} s"
        ]

        # Join the latency descriptions with commas and prepend the label
        latencies_log = "Latencies - " + ", ".join(latency_descriptions)

        # Log the compiled message
        logging.info(latencies_log)
        
    except requests.exceptions.RequestException as err:
        logging.error(f"Error occurred during job submission: {err}")


