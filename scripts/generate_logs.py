"""
Synthetic Production Log Generator for Edge AI Model Fine-Tuning.

This script generates a production-quality, synthetic dataset of realistic backend logs
resembling environments like Google Cloud Run, Docker, Kubernetes, FastAPI, Node.js,
PostgreSQL, Redis, Nginx, Cloud SQL, Pub/Sub, and Microservices.

Output: exactly 500 log samples saved in JSON Lines format (.jsonl) at `data/raw_logs/raw_logs.jsonl`.
Categories (125 each): noisy_error, pii_leak, stack_trace, healthy.
Log line count: exactly between 20 and 120 lines per log sample.
"""

import json
import logging
import pathlib
import random
from datetime import datetime, timezone, timedelta
import uuid

from faker import Faker

# Initialize global Faker instance
fake = Faker()

# =====================================================================
# CONSTANTS & REALISTIC SIMULATION POOLS
# =====================================================================

SERVICES = [
    "auth-service",
    "payment-service",
    "user-service",
    "inventory-service",
    "notification-service",
    "billing-service",
    "analytics-service",
    "gateway-service",
    "recommendation-service",
    "email-service",
    "search-service",
    "order-service",
    "worker-service",
    "scheduler-service",
    "report-service",
]

PLATFORMS = [
    "cloud_run",
    "kubernetes",
    "docker_fastapi",
    "docker_express",
    "nginx_microservice",
]

NAMESPACES = ["prod", "production", "staging", "default", "backend-services"]
HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH"]
ENDPOINTS = [
    "/api/v1/health",
    "/api/v1/auth/token",
    "/api/v1/auth/verify",
    "/api/v1/users/profile",
    "/api/v1/orders/checkout",
    "/api/v1/orders",
    "/api/v1/inventory/status",
    "/api/v1/payments/charge",
    "/api/v1/notifications/send",
    "/api/v1/billing/invoices",
    "/api/v1/analytics/events",
    "/api/v1/recommendations/feed",
    "/api/v1/search?q=query",
    "/healthz",
    "/metrics",
    "/readyz",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "PostmanRuntime/7.36.1",
    "python-requests/2.31.0",
    "Go-http-client/1.1",
    "curl/8.4.0",
]

NOISY_ERROR_TYPES = [
    ("Database timeout", "OperationalError: PostgreSQL query timeout expired after 30000ms executing SELECT * FROM orders WHERE status = $1"),
    ("Redis unavailable", "ConnectionRefusedError: [Errno 111] Connect call failed ('redis-master.internal', 6379) - socket connection refused"),
    ("Cloud SQL connection refused", "OperationalError: Cloud SQL connection pool exhausted: connection refused to instance primary-db-prod-01"),
    ("HTTP 500", "HTTPException: 500 Internal Server Error returned for POST /api/v1/orders/checkout"),
    ("Gateway timeout", "HTTP/1.1 504 Gateway Timeout while proxying request to upstream recommendation-service"),
    ("Service unavailable", "HTTP 503 Service Unavailable: Circuit breaker 'payment-service-cb' tripped OPEN due to consecutive failures"),
    ("Worker crash", "Worker process pid=419 exited unexpectedly with signal 9 (SIGKILL / OOM Killed). Memory usage limit exceeded (512MB)"),
    ("Background job failure", "Celery task 'billing.process_recurring_charges' [task_id=d89a12c4] failed after 3 retries with OperationalError"),
    ("Health check failed", "Probe failed: GET /healthz HTTP/1.1 returned status code 500 (Database connection pool unhealthy)"),
    ("Container restart", "System event: Kubelet triggered container restart for pod user-service-7f89c6b4d5 due to liveness probe timeout"),
    ("Cold start timeout", "Cloud Run cold start latency exceeded threshold (10.421s > 10.000s) for revision billing-service-0018-v2"),
    ("Dependency unavailable", "Upstream dependency notification-service is unreachable (dial tcp 10.128.4.19:8080: i/o timeout)"),
    ("Pub/Sub failure", "GoogleCloudError: Pub/Sub publish request failed on topic 'projects/gcp-prod/topics/order-events': DeadlineExceeded"),
    ("Webhook failure", "Failed to deliver webhook payload to https://hooks.stripe.com/event/evt_8892 status=504 Gateway Timeout"),
    ("Cache failure", "Redis cluster slot error on node 10.128.0.18:6379: CLUSTERDOWN The cluster is down or partitioned"),
    ("Disk full", "IOError: [Errno 28] No space left on device while attempting to write buffer to /var/log/app/worker.log"),
    ("Memory pressure", "WARNING: System memory pressure critical: 95.8% used (490MB/512MB). Triggering emergency GC cleanup"),
    ("Queue overflow", "RabbitMQ channel error: Queue 'order-processing-queue' size limit exceeded (current=10000, max=10000)"),
]


# =====================================================================
# SIMULATION CONTEXT CLASS
# =====================================================================

class SimulationContext:
    """Holds realistic metadata for simulating a single service execution window."""
    def __init__(self, service=None, platform=None):
        self.service = service or random.choice(SERVICES)
        self.platform = platform or random.choice(PLATFORMS)
        self.revision = f"{self.service}-00{random.randint(10, 99)}-{random.choice(['rev', 'prod', 'v1', 'v2', 'canary'])}"
        self.container_id = f"c_{uuid.uuid4().hex[:12]}"
        self.pod_name = f"{self.service}-{uuid.uuid4().hex[:10]}-{random.choice(['2k9qw', 'xl9mz', '8f7d1', '4p2nx', '9m3kl'])}"
        self.namespace = random.choice(NAMESPACES)
        self.instance_id = uuid.uuid4().hex
        self.trace_id = uuid.uuid4().hex
        self.span_id = uuid.uuid4().hex[:16]
        self.request_id = f"req_{uuid.uuid4().hex[:8]}"
        self.current_time = datetime.now(timezone.utc) - timedelta(days=random.randint(0, 14), hours=random.randint(0, 23))

    def next_time(self, min_ms=5, max_ms=800):
        """Advances simulation clock and returns the updated timestamp."""
        self.current_time += timedelta(milliseconds=random.randint(min_ms, max_ms))
        return self.current_time

    def format_time_iso(self, dt=None):
        """Returns ISO 8601 UTC timestamp."""
        t = dt or self.current_time
        return t.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    def format_time_nginx(self, dt=None):
        """Returns Nginx access log timestamp format."""
        t = dt or self.current_time
        return t.strftime("%d/%b/%Y:%H:%M:%S +0000")

    def format_time_uvicorn(self, dt=None):
        """Returns Uvicorn / standard Python logging timestamp format."""
        t = dt or self.current_time
        return t.strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]


# =====================================================================
# HELPER LOG FORMATTING FUNCTIONS
# =====================================================================

def format_log_line(ctx: SimulationContext, severity: str, message: str, extra_fields: dict = None) -> str:
    """Formats a single log message based on the simulated platform architecture."""
    ctx.next_time()

    if ctx.platform == "cloud_run" or (ctx.platform == "kubernetes" and random.random() < 0.6):
        # Structured JSON Log (Google Cloud Run / Kubernetes structured logging)
        data = {
            "timestamp": ctx.format_time_iso(),
            "severity": severity,
            "serviceContext": {"service": ctx.service, "version": ctx.revision},
            "trace": f"projects/gcp-prod-cloud/traces/{ctx.trace_id}",
            "spanId": ctx.span_id,
            "message": message,
        }
        if extra_fields:
            data.update(extra_fields)
        return json.dumps(data, ensure_ascii=False)

    elif ctx.platform == "kubernetes":
        # Standard Kubernetes container log line
        return f"{ctx.format_time_iso()} [{severity}] [{ctx.pod_name}] [ns:{ctx.namespace}] [trace_id:{ctx.trace_id}] {message}"

    elif ctx.platform == "docker_fastapi":
        # Uvicorn / FastAPI container stdout format
        return f"{ctx.format_time_uvicorn()} | {severity:<8} | {ctx.service} | [{ctx.request_id}] - {message}"

    elif ctx.platform == "docker_express":
        # Node.js Express / Pino or Winston format
        if random.random() < 0.55:
            pino_level = {"DEBUG": 20, "INFO": 30, "WARNING": 40, "ERROR": 50, "CRITICAL": 60}.get(severity, 30)
            data = {
                "level": pino_level,
                "time": int(ctx.current_time.timestamp() * 1000),
                "pid": random.randint(1, 40),
                "hostname": ctx.pod_name,
                "service": ctx.service,
                "trace_id": ctx.trace_id,
                "msg": message,
            }
            if extra_fields:
                data.update(extra_fields)
            return json.dumps(data, ensure_ascii=False)
        else:
            return f"[{ctx.format_time_iso()}] [{severity}] [express-worker-{ctx.container_id[:6]}] {message}"

    elif ctx.platform == "nginx_microservice":
        # Nginx microservice gateway logs
        if severity in ("ERROR", "CRITICAL", "WARNING") and random.random() < 0.45:
            return (
                f"{ctx.current_time.strftime('%Y/%m/%d %H:%M:%S')} [{severity.lower()}] "
                f"{random.randint(10,30)}#{random.randint(10,30)}: *{random.randint(1000,9999)} {message}, "
                f"client: {fake.ipv4()}, server: {ctx.service}.internal, "
                f'request: "{random.choice(HTTP_METHODS)} {random.choice(ENDPOINTS)} HTTP/1.1"'
            )
        else:
            status = extra_fields.get("status_code", random.choice([200, 201, 204, 301, 400, 500])) if extra_fields else random.choice([200, 201])
            return (
                f"{fake.ipv4()} - - [{ctx.format_time_nginx()}] "
                f'"{random.choice(HTTP_METHODS)} {random.choice(ENDPOINTS)} HTTP/1.1" {status} {random.randint(120, 5000)} '
                f'"-" "{random.choice(USER_AGENTS)}" rt={random.uniform(0.005, 0.450):.3f} req_id={ctx.request_id}'
            )

    # Fallback generic format
    return f"{ctx.format_time_iso()} [{severity}] [{ctx.service}] {message}"


def generate_routine_log_line(ctx: SimulationContext) -> str:
    """Generates a realistic routine INFO/DEBUG message for normal operation."""
    msg_type = random.choice([
        "health_check",
        "api_request",
        "db_query",
        "cache_op",
        "metrics",
        "pubsub",
        "auth_event",
    ])

    if msg_type == "health_check":
        status = random.choice([200, 200, 204])
        return format_log_line(ctx, "DEBUG", f"Health probe check GET /healthz completed with status={status}", {"status_code": status, "latency": f"{random.uniform(0.5, 2.5):.2f}ms"})

    elif msg_type == "api_request":
        method = random.choice(HTTP_METHODS)
        endpoint = random.choice(ENDPOINTS)
        status = random.choice([200, 201, 200, 204])
        latency_ms = random.uniform(8.0, 140.0)
        return format_log_line(
            ctx,
            "INFO",
            f"Handled HTTP {method} {endpoint} status={status} duration={latency_ms:.2f}ms",
            {"httpRequest": {"requestMethod": method, "requestUrl": endpoint, "status": status, "latency": f"{latency_ms/1000:.3f}s"}},
        )

    elif msg_type == "db_query":
        table = random.choice(["users", "orders", "inventory_items", "payments", "audit_logs", "sessions"])
        action = random.choice(["SELECT", "UPDATE", "INSERT INTO"])
        duration = random.uniform(1.2, 18.5)
        return format_log_line(ctx, "DEBUG", f"PostgreSQL connection pool executed: {action} {table} (duration: {duration:.2f}ms)")

    elif msg_type == "cache_op":
        key = f"{ctx.service}:cache:{uuid.uuid4().hex[:6]}"
        hit_miss = random.choice(["HIT", "HIT", "MISS"])
        return format_log_line(ctx, "DEBUG", f"Redis cache {hit_miss} for key={key} ttl=3600s")

    elif msg_type == "metrics":
        cpu = f"{random.uniform(10.0, 45.0):.1f}%"
        mem = f"{random.randint(180, 320)}MB/512MB"
        return format_log_line(ctx, "INFO", f"[METRICS] Service telemetry reported: cpu_usage={cpu} memory={mem} active_requests={random.randint(5, 35)}")

    elif msg_type == "pubsub":
        topic = f"projects/gcp-prod/topics/{random.choice(['order-events', 'user-updates', 'billing-sync'])}"
        return format_log_line(ctx, "INFO", f"Pub/Sub message acknowledged from subscription {topic}-sub msg_id={uuid.uuid4().hex[:12]}")

    else:
        user_id = f"usr_{random.randint(1000, 9999)}"
        return format_log_line(ctx, "INFO", f"Authentication check successful for session user={user_id} scopes=['read', 'write']")


# =====================================================================
# CATEGORY 1: NOISY ERROR LOG GENERATOR
# =====================================================================

def generate_noisy_error_log() -> str:
    """
    Generates a multiline log (20-120 lines) simulating production failures
    hidden among lots of routine INFO and DEBUG messages.
    """
    target_lines = random.randint(20, 120)
    ctx = SimulationContext()
    lines = []

    # Choose when the failure occurs in the log window
    error_idx = random.randint(min(10, target_lines - 5), max(12, target_lines - 4))

    error_name, error_desc = random.choice(NOISY_ERROR_TYPES)

    for i in range(target_lines):
        if i == error_idx:
            # Main failure log
            lines.append(format_log_line(ctx, "ERROR", f"[{error_name}] {error_desc}", {"status_code": 500, "error_type": error_name}))
        elif i == error_idx + 1:
            # Immediate consequence or retry attempt
            lines.append(format_log_line(ctx, "WARNING", f"Retrying operation after failure ({error_name}) attempt 1 of 3 - backoff 1.5s..."))
        elif i == error_idx + 2 and random.random() < 0.6:
            # Second failure or circuit breaker warning
            lines.append(format_log_line(ctx, "ERROR", f"Retry attempt 1 failed for {error_name}. Aborting request processing."))
        elif i == error_idx + 3 and random.random() < 0.4:
            # Optional embedded short traceback or system alert
            lines.append(format_log_line(ctx, "CRITICAL", f"System alert triggered for pod {ctx.pod_name}: consecutive failures exceeded threshold."))
        else:
            # Routine traffic (INFO/DEBUG noise)
            # Optionally mix in occasional fake PII or subtle warnings to increase variety (~15% of noisy lines)
            if random.random() < 0.12:
                lines.append(format_log_line(ctx, "INFO", f"Request payload preview: user_email={fake.email()} client_ip={fake.ipv4()} status=processing"))
            else:
                lines.append(generate_routine_log_line(ctx))

    return "\n".join(lines[:target_lines])


# =====================================================================
# CATEGORY 2: PII LEAK LOG GENERATOR
# =====================================================================

def generate_pii_log() -> str:
    """
    Generates a multiline log (20-120 lines) containing sensitive PII data
    (emails, phone numbers, JWTs, API keys, DB passwords, credit cards, etc.).
    """
    target_lines = random.randint(20, 120)
    ctx = SimulationContext()
    lines = []

    for _ in range(target_lines):
        # We scatter fake PII across ~40% of the lines, while 60% are routine/context logs
        if random.random() < 0.45:
            pii_scenario = random.choice([
                "email_phone",
                "jwt_bearer",
                "api_key",
                "db_password",
                "credit_card",
                "ids_hostnames",
                "auth_header",
            ])

            if pii_scenario == "email_phone":
                msg = f"User profile update payload received: email='{fake.email()}' phone='{fake.phone_number()}' ipv4='{fake.ipv4()}' ipv6='{fake.ipv6()}'"
                lines.append(format_log_line(ctx, "INFO", msg))

            elif pii_scenario == "jwt_bearer":
                fake_jwt = f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c3Jf{random.randint(1000,9999)}IiwiZW1haWwiOiJ{fake.email()[:8]}IiwiaWF0IjoxNzgzNTkyMTMzfQ.{uuid.uuid4().hex}{uuid.uuid4().hex[:10]}"
                msg = f"Token verification step passed. Session token: Bearer {fake_jwt} (session_id=sess_{uuid.uuid4().hex[:16]})"
                lines.append(format_log_line(ctx, "DEBUG", msg))

            elif pii_scenario == "api_key":
                key = random.choice([f"sk_live_{uuid.uuid4().hex[:24]}", f"gcp_secret_key_AIzaSy{uuid.uuid4().hex[:26]}", f"ak_prod_{uuid.uuid4().hex[:18]}"])
                msg = f"External API client initialized with X-API-Key header: {key} for customer_id=cust_{random.randint(10000, 99999)}"
                lines.append(format_log_line(ctx, "DEBUG", msg))

            elif pii_scenario == "db_password":
                db_host = f"db-primary.prod.internal.gcp.net"
                db_url = f"postgres://admin:Secret_{fake.word()}_{random.randint(100,999)}!@{db_host}:5432/production_db"
                msg = f"SQLAlchemy engine connecting with database URL: {db_url} (pool_size=20)"
                lines.append(format_log_line(ctx, random.choice(["INFO", "DEBUG", "WARNING"]), msg))

            elif pii_scenario == "credit_card":
                cc = fake.credit_card_number()
                msg = f"Payment gateway checkout transaction initiated for card={cc} amount=$142.50 customer_id=cust_{random.randint(10000, 99999)}"
                lines.append(format_log_line(ctx, "INFO", msg))

            elif pii_scenario == "ids_hostnames":
                msg = f"Employee audit trail: emp_id=emp_{random.randint(1000, 9999)} accessed internal resource http://redis-master.internal:6379/keys from ipv4={fake.ipv4()}"
                lines.append(format_log_line(ctx, "INFO", msg))

            elif pii_scenario == "auth_header":
                auth_hdr = f"Authorization: Basic dXNlcj_{random.randint(100,999)}OlNlY3JldFBPc3M="
                msg = f"Incoming HTTP request headers dump: Host={ctx.service}.internal {auth_hdr} User-Agent='PostmanRuntime/7.36.1'"
                lines.append(format_log_line(ctx, "DEBUG", msg))
        else:
            # Routine traffic or occasional error mixed with PII
            if random.random() < 0.15:
                lines.append(format_log_line(ctx, "ERROR", f"Failed to process customer order for email={fake.email()}: Payment gateway returned 402 Payment Required"))
            else:
                lines.append(generate_routine_log_line(ctx))

    return "\n".join(lines[:target_lines])


# =====================================================================
# CATEGORY 3: STACK TRACE LOG GENERATOR
# =====================================================================

def generate_stack_trace_log() -> str:
    """
    Generates a multiline log (20-120 lines) containing long, realistic stack traces
    resembling Python Tracebacks, Node.js/Express exceptions, PostgreSQL errors, etc.
    """
    target_lines = random.randint(20, 120)
    ctx = SimulationContext()
    lines = []

    trace_type = random.choice([
        "python_fastapi",
        "python_sqlalchemy",
        "nodejs_express",
        "nodejs_postgres",
        "container_crash",
    ])

    # Pre-crash routine lines
    pre_count = random.randint(4, max(5, target_lines // 3))
    for _ in range(pre_count):
        lines.append(generate_routine_log_line(ctx))

    # Generate the authentic multiline stack trace lines
    trace_lines = []
    if trace_type == "python_fastapi":
        exc_type = random.choice([
            ("ValueError", "invalid literal for int() with base 10: 'null'"),
            ("KeyError", f"'user_profile_token_for_{fake.email()}'"),
            ("TypeError", "'NoneType' object is not subscriptable"),
            ("AttributeError", "'OrderService' object has no attribute 'validate_signature'"),
            ("pydantic.error_wrappers.ValidationError", "2 validation errors for OrderCreateRequest\nbody -> items\n  field required (type=value_error.missing)"),
        ])
        trace_lines = [
            format_log_line(ctx, "ERROR", f"Exception raised in endpoint handler POST /api/v1/orders/checkout: {exc_type[0]}: {exc_type[1]}"),
            "Traceback (most recent call last):",
            "  File \"/usr/local/lib/python3.11/site-packages/starlette/routing.py\", line 686, in __call__",
            "    await self.app(scope, receive, send)",
            "  File \"/usr/local/lib/python3.11/site-packages/starlette/middleware/exceptions.py\", line 79, in __call__",
            "    raise exc",
            "  File \"/usr/local/lib/python3.11/site-packages/starlette/middleware/exceptions.py\", line 68, in __call__",
            "    await self.app(scope, receive, send)",
            "  File \"/usr/local/lib/python3.11/site-packages/fastapi/applications.py\", line 280, in __call__",
            "    await super().__call__(scope, receive, send)",
            "  File \"/usr/local/lib/python3.11/site-packages/fastapi/routing.py\", line 237, in app",
            "    raw_response = await run_endpoint_function(",
            "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.11/site-packages/fastapi/routing.py\", line 165, in run_endpoint_function",
            "    return await dependant.call(**values)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/src/api/v1/endpoints/orders.py\", line 142, in create_checkout_order",
            "    order_result = await order_service.process_payment(payload.customer_id, payload.amount)",
            "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/src/services/order_service.py\", line 89, in process_payment",
            "    user_profile = self.cache.get_user(customer_id)",
            "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            f"{exc_type[0]}: {exc_type[1]}",
        ]

    elif trace_type == "python_sqlalchemy":
        trace_lines = [
            format_log_line(ctx, "ERROR", "Unhandled exception during SQLAlchemy session commit: psycopg2.OperationalError: FATAL: remaining connection slots are reserved for non-replication superuser connections"),
            "Traceback (most recent call last):",
            "  File \"/usr/local/lib/python3.11/site-packages/sqlalchemy/engine/base.py\", line 1910, in _execute_context",
            "    self.dialect.do_execute(cursor, statement, parameters, context)",
            "  File \"/usr/local/lib/python3.11/site-packages/sqlalchemy/engine/default.py\", line 736, in do_execute",
            "    cursor.execute(statement, parameters)",
            "psycopg2.OperationalError: FATAL: remaining connection slots are reserved for non-replication superuser connections",
            "",
            "The above exception was the direct cause of the following exception:",
            "",
            "Traceback (most recent call last):",
            "  File \"/app/src/db/repository.py\", line 214, in save_transaction_record",
            "    self.session.commit()",
            "  File \"/usr/local/lib/python3.11/site-packages/sqlalchemy/orm/session.py\", line 1451, in commit",
            "    self._transaction.commit(_to_root=self.is_root)",
            "  File \"/usr/local/lib/python3.11/site-packages/sqlalchemy/orm/session.py\", line 829, in commit",
            "    self._prepare_impl()",
            "  File \"/usr/local/lib/python3.11/site-packages/sqlalchemy/orm/session.py\", line 808, in _prepare_impl",
            "    self.session.flush()",
            "sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) FATAL: remaining connection slots are reserved for non-replication superuser connections",
            "[SQL: INSERT INTO payments (id, customer_id, amount, status) VALUES (%(id)s, %(customer_id)s, %(amount)s, %(status)s)]",
            f"[parameters: {{'id': 'pay_{uuid.uuid4().hex[:8]}', 'customer_id': 'cust_{random.randint(10000, 99999)}', 'amount': 249.99, 'status': 'PENDING'}}]",
        ]

    elif trace_type == "nodejs_express":
        trace_lines = [
            format_log_line(ctx, "ERROR", "UnhandledPromiseRejectionWarning: TypeError: Cannot read properties of undefined (reading 'token')"),
            "UnhandledPromiseRejectionWarning: TypeError: Cannot read properties of undefined (reading 'token')",
            "    at AuthController.verifySession (/app/src/controllers/authController.js:142:38)",
            "    at processTicksAndRejections (internal/process/task_queues.js:95:5)",
            "    at async AuthMiddleware.authenticate (/app/src/middleware/auth.js:42:20)",
            "    at async Layer.handle [as handle_request] (/app/node_modules/express/lib/router/layer.js:95:5)",
            "    at async trim_prefix (/app/node_modules/express/lib/router/index.js:328:13)",
            "    at async /app/node_modules/express/lib/router/index.js:286:9",
            "    at async Function.process_params (/app/node_modules/express/lib/router/index.js:346:12)",
            "    at async next (/app/node_modules/express/lib/router/index.js:280:10)",
            "    at async cors (/app/node_modules/cors/lib/index.js:188:7)",
            "    at async Layer.handle [as handle_request] (/app/node_modules/express/lib/router/layer.js:95:5)",
            "UnhandledPromiseRejectionWarning: Unhandled promise rejection. This error originated either by throwing inside of an async function without a catch block, or by rejecting a promise which was not handled with .catch().",
        ]

    elif trace_type == "nodejs_postgres":
        trace_lines = [
            format_log_line(ctx, "ERROR", "Database connection failure during query execution: connect ECONNREFUSED 10.128.0.18:5432"),
            "Error: connect ECONNREFUSED 10.128.0.18:5432",
            "    at TCPConnectWrap.afterConnect [as oncomplete] (net.js:1146:16)",
            "    at Protocol._enqueue (/app/node_modules/pg/lib/protocol/protocol.js:145:15)",
            "    at Client.connect (/app/node_modules/pg/lib/client.js:101:18)",
            "    at BoundPool._connect (/app/node_modules/pg-pool/index.js:213:12)",
            "    at /app/node_modules/pg-pool/index.js:188:14",
            "    at new Promise (<anonymous>)",
            "    at BoundPool.connect (/app/node_modules/pg-pool/index.js:183:12)",
            "    at DatabaseService.query (/app/src/services/database.js:45:28)",
            "    at async InventoryController.checkStock (/app/src/controllers/inventoryController.js:68:22)",
            "    at async Layer.handle [as handle_request] (/app/node_modules/express/lib/router/layer.js:95:5)",
            "    at async next (/app/node_modules/express/lib/router/route.js:144:14)",
            "    at async Route.dispatch (/app/node_modules/express/lib/router/route.js:114:3)",
        ]

    else:
        trace_lines = [
            format_log_line(ctx, "CRITICAL", f"Container called exit(1). Command failed with status code 1. System error in worker process."),
            "Traceback (most recent call last):",
            "  File \"/app/main.py\", line 84, in <module>",
            "    asyncio.run(main())",
            "  File \"/usr/local/lib/python3.11/asyncio/runners.py\", line 190, in run",
            "    return runner.run(main)",
            "  File \"/usr/local/lib/python3.11/asyncio/runners.py\", line 118, in run",
            "    return self._loop.run_until_complete(task)",
            "  File \"/usr/local/lib/python3.11/asyncio/base_events.py\", line 653, in run_until_complete",
            "    return future.result()",
            "  File \"/app/src/worker.py\", line 112, in main",
            "    await subscriber.listen_and_process()",
            "  File \"/app/src/pubsub/subscriber.py\", line 78, in listen_and_process",
            "    raise RuntimeError(\"PubSub subscriber connection dropped unexpectedly without recovery options\")",
            "RuntimeError: PubSub subscriber connection dropped unexpectedly without recovery options",
        ]

    lines.extend(trace_lines)

    # Post-crash / recovery or additional routine lines until target_lines reached
    remaining = target_lines - len(lines)
    if remaining > 0:
        lines.append(format_log_line(ctx, "WARNING", f"Container/worker crash detected for {ctx.service}. Attempting graceful restart cleanup..."))
        for _ in range(remaining - 1):
            lines.append(generate_routine_log_line(ctx))
    elif remaining < 0:
        # If traceback exceeded target_lines, trim or adjust pre_count
        lines = lines[:target_lines]

    return "\n".join(lines[:target_lines])


# =====================================================================
# CATEGORY 4: HEALTHY LOG GENERATOR
# =====================================================================

def generate_healthy_log() -> str:
    """
    Generates a multiline log (20-120 lines) representing entirely healthy,
    normal operation (INFO/DEBUG, startup, health checks, metrics, successful API requests).
    No crashes, no exceptions, no stack traces, minimal or no PII.
    """
    target_lines = random.randint(20, 120)
    ctx = SimulationContext()
    lines = []

    # Optionally start with startup sequence (~30% of healthy logs)
    if random.random() < 0.3:
        lines.extend([
            format_log_line(ctx, "INFO", f"[STARTUP] Initializing microservice revision {ctx.revision} on platform {ctx.platform}"),
            format_log_line(ctx, "INFO", f"[STARTUP] Loading environment configurations from /app/config/settings.yaml (namespace: {ctx.namespace})"),
            format_log_line(ctx, "INFO", f"[STARTUP] Connecting to Cloud SQL PostgreSQL instance primary-pg-prod-01 (pool_min=5, pool_max=20)"),
            format_log_line(ctx, "INFO", f"[STARTUP] PostgreSQL connection pool initialized successfully with 10 active workers"),
            format_log_line(ctx, "INFO", f"[STARTUP] Redis cache connection verified: cluster node 10.128.0.14:6379 (latency: 0.8ms)"),
            format_log_line(ctx, "INFO", f"[STARTUP] Pub/Sub subscriber listening on projects/gcp-prod/subscriptions/{ctx.service}-sub-v1"),
            format_log_line(ctx, "INFO", f"[STARTUP] Cloud Run traffic routing update: revision {ctx.revision} allocated 100% traffic"),
            format_log_line(ctx, "INFO", f"[STARTUP] HTTP server listening on 0.0.0.0:8080 (workers=4, pid={random.randint(1, 20)})"),
        ])

    while len(lines) < target_lines:
        lines.append(generate_routine_log_line(ctx))

    return "\n".join(lines[:target_lines])


# =====================================================================
# MAIN ENTRYPOINT
# =====================================================================

def main():
    """
    Main execution pipeline:
    1. Generates exactly 125 logs from each of the 4 categories (total 500).
    2. Combines and shuffles all log samples randomly.
    3. Assigns sequential integer IDs (`id`: 1 to 500).
    4. Writes the final JSONL dataset to `data/raw_logs/raw_logs.jsonl`.
    """
    print("Starting generation of synthetic backend logs dataset...")

    # 1. Generate exactly 125 samples per category
    noisy_errors = [generate_noisy_error_log() for _ in range(125)]
    pii_leaks = [generate_pii_log() for _ in range(125)]
    stack_traces = [generate_stack_trace_log() for _ in range(125)]
    healthy_logs = [generate_healthy_log() for _ in range(125)]

    # 2. Combine into dictionaries
    records = []
    for log in noisy_errors:
        records.append({"category": "noisy_error", "log": log})
    for log in pii_leaks:
        records.append({"category": "pii_leak", "log": log})
    for log in stack_traces:
        records.append({"category": "stack_trace", "log": log})
    for log in healthy_logs:
        records.append({"category": "healthy", "log": log})

    # Verify initial count
    assert len(records) == 500, f"Expected exactly 500 records before shuffling, got {len(records)}"

    # 3. Shuffle all logs before writing so categories are mixed
    random.shuffle(records)

    # 4. Assign sequential IDs after shuffling
    for idx, rec in enumerate(records, start=1):
        rec["id"] = idx

    # 5. Create output directory automatically if it doesn't exist
    output_path = pathlib.Path("data/raw_logs/raw_logs.jsonl")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 6. Write final JSONL file
    with open(output_path, "w", encoding="utf-8") as f:
        for rec in records:
            # Order keys explicitly: id, category, log
            ordered_rec = {
                "id": rec["id"],
                "category": rec["category"],
                "log": rec["log"],
            }
            f.write(json.dumps(ordered_rec, ensure_ascii=False) + "\n")

    print(f"Successfully generated exactly {len(records)} log samples and saved to: {output_path}")


if __name__ == "__main__":
    main()
