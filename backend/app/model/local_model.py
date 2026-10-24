import asyncio
import threading
from typing import Any

from ..config import settings


class ModelNotReadyError(RuntimeError):
    """Raised when local model inference is requested before a successful load."""


class LocalLanguageModel:
    """One in-process Transformers model used for constrained local generation."""

    def __init__(self, model_id: str | None = None, device: str | None = None) -> None:
        self.model_id = model_id or settings.model_id
        self.device = device or settings.model_device
        self._model: Any = None
        self._tokenizer: Any = None
        self._generation_lock = threading.Lock()

    @property
    def ready(self) -> bool:
        return self._model is not None and self._tokenizer is not None

    async def load(self) -> None:
        await asyncio.to_thread(self._load_sync)

    def _load_sync(self) -> None:
        if self.ready:
            return
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as error:
            raise RuntimeError("Install backend requirements to load the local language model.") from error

        tokenizer = AutoTokenizer.from_pretrained(self.model_id, trust_remote_code=False)
        load_options: dict[str, Any] = {"torch_dtype": "auto", "low_cpu_mem_usage": True}
        if self.device == "auto":
            load_options["device_map"] = "auto"
        model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            trust_remote_code=False,
            **load_options,
        )
        if self.device != "auto":
            model.to(self.device)
        model.eval()
        self._tokenizer = tokenizer
        self._model = model

    async def generate(self, messages: list[dict[str, str]], max_new_tokens: int | None = None) -> str:
        if not self.ready:
            raise ModelNotReadyError("The local language model is not ready.")
        bounded_messages = [
            {"role": str(message["role"]), "content": str(message["content"])[:8000]}
            for message in messages
            if message.get("role") in {"system", "user", "assistant"}
        ]
        token_limit = min(max_new_tokens or settings.model_max_output_tokens, settings.model_max_output_tokens)
        return await asyncio.to_thread(self._generate_sync, bounded_messages, token_limit)

    def _generate_sync(self, messages: list[dict[str, str]], max_new_tokens: int) -> str:
        import torch

        with self._generation_lock, torch.inference_mode():
            encoded = self._tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_tensors="pt",
                return_dict=True,
            )
            input_ids = encoded["input_ids"]
            if input_ids.shape[-1] > settings.model_max_input_tokens:
                raise ValueError("Model prompt is longer than the configured input token limit.")
            encoded = encoded.to(self._model.device)
            output = self._model.generate(
                **encoded,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                pad_token_id=self._tokenizer.eos_token_id,
            )
            generated = output[0][input_ids.shape[-1]:]
            return self._tokenizer.decode(generated, skip_special_tokens=True).strip()
