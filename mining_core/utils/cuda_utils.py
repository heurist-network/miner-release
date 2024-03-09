import torch
import logging
import sys

def get_hardware_description(config):
    return torch.cuda.get_device_name(config.cuda_device_id)

def check_cuda():
    if not torch.cuda.is_available():
        logging.error("CUDA is not available. Exiting...")
        sys.exit(1)

    num_devices = torch.cuda.device_count()
    if num_devices == 0:
        logging.error("No CUDA devices found. Exiting...")
        sys.exit(1)

    # This is more informational, suitable for an info level since it's not an everyday debugging message.
    logging.info(f"Found {num_devices} CUDA device(s).")
    for i in range(num_devices):
        logging.info(f"Device {i}: {torch.cuda.get_device_name(i)}")

    logging.info("CUDA is ready...")