# Monitoring & Observability Guide

This guide covers setting up monitoring, error tracking, and observability for LLM Council.

## Quick Setup

### 1. Install Sentry SDK

**Backend:**
```bash
uv add sentry-sdk[fastapi]
```

**Frontend:**
```bash
cd frontend
npm install @sentry/react
```

### 2. Configure Sentry

**Backend (`backend/sentry_config.py`):**
```python
import sentry_sdk
import os

def init_sentry():
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
            profiles_sample_rate=0.1,  # 10% profiling
            environment=os.getenv("ENVIRONMENT", "development"),
            release=os.getenv("APP_VERSION", "unknown"),
        )
```

**Frontend (`src/sentry.js`):**
```javascript
import * as Sentry from "@sentry/react";

export function initSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  if (dsn) {
    Sentry.init({
      dsn: dsn,
      integrations: [
        Sentry.browserTracingIntegration(),
        Sentry.replayIntegration({
          maskAllText: false,
          blockAllMedia: false,
        }),
      ],
      tracesSampleRate: 0.1,
      replaysSessionSampleRate: 0.1,
      replaysOnErrorSampleRate: 1.0,
      environment: import.meta.env.MODE,
    });
  }
}
```

### 3. Environment Variables

Add to your `.env`:
```bash
# Sentry Configuration
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
VITE_SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
ENVIRONMENT=production
APP_VERSION=1.0.0
```

## Logging

LLM Council uses **structlog** for structured logging.

### Configuration

The logging is configured in `backend/logging_config.py`:
- JSON format for production (easy to parse)
- Colored console output for development
- Context binding for request tracing

### Log Levels

| Level | Use Case |
|-------|----------|
| DEBUG | Detailed debugging information |
| INFO | General operational information |
| WARNING | Unexpected but recoverable issues |
| ERROR | Errors that need attention |
| CRITICAL | System-critical failures |

### Example Usage

```python
from backend.logging_config import get_logger

logger = get_logger(__name__)

# Log with context
logger.info("Processing request",
    user_id=user_id,
    conversation_id=conv_id,
    model="gpt-4"
)

# Log errors with stack trace
try:
    result = await process_query()
except Exception as e:
    logger.error("Query failed",
        error=str(e),
        exc_info=True
    )
```

## Metrics

### Built-in Metrics

LLM Council tracks these metrics internally:

1. **Session Usage**
   - Total input tokens
   - Total output tokens
   - Total cost
   - Requests per model

2. **API Response Times**
   - Logged via middleware

3. **Cache Statistics**
   - Cache hits/misses
   - Cache size

### Prometheus Integration (Optional)

Install prometheus client:
```bash
uv add prometheus-client
```

Add metrics endpoint:
```python
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

RESPONSE_TIME = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

# Add endpoint
@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

## Health Checks

Add a health check endpoint for load balancers:

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": os.getenv("APP_VERSION", "unknown"),
        "checks": {
            "database": await check_database(),
            "cache": check_cache(),
            "openrouter": await check_openrouter()
        }
    }
```

## Error Tracking Best Practices

### 1. Capture Context

Always include relevant context with errors:
```python
sentry_sdk.set_context("conversation", {
    "id": conversation_id,
    "message_count": len(messages)
})

sentry_sdk.set_user({
    "id": user_id,
    "email": user_email
})
```

### 2. Set Error Levels

```python
# Informational (low priority)
sentry_sdk.capture_message("User exported conversation", level="info")

# Warning (medium priority)
sentry_sdk.capture_message("Rate limit approaching", level="warning")

# Error (high priority)
sentry_sdk.capture_exception(error)
```

### 3. Filter Sensitive Data

Configure Sentry to scrub sensitive data:
```python
sentry_sdk.init(
    dsn=dsn,
    before_send=scrub_sensitive_data,
)

def scrub_sensitive_data(event, hint):
    # Remove API keys
    if 'request' in event and 'headers' in event['request']:
        headers = event['request']['headers']
        if 'Authorization' in headers:
            headers['Authorization'] = '[REDACTED]'
    return event
```

## Dashboard Setup

### Sentry Dashboard

1. Create project in Sentry
2. Set up alerts for:
   - Error rate spikes
   - Performance degradation
   - New error types

### Grafana Dashboard (with Prometheus)

1. Add Prometheus data source
2. Create panels for:
   - Request rate
   - Error rate
   - Response time percentiles
   - Token usage
   - Cost tracking

## Alerting

### Recommended Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| High Error Rate | Errors > 5% for 5 min | Critical |
| Slow Responses | P95 > 30s for 5 min | Warning |
| API Key Issues | Auth errors > 10/min | Critical |
| High Cost | Daily cost > threshold | Warning |
| Memory Usage | > 90% for 10 min | Critical |

## Troubleshooting

### Common Issues

1. **Sentry not capturing errors**
   - Check DSN is correct
   - Verify SDK is initialized before errors occur
   - Check sample rate isn't 0

2. **Missing context in errors**
   - Ensure context is set before error occurs
   - Use breadcrumbs for action trails

3. **Too many events**
   - Adjust sample rate
   - Add filtering for expected errors
   - Use fingerprinting for grouping

### Debug Mode

Enable verbose logging:
```bash
LOG_LEVEL=DEBUG python -m backend.main
```

## Production Checklist

- [ ] Sentry DSN configured
- [ ] Environment properly set
- [ ] Sample rates appropriate for traffic
- [ ] Sensitive data scrubbing configured
- [ ] Alerts configured
- [ ] Health check endpoint working
- [ ] Structured logging enabled
- [ ] Error boundaries in frontend
- [ ] Source maps uploaded to Sentry
