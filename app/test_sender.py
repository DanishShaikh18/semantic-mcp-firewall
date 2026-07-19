import requests
import time
import json

# Your live Google Cloud Run production URL
URL = "https://log-distiller-service-491483155818.asia-south1.run.app/distill_logs"

# Sample log data to test
payload = {
    "log": "ERROR 2026-07-19 21:45:00 [auth-service] Connection timed out after 5000ms"
}

print("Sending request to production Cloud Run instance...")
start_time = time.time()

try:
    # Send the raw string directly since the FastAPI endpoint accepts text/plain
    response = requests.post(URL, data=payload["log"], headers={"Content-Type": "text/plain"})
    end_time = time.time()
    
    latency = end_time - start_time
    print(f"Status Code: {response.status_code}")
    print(f"Time Taken: {latency:.2f} seconds")
    print("\nParsed Model Output:")
    print(json.dumps(response.json(), indent=4))

except Exception as e:
    print(f"An error occurred: {e}")