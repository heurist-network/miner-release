import torch


def get_hardware_description():
    """
    Returns a description of the hardware being used, specifically focusing on the GPU.
    Currently, it returns the name of the first CUDA device found by PyTorch. If CUDA is not
    available or if there's a need to handle other hardware types, this function should be expanded.

    Returns:
        str: A string describing the hardware, or a message indicating no CUDA devices were found.
    """
    if torch.cuda.is_available():
        return torch.cuda.get_device_name(0)  # Assumes the first CUDA device if multiple are present
    else:
        return "No CUDA devices found. Ensure you have a compatible NVIDIA GPU with the correct drivers installed."