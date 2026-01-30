import json
import torch
import asyncio
from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from app.api.v2.llm_schemas import LLMRequest, LLMResponse
import app.services.llm_provider as llm_provider

router = APIRouter(prefix="/llm", tags=["llm"])


def _generate_sync(req: LLMRequest) -> LLMResponse:
    tokenizer = llm_provider.tokenizer
    model = llm_provider.model
    device = llm_provider.device

    inputs = tokenizer(
        req.prompt,
        return_tensors="pt"
    ).to(device)

    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=min(req.max_tokens, 256),
            temperature=req.temperature,
            top_p=req.top_p,
            do_sample=req.temperature > 0,
            repetition_penalty=1.1,
            eos_token_id=tokenizer.eos_token_id,
        )

    generated = output[0][inputs["input_ids"].shape[-1]:]
    text = tokenizer.decode(generated, skip_special_tokens=True).strip()

    parsed = None
    if not req.raw:
        try:
            parsed = json.loads(text)
        except Exception:
            pass

    return LLMResponse(text=text, parsed=parsed)


@router.post("/generate", response_model=LLMResponse)
async def generate(req: LLMRequest):
    try:
        llm_provider.load_model()

        # 👇 КЛЮЧЕВОЕ МЕСТО
        return await run_in_threadpool(_generate_sync, req)

    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            torch.cuda.empty_cache()
        raise HTTPException(status_code=500, detail=str(e))
