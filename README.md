# Semantic MCP Firewall 🛡️

**An Edge-Deployed Logging Firewall for Backend Telemetry & Observability**

---

## 📌 Project Overview

**Semantic MCP Firewall** (`edge_firewall_model`) is an edge-optimized AI firewall designed to sit between raw, high-volume backend microservice logs (e.g., Kubernetes, Cloud Run, FastAPI, Node.js, Cloud SQL) and downstream telemetry analysis or observability pipelines.

Raw server logs often contain massive amounts of routine noise (`INFO`/`DEBUG` chatter), multiline stack traces, and sensitive Personally Identifiable Information (**PII** such as JWTs, API keys, emails, phone numbers, and database connection strings). Sending this unfiltered stream to large central LLMs or analytics platforms creates severe bottlenecks, data leaks, and high costs.

### Core Objectives
1. **Filter Noise**: Instantly ignore routine health checks and benign debug logs.
2. **Redact PII**: Automatically identify and redact sensitive credentials and personal data before they leave the edge.
3. **Structured Telemetry Output**: Parse unstructured multiline log clusters into **valid, strict JSON** matching our telemetry schema:
   ```json
   {
     "error_type": "PubSubFailure",
     "affected_service": "email-service",
     "root_cause": "Publish request deadline exceeded",
     "pii_redacted": true,
     "summary": "Email service failed to synchronize payloads via Pub/Sub when the network deadline was exceeded."
   }
   ```

---

## 🛠️ What We Did Till Now

Our journey so far covers the complete lifecycle from **synthetic data generation** to **ETL processing**, and finally **model fine-tuning and edge export**.

### 1. Synthetic Data Engineering (`scripts/`)
- **Realistic Production Log Generator ([generate_logs.py](file:///d:/semantic-mcp-firewall/scripts/generate_logs.py))**:
  Built a generator producing exactly **500 multiline log samples** (strictly 4–8 lines per cluster) distributed across 4 distinct categories (`noisy_error`, `pii_leak`, `stack_trace`, and `healthy`).
- **Batch Processing & ETL ([prepare_chunks.py](file:///d:/semantic-mcp-firewall/scripts/prepare_chunks.py))**:
  Created a processing pipeline that splits the 500 intact log clusters into 4 chunks (`logs_chunk_1.txt` to `logs_chunk_4.txt`) wrapped in `<LOG_START>` and `<LOG_END>` blocks for batch labeling.
- **ChatML Dataset Builder & Splitter ([build_dataset.py](file:///d:/semantic-mcp-firewall/scripts/build_dataset.py))**:
  Combined 4 target JSON ground-truth files (`target_1.json` through `target_4.json`), paired them with raw logs by `id`, formatted them into strict **Hugging Face ChatML** format, dropped temporary tracking IDs, and performed an **80/20 train/test split**:
  - `data/training/train_data.jsonl` (400 samples)
  - `data/training/test_data.jsonl` (100 samples)

---

## 🧠 Model Fine-Tuning & Edge Export (`notebooks/`)

We performed supervised fine-tuning (**SFT**) on a compact, highly capable edge LLM inside `notebooks/edge_training.ipynb` using **Unsloth** and **TRL**.

### Base Model & QLoRA Setup
- **Base Model**: `unsloth/Llama-3.2-1B-Instruct` (1 Billion parameters).
- **Quantization**: Loaded in **4-bit (`load_in_4bit = True`)**, reducing the model's VRAM footprint to ~700MB so it can run efficiently on edge servers and edge GPUs (like Tesla T4).
- **LoRA Adapters**: Attached Rank-16 (`r = 16`, `lora_alpha = 16`) adapters to all primary attention and projection layers (`q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`).
- **Memory Optimization**: Used `"unsloth"` gradient checkpointing for 2x faster training and minimal VRAM consumption.

### Training Configuration & Metrics (`SFTTrainer`)
- **System Prompt**: Enforced strict behavior instructing the model to act as an Edge Logging Firewall and output only valid telemetry schema JSON.
- **Sequence Length**: Configured up to `max_seq_length = 2048` tokens (our dataset averages ~607 tokens per conversation).
- **Hyperparameters**:
  - `epochs`: 2 (100 total steps across 400 training samples)
  - `learning_rate`: `2e-4` with linear decay and 5 warmup steps
  - `batch_size`: 2 per device with `gradient_accumulation_steps = 4` (effective batch size of 8)
  - `optimizer`: `adamw_8bit`
- **Training Results**:
  - **Epoch 1**: Training Loss: `0.6276` | Validation Loss: `0.6059`
  - **Epoch 2**: Training Loss: `0.5424` | Validation Loss: `0.5691`
  *The model converged smoothly without overfitting, accurately capturing log structure and redaction rules.*

### Edge Inference & GGUF Quantization (`q4_k_m`)
- **Inference Verification**: Tested the fine-tuned model (`FastLanguageModel.for_inference`) on unseen multiline server logs and verified 100% schema-compliant JSON outputs.
- **16-bit Merge & GGUF Export**: Merged the LoRA adapter weights directly into the base 16-bit model (`save_pretrained_gguf`).
- **4-Bit GGUF (`q4_k_m`)**: Used `llama.cpp` to convert the finalized model into a `Q4_K_M` GGUF file (`edge_firewall_model_gguf/llama-3.2-1b-instruct.Q4_K_M.gguf`).
- **Ready for Edge Deployment**: The exported `.gguf` file and included `Modelfile` allow instant, low-latency execution on CPU/GPU edge nodes using **Ollama** (`ollama create edge-firewall -f Modelfile`) or standalone `llama.cpp`.

---

## 📂 Repository Structure

```text
semantic-mcp-firewall/
├── data/
│   ├── raw_logs/          # 500 multiline raw log clusters (.jsonl)
│   ├── processing_chunks/ # 4 text chunk files with <LOG_START>/<LOG_END> blocks
│   ├── target/            # Ground truth telemetry summary JSONs (`target_1.json` to `target_4.json`)
│   └── training/          # Final ChatML dataset (`train_data.jsonl` & `test_data.jsonl`)
├── scripts/
│   ├── generate_logs.py   # Synthetic log cluster dataset generator
│   ├── prepare_chunks.py  # Chunk splitter keeping multiline logs intact
│   └── build_dataset.py   # ChatML formatter & 80/20 train/test splitter
├── notebooks/
│   └── edge_training.ipynb # Complete Unsloth/Llama-3.2-1B fine-tuning & GGUF export notebook
└── README.md
```