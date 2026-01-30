import json
import torch
from fastapi import APIRouter, HTTPException

from app.api.v2.llm_schemas import LLMRequest, LLMResponse
import app.services.llm_provider as llm_provider

router = APIRouter(prefix="/llm", tags=["llm"])


@router.post("/generate", response_model=LLMResponse)
def generate(req: LLMRequest):
    try:
        llm_provider.load_model()

        tokenizer = llm_provider.tokenizer
        model = llm_provider.model
        device = llm_provider.device

        inputs = tokenizer(
            req.prompt,
            return_tensors="pt"
        ).to(device)

        with torch.no_grad():
            output = model.generate(
                **inputs,
                max_new_tokens=req.max_tokens,
                temperature=req.temperature,
                top_p=req.top_p,
                do_sample=req.temperature > 0,
                repetition_penalty=1.1,
                eos_token_id=tokenizer.eos_token_id,
            )

        text = tokenizer.decode(
            output[0][inputs["input_ids"].shape[-1]:],
            skip_special_tokens=True
        ).strip()

        parsed = None
        if not req.raw:
            try:
                parsed = json.loads(text)
            except Exception:
                pass

        return LLMResponse(text=text, parsed=parsed)

    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            torch.cuda.empty_cache()
        raise HTTPException(status_code=500, detail=str(e))
