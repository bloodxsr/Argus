# OpenTelemetry

Collects traces, metrics, and logs from applications. Bridges the gap between infrastructure-level eBPF data and application-level behavior.

Feeds data into [[Telemetry Layer]].

---

## What It Adds That eBPF Misses

eBPF sees OS-level calls. OTel sees application-level semantics:

| eBPF Sees | OTel Sees |
|---|---|
| TCP connection to port 5432 | Query: `SELECT * FROM users WHERE id=1 OR 1=1` |
| HTTP request received | `POST /api/admin/users` with response 403 |
| File read | `config.load("/etc/app/secrets.yaml")` |

This is critical for detecting SQL injection, API abuse, and application-layer attacks that are invisible at the kernel level.

---

## Implementation

### OTEL Collector Config

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s
    send_batch_size: 1000

  # Filter to only security-relevant spans
  filter:
    spans:
      exclude:
        match_type: strict
        services: ["health-check", "metrics-collector"]

exporters:
  # Forward to AGRUS telemetry processor
  otlp/agrus:
    endpoint: agrus-telemetry:4317
    tls:
      insecure: true

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch, filter]
      exporters: [otlp/agrus]
```

### Security-Relevant Span Detection

```rust
// In Telemetry Layer — process incoming OTEL spans
async fn process_otel_span(span: OtelSpan) -> Option<UnifiedEvent> {
    // Flag anomalous HTTP patterns
    if let Some(status) = span.attributes.get("http.status_code") {
        if is_anomalous_status(status, &span) {
            return Some(map_to_security_event(span, "API_ANOMALY"));
        }
    }

    // Flag SQL-like patterns in DB spans
    if let Some(query) = span.attributes.get("db.statement") {
        if contains_injection_pattern(query) {
            return Some(map_to_security_event(span, "SQL_INJECTION_ATTEMPT"));
        }
    }

    // Flag unusual auth failures
    if span.name.contains("authenticate") && span.status == SpanStatus::Error {
        return Some(map_to_security_event(span, "AUTH_FAILURE"));
    }

    None // Not security relevant — discard
}
```

### Injection to App (SDK)

Application teams add this once and never touch it again:

```python
# Python app — Django/FastAPI
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

provider = TracerProvider()
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="http://otel-collector:4317"))
)
trace.set_tracer_provider(provider)
# From here, Django/FastAPI auto-instrumentation captures everything
```

---

## Scalability

- OTel Collector is horizontally scalable — run multiple instances behind a load balancer
- Filter processor drops non-security spans before they hit AGRUS — keeps volume manageable
- At scale: OTel Collector cluster handles millions of spans/sec, only security-relevant ones (typically <1%) reach AGRUS
