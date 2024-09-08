"""
This file is adapted from 'flux-4bit' by Wu Hecong.
Original source: https://github.com/HighCWu/flux-4bit
License: MIT
For more information, please see the original repository.
"""
import os
import copy
import torch
import torch.nn as nn
import diffusers.utils.constants
import transformers.utils, transformers.modeling_utils

from contextlib import contextmanager
from hqq.core.quantize import HQQLinear
from huggingface_hub import hf_hub_download
from diffusers import FluxTransformer2DModel as OriginalFluxTransformer2DModel
from diffusers.configuration_utils import FrozenDict
from huggingface_hub import hf_hub_download
from huggingface_hub.utils import validate_hf_hub_args
from safetensors.torch import load_file
from transformers import T5Config, T5EncoderModel as OriginalT5EncoderModel
from transformers.configuration_utils import PretrainedConfig
from transformers.modeling_utils import PreTrainedModel

from typing import Optional, Union, Dict, List, Any


@contextmanager
def switch_weight_name():
    transformers.modeling_utils.WEIGHTS_NAME = diffusers.utils.constants.WEIGHTS_NAME
    transformers.modeling_utils.WEIGHTS_INDEX_NAME = diffusers.utils.constants.WEIGHTS_INDEX_NAME
    transformers.modeling_utils.SAFE_WEIGHTS_NAME = diffusers.utils.constants.SAFETENSORS_WEIGHTS_NAME
    transformers.modeling_utils.SAFE_WEIGHTS_INDEX_NAME = diffusers.utils.constants.SAFE_WEIGHTS_INDEX_NAME
    yield
    transformers.modeling_utils.WEIGHTS_NAME = transformers.utils.WEIGHTS_NAME
    transformers.modeling_utils.WEIGHTS_INDEX_NAME = transformers.utils.WEIGHTS_INDEX_NAME
    transformers.modeling_utils.SAFE_WEIGHTS_NAME = transformers.utils.SAFE_WEIGHTS_NAME
    transformers.modeling_utils.SAFE_WEIGHTS_INDEX_NAME = transformers.utils.SAFE_WEIGHTS_INDEX_NAME


def patch_transformers_quantizer_bnb_4bit():
    from transformers.quantizers.quantizer_bnb_4bit import Bnb4BitHfQuantizer, Conv1D, get_module_from_name

    def create_quantized_param(
        self,
        model: "PreTrainedModel",
        param_value: "torch.Tensor",
        param_name: str,
        target_device: "torch.device",
        state_dict: Dict[str, Any],
        unexpected_keys: Optional[List[str]] = None,
    ):
        """
        combines logic from _load_state_dict_into_meta_model and .integrations.bitsandbytes.py::set_module_quantized_tensor_to_device()
        """
        import bitsandbytes as bnb

        module, tensor_name = get_module_from_name(model, param_name)

        if tensor_name not in module._parameters:
            raise ValueError(f"{module} does not have a parameter or a buffer named {tensor_name}.")

        old_value = getattr(module, tensor_name)

        if tensor_name == "bias":
            if param_value is None:
                new_value = old_value.to(target_device)
            else:
                new_value = param_value.to(target_device)

            new_value = torch.nn.Parameter(new_value, requires_grad=old_value.requires_grad)
            module._parameters[tensor_name] = new_value
            return

        if not isinstance(module._parameters[tensor_name], bnb.nn.Params4bit):
            raise ValueError("this function only loads `Linear4bit components`")
        if (
            old_value.device == torch.device("meta")
            and target_device not in ["meta", torch.device("meta")]
            and param_value is None
        ):
            raise ValueError(f"{tensor_name} is on the meta device, we need a `value` to put in on {target_device}.")

        # construct `new_value` for the module._parameters[tensor_name]:
        if self.pre_quantized:
            # 4bit loading. Collecting components for restoring quantized weight
            # This can be expanded to make a universal call for any quantized weight loading

            if not self.is_serializable:
                raise ValueError(
                    "Detected int4 weights but the version of bitsandbytes is not compatible with int4 serialization. "
                    "Make sure to download the latest `bitsandbytes` version. `pip install --upgrade bitsandbytes`."
                )

            if (param_name + ".quant_state.bitsandbytes__fp4" not in state_dict) and (
                param_name + ".quant_state.bitsandbytes__nf4" not in state_dict
            ):
                raise ValueError(
                    f"Supplied state dict for {param_name} does not contain `bitsandbytes__*` and possibly other `quantized_stats` components."
                )

            quantized_stats = {}
            for k, v in state_dict.items():
                if k.startswith(param_name + "."):
                    quantized_stats[k] = v
                    if unexpected_keys is not None and k in unexpected_keys:
                        unexpected_keys.remove(k)

            new_value = bnb.nn.Params4bit.from_prequantized(
                data=param_value,
                quantized_stats=quantized_stats,
                requires_grad=False,
                device=target_device,
            )
        else:
            new_value = param_value.to("cpu")

            # Support models using `Conv1D` in place of `nn.Linear` (e.g. openai-community/gpt2) by transposing the weight matrix prior to quantization.
            # Since weights are saved in the correct "orientation", we skip transposing when loading.
            if issubclass(module.source_cls, Conv1D):
                new_value = new_value.T

            kwargs = old_value.__dict__
            new_value = bnb.nn.Params4bit(new_value, requires_grad=False, **kwargs).to(target_device)

        module._parameters[tensor_name] = new_value

    Bnb4BitHfQuantizer.create_quantized_param = create_quantized_param


class T5EncoderModel(OriginalT5EncoderModel):
    _torch_dtype = torch.float32
    _hqq_4bit_compute_dtype = torch.float32

    def to(self, *args, **kwargs):
        super().to(*args, **kwargs)
        for arg in args:
            if isinstance(arg, torch.dtype):
                self._torch_dtype = arg
                break
        for k, v in kwargs.items():
            if k == "device" and isinstance(v, torch.dtype):
                self._torch_dtype = v
                break
        return self

    @property
    def dtype(self) -> torch.dtype:
        return self._torch_dtype
    
    @property
    def hqq_4bit_compute_dtype(self) -> torch.dtype:
        return self._hqq_4bit_compute_dtype
    
    @hqq_4bit_compute_dtype.setter
    def hqq_4bit_compute_dtype(self, value: torch.dtype):
        for module in self.modules():
            if isinstance(module, HQQLinear):
                module.compute_dtype = value
                module.meta["compute_dtype"] = value
        self._hqq_4bit_compute_dtype = value
    
    def state_dict(self, *args, **kwargs):
        global _in_state_dict_fn
        in_state_dict_fn = _in_state_dict_fn
        _in_state_dict_fn = True
        result = super().state_dict(*args, **kwargs)
        _in_state_dict_fn = in_state_dict_fn
        return result
    
    @classmethod
    def from_pretrained(
        cls,
        pretrained_model_name_or_path: Optional[Union[str, os.PathLike]],
        *model_args,
        hqq_4bit_compute_dtype: Optional[torch.dtype] = None,
        **kwargs_ori,
    ) -> "T5EncoderModel":
        kwargs = copy.deepcopy(kwargs_ori)
        cache_dir = kwargs.pop("cache_dir", None)
        subfolder = kwargs.pop("subfolder", None)
        torch_dtype = kwargs.pop("torch_dtype", T5EncoderModel._torch_dtype)
        if hqq_4bit_compute_dtype is None:
            hqq_4bit_compute_dtype = torch_dtype
        model_config: Dict[str, Any] = T5Config.from_pretrained(
            pretrained_model_name_or_path,
            subfolder=subfolder,
            cache_dir=cache_dir,
            **kwargs
        )
        quant_config: Dict[str, Any] = getattr(model_config, "quantization_config", { "quant_method": None })
        is_hqq_quant = quant_config.pop("quant_method") == "hqq"
        if not is_hqq_quant:
            return super(T5EncoderModel, cls).from_pretrained(
                pretrained_model_name_or_path, *model_args, **kwargs_ori
            )
        if hasattr(model_config, "quantization_config"):
            delattr(model_config, "quantization_config")
        with torch.device("meta"):
            model = T5EncoderModel._from_config(
                config=model_config,
                torch_dtype=torch_dtype,
            )
        model._torch_dtype = torch_dtype
        model._hqq_4bit_compute_dtype = hqq_4bit_compute_dtype

        modules = { name: module for name, module in model.named_modules() }
        parameters = { name: param for name, param in model.named_parameters() }
        for name, param in parameters.items():
            parent_name, param_name = '.'.join(name.split('.')[:-1]), name.split('.')[-1]
            module = modules[parent_name]
            if not isinstance(module, nn.Linear):
                dtype = param.dtype
                if 'float' in repr(dtype):
                    dtype = torch_dtype
                param = torch.empty_like(param, dtype=dtype, device="cuda")
                setattr(module, param_name, nn.Parameter(param))
        # model.quantization_method = "hqq" # not to set it, then we can use `.to(device)` in cpu_offload
        for name, module in modules.items():
            if isinstance(module, nn.Linear):
                parent_name, linear_name = ".".join(name.split(".")[:-1]), name.split(".")[-1]
                hqq_layer = HQQLinear(
                    None, #torch.nn.Linear or None 
                    quant_config=quant_config, #quantization configuration
                    compute_dtype=hqq_4bit_compute_dtype, #compute dtype
                    device="cuda", #cuda device
                    initialize=True, #Use False to quantize later
                    del_orig=True, #if True, delete the original layer
                )
                hqq_layer.weight = torch.empty(1,1,dtype=torch_dtype,device='cuda') # Placeholder
                del module.weight
                del module.bias

                if parent_name == "":
                    parent_module = model
                else:
                    parent_module = modules[parent_name]
                setattr(parent_module, linear_name, hqq_layer)
        weight_path = pretrained_model_name_or_path
        if subfolder is not None:
            weight_path += '/' + subfolder
        weight_name = kwargs.pop("weight_name", "model.safetensors")
        weight_path += '/' + weight_name
        if not os.path.exists(weight_path):
            weight_path = hf_hub_download(
                pretrained_model_name_or_path,
                weight_name,
                subfolder=subfolder,
                cache_dir=cache_dir)
        model_state_dict = load_file(
            weight_path,
            device="cuda"
        )

        def make_cast_forward(self):
            forward_ori = self.forward
            def forward(x):
                return forward_ori(x.to(model._hqq_4bit_compute_dtype)).type_as(x)
            self.forward = forward
            return self
        
        model.load_state_dict(model_state_dict, strict=False)
        for name, module in model.named_modules():
            if isinstance(module, HQQLinear):
                state_dict = { k.split(name + ".")[-1]: v for k, v in model_state_dict.items() if k.startswith(name + ".")}
                module.load_state_dict(state_dict)
                make_cast_forward(module)
                module.compute_dtype = hqq_4bit_compute_dtype
                module.meta["compute_dtype"] = hqq_4bit_compute_dtype
                
                del state_dict
        del model_state_dict
        torch.cuda.empty_cache()

        return model


class FluxConfig(PretrainedConfig):
    def __init__(
        self, 
        patch_size: int = 1,
        in_channels: int = 64,
        num_layers: int = 19,
        num_single_layers: int = 38,
        attention_head_dim: int = 128,
        num_attention_heads: int = 24,
        joint_attention_dim: int = 4096,
        pooled_projection_dim: int = 768,
        guidance_embeds: bool = False,
        axes_dims_rope: List[int] = [16, 56, 56],
        **kwargs,
    ):
        self.patch_size = patch_size
        self.in_channels = in_channels
        self.num_layers = num_layers
        self.num_single_layers = num_single_layers
        self.attention_head_dim = attention_head_dim
        self.num_attention_heads = num_attention_heads
        self.joint_attention_dim = joint_attention_dim
        self.pooled_projection_dim = pooled_projection_dim
        self.guidance_embeds = guidance_embeds
        self.axes_dims_rope = axes_dims_rope

        super().__init__(**kwargs)


class FluxTransformer2DPretrainedModel(PreTrainedModel):
    config_class = FluxConfig
    base_model_prefix = "model"

    def __init__(self, config: FluxConfig):
        super().__init__(config)

        patch_size = config.patch_size
        in_channels = config.in_channels
        num_layers = config.num_layers
        num_single_layers = config.num_single_layers
        attention_head_dim = config.attention_head_dim
        num_attention_heads = config.num_attention_heads
        joint_attention_dim = config.joint_attention_dim
        pooled_projection_dim = config.pooled_projection_dim
        guidance_embeds = config.guidance_embeds
        axes_dims_rope = config.axes_dims_rope
        self.model = FluxTransformer2DModel(
            patch_size = patch_size,
            in_channels = in_channels,
            num_layers = num_layers,
            num_single_layers = num_single_layers,
            attention_head_dim = attention_head_dim,
            num_attention_heads = num_attention_heads,
            joint_attention_dim = joint_attention_dim,
            pooled_projection_dim = pooled_projection_dim,
            guidance_embeds = guidance_embeds,
            axes_dims_rope = axes_dims_rope,
        )


class FluxTransformer2DModel(OriginalFluxTransformer2DModel):
    _cached_wrappers: List[FluxTransformer2DPretrainedModel] = []

    @property
    def to_transformers_format(self):
        return self._cached_wrappers[-1]

    @classmethod
    @validate_hf_hub_args
    def from_pretrained(cls, pretrained_model_name_or_path: Optional[Union[str, os.PathLike]], **kwargs):
        with switch_weight_name():
            model_wrapper: FluxTransformer2DPretrainedModel = FluxTransformer2DPretrainedModel.from_pretrained(
                pretrained_model_name_or_path, **kwargs
            )
        model = model_wrapper.model
        model._cached_wrappers += [model_wrapper]
        return model

    def save_pretrained(
        self,
        save_directory: Union[str, os.PathLike],
        **kwargs,
    ):
        model_wrapper = self._cached_wrappers[-1]
        original_config = self._internal_dict
        config = model_wrapper.config.to_dict()
        self._internal_dict = FrozenDict(config)
        super().save_pretrained(save_directory, **kwargs)
        self._internal_dict = original_config


patch_transformers_quantizer_bnb_4bit()