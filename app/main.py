from fastapi import FastAPI, Request
from llama_cpp import Llama
import json

app = FastAPI(title="Edge Logging Firewall")

# Load the GGUF model into memory on startup
print("Loading Llama 3.2 Edge Firewall onto CPU...")
llm = Llama(
    model_path="models\llama-3.2-1b-instruct.Q4_K_M.gguf",
    n_ctx=2048,          # Context window for log clusters
    n_gpu_layers=0,      # 0 means pure CPU execution
    chat_format="chatml" # Matches your Unsloth training template
)

SYSTEM_PROMPT = "You are an Edge Logging Firewall. Analyze backend production logs, ignore irrelevant noise, redact sensitive PII, and output ONLY valid JSON matching the telemetry schema."

@app.post("/distill_logs")
async def analyze_logs(request: Request):
    # Receive the raw text bytes from the sender script
    raw_log_bytes = await request.body()
    raw_log = raw_log_bytes.decode("utf-8")
    
    # Format the payload exactly like the training data layout
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": raw_log}
    ]
    
    # Run CPU inference with strict determinism
    response = llm.create_chat_completion(
        messages=messages,
        max_tokens=256,
        temperature=0.1
    )
    
    model_output = response["choices"][0]["message"]["content"].strip()
    
    try:
        # Convert string output to formal JSON dictionary response
        return json.loads(model_output)
    except json.JSONDecodeError:
        return {"status": "error", "raw_output": model_output}