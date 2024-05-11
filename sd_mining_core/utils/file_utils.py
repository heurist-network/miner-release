import os
import logging
import requests
from tqdm import tqdm
from itertools import chain

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
    except requests.exceptions.ConnectionError as ce:
        logging.error(f"Failed to connect to server: {ce}")
    except Exception as e:
        logging.error(f"Error downloading file {file_name}: {e}")

def fetch_and_download_config_files(config):
    try:
        models = requests.get(config.model_config_url).json()
        vaes = requests.get(config.vae_config_url).json()
        loras = requests.get(config.lora_config_url).json()

        config.model_configs = {
            model['name']: model for model in models
            if 'type' in model and (
                'sd' in model['type'] or model['type'].startswith('composite')
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
            if 'type' not in model or (model['type'] not in ['sd15', 'sdxl10', 'vae', 'lora']):
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

        for i, model in enumerate(files_to_download, 1):
            print(f"Downloading file {i}/{len(files_to_download)}")
            download_file(config.base_dir, model['file_url'], model['name'] + ".safetensors")
            
    except requests.exceptions.ConnectionError as ce:
        logging.error(f"Failed to connect to server: {ce}")
    except Exception as e:
        logging.error(f"Error fetching and downloading config files: {e}")