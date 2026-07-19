import requests

# The local endpoint exposed by your FastAPI server
url = "http://127.0.0.1:8080/distill_logs"

# A realistic, messy sample log showing a failure mixed with healthy requests
sample_raw_log = """
192.168.1.45 - - [16/Jul/2026:23:14:02 +0000] "GET /api/v1/auth/status HTTP/1.1" 200 422
2026-07-16 23:14:03 [CRITICAL] auth-service internal connection pool exhaustion. Failed to connect to database instance at 10.0.4.12:5432. Retrying in 5s... ConnectionTimeoutException: pool checkout timeout after 30000ms.
192.168.1.99 - - [16/Jul/2026:23:14:05 +0000] "POST /api/v1/metrics HTTP/1.1" 201 120
"""

print("Sending 1 raw sample error log to the Edge Firewall...")
response = requests.post(url, data=sample_raw_log.strip())

print("\n--- Response From Local AI Microservice ---")
print(response.json())