from fastapi import FastAPI, Body, Request
from llama_cpp import Llama
import json
from pathlib import Path

app = FastAPI(title="Edge Logging Firewall")

# Resolve model path dynamically relative to project root
MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "llama-3.2-1b-instruct.Q4_K_M.gguf"

# Load the GGUF model into memory on startup
print(f"Loading Llama 3.2 Edge Firewall onto CPU from {MODEL_PATH}...")
llm = Llama(
    model_path=str(MODEL_PATH),
    n_ctx=4096,          # INCREASED: Allows users to paste huge paragraphs/stack traces up to 4K tokens
    n_gpu_layers=0,      # 0 means pure CPU execution
    chat_format="chatml" # Matches your Unsloth training template
)

# CRITICAL: DO NOT REMOVE THIS. This is the exact "trigger key" the LoRA model was trained on.
# If you remove or change this, the model will hallucinate and fail to output JSON.
SYSTEM_PROMPT = "You are an Edge Logging Firewall. Analyze backend production logs, ignore irrelevant noise, redact sensitive PII, and output ONLY valid JSON matching the telemetry schema."

# Accept plain text directly so Swagger UI renders a large raw text box for pasting paragraphs
@app.post("/distill_logs")
async def analyze_logs(raw_log: str = Body(..., media_type="text/plain", description="Paste your raw logs or paragraphs directly here.")):
    
    # Format the payload exactly like the training data layout
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": raw_log}
    ]
    
    # Run CPU inference with strict determinism
    response = llm.create_chat_completion(
        messages=messages,
        max_tokens=1024,     # INCREASED: Prevents the JSON output from truncating mid-sentence
        temperature=0.0      # REDUCED: 0.0 guarantees absolute determinism for strict JSON formats
    )
    
    model_output = response["choices"][0]["message"]["content"].strip()
    
    try:
        # Convert string output to formal JSON dictionary response
        return json.loads(model_output)
    except json.JSONDecodeError:
        return {"status": "error", "raw_output": model_output}