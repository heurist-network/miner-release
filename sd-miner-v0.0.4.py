import time
import torch
import sys
from itertools import cycle
import os
import logging
from multiprocessing import Process, set_start_method
import signal
import threading

from mining_core.base import BaseConfig, ModelUpdater
from mining_core.utils import (
    check_cuda, get_hardware_description,
    fetch_and_download_config_files, get_local_model_ids,
    post_request, log_response, submit_job_result
)

class MinerConfig(BaseConfig):
    def __init__(self, config_file, cuda_device_id=0):
        super().__init__(config_file, cuda_device_id)
        
        if self.num_cuda_devices > 1:
            for i in range(self.num_cuda_devices):
                miner_id = self.config['general'].get(f'miner_id_{i}', None)
                if miner_id is None:
                    print(f"miner_id_{i} not found in config. Exiting...")
                    sys.exit(1)
            self.miner_id = self.config['general'][f'miner_id_{cuda_device_id}']
        else:
            self.miner_id = self.config['general'].get('miner_id', self.config['general']['miner_id_0'])
            if self.miner_id is None:
                print("miner_id not found in config. Exiting...")
                sys.exit(1)

def load_config(filename='config.toml', cuda_device_id=0):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, filename)
    return MinerConfig(config_path, cuda_device_id)

def send_miner_request(config, model_ids, min_deadline, current_model_id):
    request_data = {
        "miner_id": config.miner_id,
        "model_ids": model_ids,
        "min_deadline": min_deadline,
        "current_model_id": current_model_id
    }
    if time.time() - config.last_heartbeat >= 60:
        request_data['hardware'] = get_hardware_description(config)
        config.last_heartbeat = time.time()
    response = post_request(config.base_url + "/miner_request", request_data, config.miner_id)
    return log_response(response, config.miner_id)

def main(cuda_device_id):
    torch.cuda.set_device(cuda_device_id)
    config = load_config(cuda_device_id=cuda_device_id)
    print(config.__dict__)
    
    # The parent process should have already downloaded the model files
    # Now we just need to load them into memory
    fetch_and_download_config_files(config)

    # Configure unique logging for each process
    process_log_filename = f"{config.log_filename.split('.')[0]}_{cuda_device_id}.log"
    logging.basicConfig(filename=process_log_filename, filemode='a', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    
    executed = False
    while True:
        try:
            current_model_id = next(iter(config.loaded_models)) if config.loaded_models else None
            model_ids = get_local_model_ids(config)
            if len(model_ids) == 0:
                logging.info("No models found. Exiting...")
                exit(0)
                
            job = send_miner_request(config, model_ids, config.min_deadline, current_model_id)

            if job is not None:
                logging.info(f"Processing job {job['job_id']}...")
                submit_job_result(config, config.miner_id, job, job['temp_credentials'])
                executed = True
            else:
                logging.info("No job received.")
                executed = False
        except Exception as e:
            logging.error(f"Error occurred: {e}")
            import traceback
            traceback.print_exc()
            
        if not executed:
            time.sleep(2)
            
if __name__ == "__main__":
    processes = []
    def signal_handler(signum, frame):
        for p in processes:
            p.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    set_start_method('spawn', force=True)
    
    config = load_config()

    if config.num_cuda_devices > torch.cuda.device_count():
        print("Number of CUDA devices specified in config is greater than available. Exiting...")
        sys.exit(1)
    check_cuda()

    fetch_and_download_config_files(config)

    # Initialize and start model updater before processing tasks
    model_updater = ModelUpdater(config=config.__dict__)  # Assuming config.__dict__ provides necessary settings

    # Start the model updater in a separate thread
    updater_thread = threading.Thread(target=model_updater.start_scheduled_updates)
    updater_thread.start()
    
    # TODO: There appear to be 1 leaked semaphore objects to clean up at shutdown
    # Launch a separate process for each CUDA device
    try:
        for i in range(config.num_cuda_devices):
            p = Process(target=main, args=(i,))
            p.start()
            processes.append(p)

        for p in processes:
            p.join()

    except KeyboardInterrupt:
        print("Main process interrupted. Terminating child processes.")
        for p in processes:
            p.terminate()
            p.join()