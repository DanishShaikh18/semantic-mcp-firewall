# 1. Use a lightweight Python base image
FROM python:3.10-slim

# 2. Set the working directory inside the container
WORKDIR /code

# 3. Install system dependencies required to compile llama-cpp-python
RUN apt-get update && apt-get install -y \
    build-essential \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 4. Copy only the requirements first (this caches the installation step)
COPY requirements.txt .

# 5. Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy your FastAPI application code
COPY ./app /code/app

# 7. Copy the local model file directly into the container
COPY ./models/llama-3.2-1b-instruct.Q4_K_M.gguf /code/models/llama-3.2-1b-instruct.Q4_K_M.gguf

# 8. Cloud Run expects apps to listen on port 8080 by default
EXPOSE 8080

# 9. Start the FastAPI server using Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]