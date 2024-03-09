import os
import torch
import io
from diffusers import StableDiffusionPipeline, StableDiffusionXLPipeline, AutoencoderKL, DPMSolverMultistepScheduler
import gc
import logging
import time

def get_local_model_ids(config):
    local_files = os.listdir(config.base_dir)
    local_model_ids = [model['name'] for model in config.model_configs.values() if model['name'] + ".safetensors" in local_files]
    return local_model_ids

def load_model(config, model_id):
    start_time = time.time()  # Start measuring time
    model_config = config.model_configs.get(model_id, None)
    if model_config is None:
        raise Exception(f"Model configuration for {model_id} not found.")

    model_file_path = os.path.join(config.base_dir, f"{model_id}.safetensors")

    # Load the main model
    if model_config['type'] == "sd15":
        pipe = StableDiffusionPipeline.from_single_file(model_file_path, torch_dtype=torch.float16).to('cuda:' + str(config.cuda_device_id))
        pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, use_karras_sigmas=True, algorithm_type="sde-dpmsolver++")
    else:
        pipe = StableDiffusionXLPipeline.from_single_file(model_file_path, torch_dtype=torch.float16, variant="fp16").to('cuda:' + str(config.cuda_device_id))
    pipe.safety_checker = None
    # TODO: Add support for other schedulers

    if 'vae' in model_config:
        vae_name = model_config['vae']
        vae_file_path = os.path.join(config.base_dir, f"{vae_name}.safetensors")
        vae = AutoencoderKL.from_single_file(vae_file_path, torch_dtype=torch.float16).to('cuda:' + str(config.cuda_device_id))
        pipe.vae = vae
    
    end_time = time.time()  # End measuring time
    # Calculate and log the loading latency
    loading_latency = end_time - start_time

    return pipe, loading_latency

def unload_model(config, model_id):
    if model_id in config.loaded_models:
        del config.loaded_models[model_id]
        torch.cuda.empty_cache()
        gc.collect()

def execute_model(config, model_id, prompt, neg_prompt, height, width, num_iterations, guidance_scale, seed):
    try:
        current_model = config.loaded_models.get(model_id, None)
        model_config = config.model_configs.get(model_id, {})
        loading_latency = None  # Indicates no loading occurred if the model was already loaded

        if current_model is None:
            # Check if there are any models to unload
            if config.loaded_models:
                # Unload the first model in the list
                model_to_unload = next(iter(config.loaded_models))
                unload_model(config, model_to_unload)
                logging.debug(f"Unloaded model {model_to_unload} to make space for {model_id}")

            logging.info(f"Loading model {model_id}...")
            current_model, loading_latency = load_model(config, model_id)
            config.loaded_models[model_id] = current_model

        kwargs = {
            'height': min(height - height % 8, config.config['general']['max_height']),
            'width': min(width - width % 8, config.config['general']['max_width']),
            'num_inference_steps': min(num_iterations, config.config['general']['max_iterations']),
            'guidance_scale': guidance_scale,
            'negative_prompt': neg_prompt,
            'add_watermarker': False
        }

        if 'clip_skip' in model_config:
            kwargs['clip_skip'] = model_config['clip_skip']

        if seed is not None and seed >= 0:
            kwargs['generator'] = torch.Generator().manual_seed(seed)

        logging.debug(f"Executing model {model_id} with parameters: {kwargs}")

        # Start measuring inference time
        inference_start_time = time.time()

        images = current_model(prompt, **kwargs).images

        # End measuring inference time
        inference_end_time = time.time()

        # Calculate and log the inference latency
        inference_latency = inference_end_time - inference_start_time

        image_data = io.BytesIO()
        images[0].save(image_data, format='PNG')
        image_data.seek(0)

        return image_data, inference_latency, loading_latency
    
    except Exception as e:
        logging.error(f"Error executing model {model_id}: {e}")
        raise