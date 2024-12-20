import os
import logging
import requests
from tqdm import tqdm
from itertools import chain
import json


def download_flux_dev_file(url, local_path):
    if os.path.exists(local_path):
        print(f"File already exists: {local_path}. Skipping download.")
        return

    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(local_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    print(f"Downloaded: {url} -> {local_path}")

def download_flux_dev(base_dir, original_file_url, flux_dev_file_downloads):
    local_dir = os.path.join(base_dir, "FLUX.1-dev")
    os.makedirs(local_dir, exist_ok=True)

    for file in flux_dev_file_downloads:
        try:
            file_url = original_file_url + file  # Reset file_url for each file
            local_file_path = os.path.join(local_dir, file)
            local_file_dir = os.path.dirname(local_file_path)
            os.makedirs(local_file_dir, exist_ok=True)
            download_flux_dev_file(file_url, local_file_path)
        except Exception as e:
            print(f"Error downloading {file}: {str(e)}")

def download_file(base_dir, file_url, file_name):
    try:
        response = requests.get(file_url, stream=True)
        total_size = int(response.headers.get('Content-Length', 0))
        
        file_path = os.path.join(base_dir, file_name)
        with open(file_path, 'wb') as f, tqdm(
            desc=file_name,
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            downloaded_size = 0
            for data in response.iter_content(chunk_size=1024):
                size = f.write(data)
                downloaded_size += size
                bar.update(size)
            
            if total_size != 0 and downloaded_size != total_size:
                print(f"Warning: Downloaded size ({downloaded_size}) does not match expected size ({total_size}) for {file_name}")
        
        logging.info(f"Successfully downloaded {file_name}")
    except requests.exceptions.RequestException as re:
        logging.error(f"Network error downloading {file_name}: {re}")
    except IOError as ioe:
        logging.error(f"I/O error writing file {file_name}: {ioe}")
    except Exception as e:
        logging.error(f"Unexpected error downloading {file_name}: {e}")

def check_flux_dev_files(base_dir, flux_dev_file_downloads):
    flux_dir = os.path.join(base_dir, "FLUX.1-dev")
    for file in flux_dev_file_downloads:
        file_path = os.path.join(flux_dir, file)
        if not os.path.exists(file_path):
            return False
    return True

def fetch_and_download_config_files(config):
    try:
        # Fetch configurations
        models = requests.get(config.model_config_url, timeout=30).json()
        vaes = requests.get(config.vae_config_url, timeout=30).json()
        loras = requests.get(config.lora_config_url, timeout=30).json()

        # If a specific model_id is provided, filter the configurations
        if config.specified_model_id:
            specified_model = next((model for model in models if model['name'] == config.specified_model_id), None)
            if specified_model:
                config.model_configs = {config.specified_model_id: specified_model}
                
                # If it's a composite model, include its base model as well
                if specified_model.get('type') in ['composite15', 'compositexl']:
                    base_model_id = specified_model.get('base')
                    base_model = next((model for model in models if model['name'] == base_model_id), None)
                    if base_model:
                        config.model_configs[base_model_id] = base_model
                    else:
                        logging.warning(f"Base model '{base_model_id}' for composite model '{config.specified_model_id}' not found.")
                
                # Include the corresponding LoRA if it exists
                lora = next((lora for lora in loras if lora['name'] == config.specified_model_id), None)
                if lora:
                    config.lora_configs = {config.specified_model_id: lora}
            else:
                # Check if it's a LoRA
                lora = next((lora for lora in loras if lora['name'] == config.specified_model_id), None)
                if lora:
                    config.lora_configs = {config.specified_model_id: lora}
                    # Include the base model for this LoRA
                    base_model_id = lora.get('base')
                    base_model = next((model for model in models if model['name'] == base_model_id), None)
                    if base_model:
                        config.model_configs = {base_model_id: base_model}
                    else:
                        logging.warning(f"Base model '{base_model_id}' for LoRA '{config.specified_model_id}' not found.")
                else:
                    raise ValueError(f"Specified model ID '{config.specified_model_id}' not found in model or LoRA configurations.")
        else:
            # Original logic for handling all models
            config.model_configs = {
                model['name']: model for model in models
                if 'type' in model and (
                    'sd' in model['type'] or 
                    model['type'].startswith('composite')
                ) and (not config.exclude_sdxl or 'xl' not in model['type'])
            }
            config.lora_configs = { 
                lora['name']: lora for lora in loras 
            }

        config.vae_configs = {
            vae['name']: vae for vae in vaes
        }

        total_size = 0
        files_to_download = []
        
        def process_model(model):
            nonlocal total_size, files_to_download
            if 'type' not in model or (model['type'] not in ['sd15', 'sdxl10', 'vae', 'lora', 'flux-dev', 'composite15', 'compositexl']):
                return
            
            if model['type'] in ['composite15', 'compositexl']:
                # Handle composite models
                base_model = config.model_configs.get(model['base'])
                if base_model:
                    process_model(base_model)  # Process the base model
                else:
                    logging.warning(f"Base model '{model['base']}' for composite model '{model['name']}' not found.")
                
                # Process the LoRA part
                lora = config.lora_configs.get(model['name'])
                if lora:
                    process_model(lora)
                else:
                    logging.warning(f"LoRA part for composite model {model['name']} not found.")
                return

            if 'size_mb' not in model:
                logging.warning(f"Model {model['name']} does not have a size_mb field. models.json is misconfigured. Skipping.")
                return
            
            if model['type'] == 'flux-dev':
                if not check_flux_dev_files(config.base_dir, config.flux_dev_file_downloads):
                    if not any(m['name'] == model['name'] for m in files_to_download):
                        total_size += model['size_mb']
                        files_to_download.append(model)
            else:
                file_path = os.path.join(config.base_dir, model['name'] + ".safetensors")
                if not os.path.exists(file_path):
                    if not any(m['name'] == model['name'] for m in files_to_download):
                        total_size += model['size_mb']
                        files_to_download.append(model)
            
            # Check for associated VAE
            vae_name = model.get('vae')
            if vae_name:
                vae_path = os.path.join(config.base_dir, vae_name + ".safetensors")
                if not os.path.exists(vae_path):
                    vae_config = config.vae_configs.get(vae_name)
                    if vae_config:
                        if not any(m['name'] == vae_name for m in files_to_download):
                            total_size += vae_config['size_mb']
                            files_to_download.append(vae_config)
                    else:
                        logging.error(f"VAE config for {vae_name} not found.")

        # Process models based on whether a specific model_id is provided
        if config.specified_model_id:
            model = config.model_configs.get(config.specified_model_id) or config.lora_configs.get(config.specified_model_id)
            if model:
                process_model(model)
            else:
                raise ValueError(f"Specified model ID '{config.specified_model_id}' not found in configurations.")
        else:
            for model in chain(config.model_configs.values(), config.lora_configs.values()):
                process_model(model)

        if len(files_to_download) == 0:
            print("All required model files are up to date. Miner is ready.")
            return
        
        total_size_gb = total_size / 1024
        print(f"Need to download {len(files_to_download)} files, total size: {total_size_gb:.2f} GB")

        confirm = 'yes' if config.auto_confirm else input("Do you want to proceed with the download? (yes/no): ")
        if confirm.strip().lower() not in ['yes', 'y']:
            print("Download canceled.")
            return

        for i, model in enumerate(files_to_download, 1):
            if model["name"] != "FLUX.1-dev":
                print(f"Downloading file {i}/{len(files_to_download)}")
                download_file(config.base_dir, model['file_url'], model['name'] + ".safetensors")
            else: 
                print(f"downloading flux dev 4bit: {len(config.flux_dev_file_downloads)} files")
                download_flux_dev(config.base_dir, model['file_url'], config.flux_dev_file_downloads)
            
    except requests.exceptions.ConnectionError as ce:
        logging.error(f"Failed to connect to server: {ce}")
    except Exception as e:
        logging.error(f"Error fetching and downloading config files: {e}")
