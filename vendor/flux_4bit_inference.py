"""
This file is adapted from 'flux-4bit' by Wu Hecong.
Original source: https://github.com/HighCWu/flux-4bit
License: MIT
For more information, please see the original repository.
"""
import torch
import os
from .flux_t5_quantization import T5EncoderModel, FluxTransformer2DModel
from diffusers import FluxPipeline

def load_flux_model(config, device="cuda"):
    text_encoder_2 = T5EncoderModel.from_pretrained(
        "HighCWu/FLUX.1-dev-4bit",
        subfolder="text_encoder_2",
        torch_dtype=torch.bfloat16,
    ).to(device)

    transformer = FluxTransformer2DModel.from_pretrained(
        "HighCWu/FLUX.1-dev-4bit",
        subfolder="transformer",
        torch_dtype=torch.bfloat16,
    ).to(device)
   
    base_model_path = os.path.join(config.base_dir, "FLUX.1-dev" )

    pipe = FluxPipeline.from_pretrained(
        base_model_path,
        text_encoder_2=text_encoder_2,
        transformer=transformer,
        torch_dtype=torch.bfloat16,
    )
    pipe.remove_all_hooks()
    pipe = pipe.to(device)

    return pipe