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
    print("Downloading flux-dev model")
    print("Original file_url:", original_file_url)

    local_dir = os.path.join(base_dir, "FLUX.1-dev")
    os.makedirs(local_dir, exist_ok=True)
    print("local_dir:", local_dir)

    for file in flux_dev_file_downloads:
        try:
            file_url = original_file_url + file  # Reset file_url for each file
            local_file_path = os.path.join(local_dir, file)
            print(f"Attempting to download: {file}")
            print("local_file_path:", local_file_path)
            local_file_dir = os.path.dirname(local_file_path)
            
            os.makedirs(local_file_dir, exist_ok=True)
            
            download_flux_dev_file(file_url, local_file_path)
            print(f"Successfully downloaded: {file}")
        except Exception as e:
            print(f"Error downloading {file}: {str(e)}")

    print("Finished downloading flux-dev model files")


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

def fetch_and_download_config_files(config):
    print("config.flux_dev_file_downloads",config.flux_dev_file_downloads)
    try:
        # Fetch configurations
        models = requests.get(config.model_config_url, timeout=30).json()
        vaes = requests.get(config.vae_config_url, timeout=30).json()
        loras = requests.get(config.lora_config_url, timeout=30).json()


        config.model_configs = {
            model['name']: model for model in models
            if 'type' in model and (
                'sd' in model['type'] or 
                model['type'].startswith('composite') or
                model['type'] == 'flux-dev-4bit'
            ) and (not config.exclude_sdxl or not model['type'].startswith('sdxl'))
        }

        config.vae_configs = {
            vae['name']: vae
            for vae in vaes
        }

        config.lora_configs = { 
            lora['name']: lora
            for lora in loras 
        }

        total_size = 0
        files_to_download = []
        for model in chain(config.model_configs.values(), config.lora_configs.values()):
            if 'type' not in model or (model['type'] not in ['sd15', 'sdxl10', 'vae', 'lora', 'flux-dev-4bit']):
                continue
            if not 'size_mb' in model:
                print(f"Warning: Model {model['name']} does not have a size_mb field. models.json is misconfgured. Skipping.")
                continue
            file_path = os.path.join(config.base_dir, model['name'] + ".safetensors")
            if not os.path.exists(file_path):
                size_mb = model['size_mb']
                total_size += size_mb
                files_to_download.append(model)
            vae_name = model.get('vae', None)
            if vae_name is not None:
                vae_path = os.path.join(config.base_dir, model['vae'] + ".safetensors")
                if not os.path.exists(vae_path):
                    vae_config = next((vae for vae in vaes if vae['name'] == vae_name), None)
                    if vae_config is not None:
                        size_mb = vae_config['size_mb']
                        total_size += size_mb
                        files_to_download.append(vae_config)
                    else:
                        logging.error(f"VAE config for {vae_name} not found.")

        if len(files_to_download) == 0:
            print("All model files are up to date. Miner is ready.")
            return
        
        total_size_gb = total_size / 1024
        print(f"Need to download {len(files_to_download)} files, total size: {total_size_gb:.2f} GB")

        confirm = 'yes' if config.auto_confirm else input("Do you want to proceed with the download? (yes/no): ")
        if confirm.strip().lower() not in ['yes', 'y']:
            print("Download canceled.")
            return
        print("files_to_download: ",files_to_download)
        for i, model in enumerate(files_to_download, 1):
            print("i,model: ",i,model)
            if model["name"] != "FLUX.1-dev-4bit":
                print(f"Downloading file {i}/{len(files_to_download)}")
                download_file(config.base_dir, model['file_url'], model['name'] + ".safetensors")
            else: 
                print(f"downloading flux dev 4bit: {len(config.flux_dev_file_downloads)} files")
                download_flux_dev(config.base_dir, model['file_url'],config.flux_dev_file_downloads)
            
    except requests.exceptions.ConnectionError as ce:
        logging.error(f"Failed to connect to server: {ce}")
    except Exception as e:
        logging.error(f"Error fetching and downloading config files: {e}")
