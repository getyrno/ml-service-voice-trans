import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import Optional

MODEL_NAME = "Qwen/Qwen2.5-3B-Instruct"

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float16,
    device_map=None
).to("cuda")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
device = "cuda"


def load_model():
    global tokenizer, model, device

    if model is not None:
        return

    if torch.cuda.is_available():
        device = "cuda"
        dtype = torch.float16
    else:
        device = "cpu"
        dtype = torch.float32

    print(f"[LLM] loading {MODEL_NAME} on {device}")

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        trust_remote_code=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=dtype,
        device_map="auto",
        trust_remote_code=True,
    )

    model.eval()
    print("[LLM] model loaded")
