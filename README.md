# Fine-Tuned-Log-to-JSON-Parser ☁️🤖

![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![GCP](https://img.shields.io/badge/Google_Cloud-Cloud_Run-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.139+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Llama](https://img.shields.io/badge/Llama_3.2_1B-PEFT%20%2F%20QLoRA-0467DF?style=for-the-badge)
![llama.cpp](https://img.shields.io/badge/llama.cpp-CPU_Inference-FF7F00?style=for-the-badge)

**🌐 Live API / Swagger UI**: [https://log-distiller-service-491483155818.asia-south1.run.app/docs](https://log-distiller-service-491483155818.asia-south1.run.app/docs)

**An end-to-end AI & Cloud project that intercepts raw backend logs, leverages a fine-tuned LLM to redact PII and extract structured JSON telemetry, and runs entirely serverless on Google Cloud.**

---

## 📌 Project Overview

In modern cloud environments, microservices generate massive volumes of unstructured log streams (stack traces, debug chatter, health checks). Sending this raw data directly to central observability platforms is expensive, and transmitting plain-text Personally Identifiable Information (PII) is a severe security risk.

**Fine-Tuned-Log-to-JSON-Parser** acts as a serverless edge firewall. It uses a specialized, fine-tuned **1-Billion parameter AI model** to parse unstructured logs, filter out benign noise, redact sensitive credentials, and output strict JSON telemetry. 

By utilizing **GGUF quantization** and **llama.cpp**, this inference runs entirely on cost-effective CPUs. The entire system is deployed on **Google Cloud Run** using a scale-to-zero architecture, demonstrating a practical, highly optimized intersection of **AI Engineering and Cloud DevOps**.

---

## ☁️ Cloud Architecture (GCP Deployment)

The deployment is architected for maximum cost-efficiency, strict security, and stable CPU-based inference.

- **Serverless Compute (Google Cloud Run)**: The FastAPI application and containerized `llama.cpp` inference engine are deployed to Cloud Run (`asia-south1`).
- **Scale-to-Zero Configuration**: `min-instances=0` ensures that zero compute costs are incurred when the API is idle. `max-instances=2` provides a strict ceiling to prevent runaway billing under heavy load.
- **Optimized CPU Inference**: Allocated exactly **1 vCPU and 2Gi Memory** per instance.
- **Strict Concurrency**: Configured with `concurrency=1`. This is a critical engineering decision for LLM inference on CPUs, ensuring that each request has exclusive access to the instance's RAM and CPU, preventing memory exhaustion and latency spikes.
- **Container Registry**: Docker images are built and stored securely in **Google Artifact Registry**.
- **Least-Privilege Security**: Operates under a dedicated IAM Service Account (`log-parser-runner`), replacing the default compute account to maintain strict access boundaries.

---

## 🧠 AI & Fine-Tuning Pipeline

The underlying intelligence is driven by a rigorously fine-tuned model optimized for edge deployments.

1. **Base Model**: `Llama-3.2-1B-Instruct`
2. **Synthetic Data Engineering**: Generated hundreds of multiline log clusters representing real-world failure modes (e.g., `DatabaseTimeout`, `AuthExhaustion`), multiline stack traces, and routine health checks, formatted into strict Hugging Face ChatML.
3. **Parameter-Efficient Fine-Tuning (PEFT)**: Fine-tuned using **QLoRA** via **Unsloth** (`r=16`, `lora_alpha=16`), targeting all primary attention layers.
4. **Stable Convergence**: Employed the 8-bit Adam optimizer (`adamw_8bit`) and Gradient Accumulation over 100 training steps.
5. **Edge Quantization**: The final model weights were merged and exported to a **4-bit GGUF format (`Q4_K_M`)**. This reduced the memory footprint to ~700MB, making serverless, zero-GPU deployment mathematically viable.

---

## 📂 Project Structure

```text
Fine-Tuned-Log-to-JSON-Parser/
├── app/
│   ├── main.py                   # FastAPI application running offline llama.cpp inference
│   └── test_sender.py            # Test script to evaluate the live Cloud Run endpoint
├── data/
│   └── ...                       # Raw logs, target schemas, and final ChatML datasets
├── models/
│   └── llama-3.2-1b-instruct.Q4_K_M.gguf  # Quantized 4-bit edge model (Excluded from Git)
├── notebooks/
│   └── edge_training.ipynb       # End-to-end Unsloth QLoRA training and GGUF export workflow
├── scripts/
│   └── ...                       # Python scripts for synthetic log generation and ETL
├── Dockerfile                    # Multi-stage containerization for Cloud Run
├── requirements.txt              # Core API dependencies (FastAPI, llama-cpp-python, etc.)
└── requirements-training.txt     # Heavy ML dependencies (Torch, Transformers, Unsloth)
```

---

## 🚀 API Usage & Testing

The deployed Cloud Run service accepts raw, unstructured text directly via a `text/plain` POST request.

### Example Request
You can test the API by sending a raw stack trace or log block:

```bash
curl -X POST "https://log-distiller-service-491483155818.asia-south1.run.app/distill_logs" \
     -H "Content-Type: text/plain" \
     -d "[2026-07-19 23:25:07] CRITICAL [database-service] Postgres connection pool failed! FATAL: password authentication failed for user 'admin'. Database string used: postgres://admin:SuperSecretPassword123@10.0.5.42:5432/prod_db"
```

### Example Response (Parsed JSON)
The fine-tuned model strips the noise, redacts the sensitive database password, and structures the output:

```json
{
  "error_type": "DatabaseConnectionError",
  "affected_service": "database-service",
  "root_cause": "Authentication failure",
  "pii_redacted": true,
  "summary": "Database connection failed due to authentication failure in the connection pool."
}
```

---

## 💻 Local Development

If you wish to run the containerized service locally:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/Fine-Tuned-Log-to-JSON-Parser.git
   cd Fine-Tuned-Log-to-JSON-Parser
   ```
2. **Provide the Model**:
   Download the fine-tuned `llama-3.2-1b-instruct.Q4_K_M.gguf` file and place it inside the `models/` directory.
3. **Build and Run via Docker**:
   ```bash
   docker build -t log-distiller .
   docker run -p 8080:8080 log-distiller
   ```
4. **Access the UI**:
   Navigate to `http://localhost:8080/docs` to use the interactive Swagger UI.