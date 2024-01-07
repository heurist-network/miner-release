import requests
import time
import torch
import io
import boto3
import sys
import gc
import os
import logging
import toml
from tqdm import tqdm
from diffusers import StableDiffusionPipeline, AutoencoderKL, DPMSolverMultistepScheduler

if not torch.cuda.is_available():
    print("CUDA is not available. Exiting...")
    sys.exit(1)

config = toml.load('config.toml')

base_url = config['general']['base_url']
miner_id = config['general']['miner_id']
s3_bucket = config['general']['s3_bucket']
model_config_url = config['general']['model_config_url']
vae_config_url = config['general']['vae_config_url']
base_dir = os.path.expanduser(config['general']['base_dir'])
os.makedirs(base_dir, exist_ok=True)

logging.basicConfig(filename=config['general']['log_filename'], filemode='w', format='%(name)s - %(levelname)s - %(message)s')

min_deadline = int(config['general']['min_deadline'])

loaded_models = {}  # key: model_id, value: model pipeline
model_configs = {}  # key: model_id, value: model config
vae_configs = {}    # key: vae_id, value: vae config

def download_file(file_url, file_name, total_size):
    try:
        response = requests.get(file_url, stream=True)
        file_path = os.path.join(base_dir, file_name)
        with open(file_path, 'wb') as f, tqdm(
            total=total_size, unit='B', unit_scale=True, desc=file_name) as bar:
            for data in response.iter_content(chunk_size=1024):
                size = f.write(data)
                bar.update(size)
    except requests.exceptions.ConnectionError as ce:
        logging.error(f"Failed to connect to server: {ce}")

def fetch_and_download_config_files():
    global model_configs, vae_configs
    try:
        models = requests.get(model_config_url).json()
        vaes = requests.get(vae_config_url).json()
        model_configs = {model['name']: model for model in models}
        vae_configs = {vae['name']: vae for vae in vaes}
        total_size = 0
        files_to_download = []

        for model in models:
            file_path = os.path.join(base_dir, model['name'] + ".safetensors")
            if not os.path.exists(file_path):
                size_mb = model['size_mb']
                total_size += size_mb
                files_to_download.append(model)
            vae_name = model.get('vae', None)
            if vae_name is not None:
                vae_path = os.path.join(base_dir, model['vae'] + ".safetensors")
                if not os.path.exists(vae_path):
                    vae_config = next((vae for vae in vaes if vae['name'] == vae_name), None)
                    if vae_config is not None:
                        size_mb = vae_config['size_mb']
                        total_size += size_mb
                        files_to_download.append(vae_config)
                    else:
                        logging.error(f"VAE config for {vae_name} not found.")

        if len(files_to_download) == 0:
            print("All model files are up to date.")
            return
        total_size_gb = total_size / 1024
        print(f"Need to download {len(files_to_download)} files, total size: {total_size_gb:.2f} GB")
        confirm = input("Do you want to proceed with the download? (yes/no): ")

        if confirm.lower() == 'yes':
            for i, model in enumerate(files_to_download, 1):
                print(f"Downloading file {i}/{len(files_to_download)}")
                download_file(model['file_url'], model['name'] + ".safetensors", model['size_mb'] * 1024 * 1024)
    except requests.exceptions.ConnectionError as ce:
        logging.error(f"Failed to connect to server: {ce}")
            
def get_local_model_ids():
    global model_configs, base_dir
    local_files = os.listdir(base_dir)
    return [model['name'] for model in model_configs.values() if model['name'] + ".safetensors" in local_files]

def load_model(model_id):
    global model_configs, base_dir
    model_config = model_configs.get(model_id, None)
    if model_config is None:
        raise Exception(f"Model configuration for {model_id} not found.")

    model_file_path = os.path.join(base_dir, f"{model_id}.safetensors")

    # Load the main model
    pipe = StableDiffusionPipeline.from_single_file(model_file_path, torch_dtype=torch.float16).to('cuda')
    pipe.safety_checker = None
    # TODO: Add support for other schedulers
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, use_karras_sigmas=True, algorithm_type="sde-dpmsolver++")

    if 'vae' in model_config:
        vae_name = model_config['vae']
        vae_file_path = os.path.join(base_dir, f"{vae_name}.safetensors")
        vae = AutoencoderKL.from_single_file(vae_file_path, torch_dtype=torch.float16).to("cuda")
        pipe.vae = vae

    return pipe


def unload_model(model_id):
    global loaded_models
    if model_id in loaded_models:
        del loaded_models[model_id]
        torch.cuda.empty_cache()
        gc.collect()

def send_miner_request(model_ids, min_deadline, current_model_id):
    url = base_url + "/miner_request"
    request_data = {
        "miner_id": miner_id,
        "model_ids": model_ids,
        "min_deadline": min_deadline,
        "current_model_id": current_model_id
    }
    try:
        response = requests.post(url, json=request_data)
        print(f"Response from server: {response.text}")
        try:
            data = response.json()
            if isinstance(data, dict):
                return data
            else:
                return None
        except ValueError as ve:
            logging.error(f"Failed to parse JSON response: {ve}")
            return None
    except requests.exceptions.RequestException as re:
        logging.error(f"Request failed: {re}")
        return None

def submit_job_result(job, temp_credentials):
    url = base_url + "/miner_submit"
    
    # Create an S3 client with the temporary credentials
    s3 = boto3.client('s3', 
                      aws_access_key_id=temp_credentials[0], 
                      aws_secret_access_key=temp_credentials[1], 
                      aws_session_token=temp_credentials[2])

    image_data = execute_model(job['model_id'], job['model_input']['SD']['prompt'], job['model_input']['SD']['neg_prompt'], job['model_input']['SD']['height'], job['model_input']['SD']['width'], job['model_input']['SD']['num_iterations'], job['model_input']['SD']['guidance_scale'], job['model_input']['SD']['seed'])

    # Upload the image to S3
    s3_key = f"{job['job_id']}.png"
    s3.put_object(Body=image_data.getvalue(), Bucket=s3_bucket, Key=s3_key)

    result = {
        "miner_id": miner_id,
        "job_id": job['job_id'],
        "result_type": {"S3Key": s3_key},
        "result": s3_key
    }
    response = requests.post(url, json=result)
    print(f"Response from server: {response.text}")

def execute_model(model_id, prompt, neg_prompt, height, width, num_iterations, guidance_scale, seed):
    global loaded_models, model_configs
    current_model = loaded_models.get(model_id, None)
    model_config = model_configs.get(model_id, {})

    if current_model is None:
        # Unload current model if exists
        if len(loaded_models) > 0:
            unload_model(next(iter(loaded_models)))

        print(f"Loading model {model_id}...")
        current_model = load_model(model_id)
        loaded_models[model_id] = current_model

    kwargs = {
        'height': height,
        'width': width,
        'num_inference_steps': num_iterations,
        'guidance_scale': guidance_scale,
        'negative_prompt': neg_prompt
    }

    if 'clip_skip' in model_config:
        kwargs['clip_skip'] = model_config['clip_skip']

    if seed is not None and seed >= 0:
        kwargs['generator'] = torch.Generator().manual_seed(seed)

    images = current_model(prompt, **kwargs).images

    image_data = io.BytesIO()
    images[0].save(image_data, format='PNG')
    image_data.seek(0)

    return image_data

if __name__ == "__main__":
    fetch_and_download_config_files()

    while True:
        try:
            current_model_id = next(iter(loaded_models)) if loaded_models else None
            model_ids = get_local_model_ids()
            if len(model_ids) == 0:
                print("No models found. Exiting...")
                exit(0)
                
            job = send_miner_request(model_ids, min_deadline, current_model_id)

            if job is not None:
                print(f"Processing job {job['job_id']}...")
                submit_job_result(job, job['temp_credentials'])
            else:
                print("No job received.")
        except Exception as e:
            print(f"Error occurred: {e}")
            import traceback
            traceback.print_exc()
            
        time.sleep(2)
