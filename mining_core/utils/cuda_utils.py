import torch
import sys

def get_hardware_description(config):
    return torch.cuda.get_device_name(config.cuda_device_id)

def check_cuda():
    if not torch.cuda.is_available():
        print("CUDA is not available. Exiting...")
        sys.exit(1)
    num_devices = torch.cuda.device_count()
    if num_devices == 0:
        print("No CUDA devices found. Exiting...")
        sys.exit(1)
    print(f"Found {num_devices} CUDA device(s).")
    for i in range(num_devices):
        print(f"Device {i}: {torch.cuda.get_device_name(i)}")

    print("CUDA is ready...")