"""Persistent, offline MedGemma subprocess. JSON lines are the only stdout protocol."""
import json
import os
import sys
import time
from pathlib import Path

from medgemma_generation_guard import (LIMIT_CODE, MAX_NEW_TOKENS,
                                        repeated_text_block, repeated_token_block)

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

MODEL_ID = "google/medgemma-1.5-4b-it"
REVISION = "91850547d9f0b2fdd21aa7c5f4f3d1a8a52c243b"
SNAPSHOT = Path(r"D:\MedNexus\Cache\MedGemma\models--google--medgemma-1.5-4b-it\snapshots") / REVISION
INSTRUCTION = ("Extract the clinically important findings, pertinent negatives, measurements, "
               "diagnostic considerations, and follow-up recommendations from this radiology "
               "report. Do not infer information that is not explicitly stated in the report.")


def emit(payload):
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def main():
    if not SNAPSHOT.is_dir():
        emit({"protocol": 1, "kind": "ERROR", "code": "MODEL_UNAVAILABLE",
              "failure_stage": "MODEL_LOAD", "exception_type": "FileNotFoundError",
              "exception_message": "Pinned local model snapshot is unavailable"})
        return 2
    emit({"protocol": 1, "kind": "PHASE", "phase": "MODEL_LOAD_STARTED"})
    try:
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor, StoppingCriteria
        if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
            raise RuntimeError("CUDA BF16 unavailable")
        processor = AutoProcessor.from_pretrained(
            str(SNAPSHOT), local_files_only=True, trust_remote_code=False)
        model = AutoModelForImageTextToText.from_pretrained(
            str(SNAPSHOT), torch_dtype=torch.bfloat16, device_map="auto",
            local_files_only=True, trust_remote_code=False, use_safetensors=True,
            low_cpu_mem_usage=True)
        model.eval()
    except Exception as exc:
        emit({"protocol": 1, "kind": "ERROR", "code": "MODEL_LOAD_FAILED",
              "failure_stage": "MODEL_LOAD", "exception_type": type(exc).__name__,
              "exception_message": str(exc)})
        return 2
    emit({"protocol": 1, "kind": "READY", "model_id": MODEL_ID, "model_revision": REVISION})

    class RepetitionGuard(StoppingCriteria):
        def __init__(self, prompt_tokens):
            self.prompt_tokens = prompt_tokens
            self.repetition_detected = False

        def __call__(self, input_ids, scores, **kwargs):
            generated_count = input_ids.shape[-1] - self.prompt_tokens
            if generated_count >= 24 and generated_count % 4 == 0:
                self.repetition_detected = repeated_token_block(input_ids[0, self.prompt_tokens:].tolist())
            return torch.full((input_ids.shape[0],), self.repetition_detected,
                              dtype=torch.bool, device=input_ids.device)

    for line in sys.stdin:
        failure_stage = "INPUT_PREPARATION"
        try:
            request = json.loads(line)
            if request.get("protocol") != 1 or not isinstance(request.get("protected_text"), str):
                raise ValueError("Invalid request")
            text = request["protected_text"]
            if not text or len(text) > 20000:
                raise ValueError("Protected input outside pilot size limit")
            prompt = INSTRUCTION + "\n\n" + text
            messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
            inputs = processor.apply_chat_template(
                messages, add_generation_prompt=True, tokenize=True,
                return_dict=True, return_tensors="pt")
            if any("pixel" in key or "image" in key for key in inputs):
                raise ValueError("Image inputs are not allowed")
            input_tokens = int(inputs["input_ids"].shape[-1])
            inputs = inputs.to(model.device, dtype=torch.bfloat16)
            torch.cuda.reset_peak_memory_stats(0)
            start = time.perf_counter()
            failure_stage = "INFERENCE"
            emit({"protocol": 1, "kind": "PHASE", "phase": "INFERENCE_STARTED"})
            repetition_guard = RepetitionGuard(input_tokens)
            with torch.inference_mode():
                generated = model.generate(
                    **inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False,
                    repetition_penalty=1.3, no_repeat_ngram_size=4,
                    stopping_criteria=[repetition_guard])
            torch.cuda.synchronize(0)
            emit({"protocol": 1, "kind": "PHASE", "phase": "GENERATION_COMPLETED"})
            failure_stage = "RESPONSE_DECODE"
            output_ids = generated[0][input_tokens:]
            raw_response = processor.decode(output_ids, skip_special_tokens=True)
            output_tokens = int(output_ids.numel())
            token_limit_reached = output_tokens >= MAX_NEW_TOKENS
            repetition_detected = repetition_guard.repetition_detected or repeated_text_block(raw_response)
            emit({"protocol": 1, "kind": "RESULT",
                  "raw_response": raw_response,
                  "input_tokens": input_tokens, "output_tokens": output_tokens,
                  "token_limit_reached": token_limit_reached,
                  "repetition_detected": repetition_detected,
                  "natural_stop_before_limit": not token_limit_reached and not repetition_guard.repetition_detected,
                  "code": LIMIT_CODE if token_limit_reached or repetition_detected else None,
                  "latency_seconds": round(time.perf_counter() - start, 3),
                  "peak_gpu_memory_bytes": torch.cuda.max_memory_allocated(0)})
        except Exception as exc:
            emit({"protocol": 1, "kind": "ERROR",
                  "code": "CUDA_OUT_OF_MEMORY" if type(exc).__name__ == "OutOfMemoryError" else "INFERENCE_FAILED",
                  "failure_stage": failure_stage,
                  "exception_type": type(exc).__name__, "exception_message": str(exc)})
            if type(exc).__name__ == "OutOfMemoryError":
                return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
