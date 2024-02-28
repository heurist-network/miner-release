import os
from tqdm import tqdm
import requests
import logging
import json
import argparse

def download_file(base_dir, file_url, file_name, total_size):
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

def fetch_and_download_config_files(config):
    try:
        models = requests.get(config.model_config_url).json()
        vaes = requests.get(config.vae_config_url).json()
        config.model_configs = {model['name']: model for model in models}
        config.vae_configs = {vae['name']: vae for vae in vaes}
        total_size = 0
        files_to_download = []

        for model in models:
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
            print("All model files are up to date.")
            return
        total_size_gb = total_size / 1024

        # Create the parser
        parser = argparse.ArgumentParser(description="Download files")
        # Add the arguments
        parser.add_argument('-y', '--yes', action='store_true', help="Automatically proceed with the download")
        # Parse the arguments
        args = parser.parse_args()

        print(f"Need to download {len(files_to_download)} files, total size: {total_size_gb:.2f} GB")
        
        if args.yes:
            confirm = 'yes'
        else:
            confirm = input("Do you want to proceed with the download? (yes/no): ")

        if confirm.strip().lower() in ['yes', 'y']:
            for i, model in enumerate(files_to_download, 1):
                print(f"Downloading file {i}/{len(files_to_download)}")
                download_file(config.base_dir, model['file_url'], model['name'] + ".safetensors", model['size_mb'] * 1024 * 1024)
    except requests.exceptions.ConnectionError as ce:
        logging.error(f"Failed to connect to server: {ce}")