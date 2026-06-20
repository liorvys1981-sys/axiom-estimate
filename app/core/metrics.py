"""
In-process metrics store for axiom-estimate.

Tracks three counters and one histogram (bucketed latency) using only the
standard library — no Prometheus client dependency required.

Exposed via GET /metrics in Prometheus text-format (exposition format 0.0.4)
so that any Prometheus-compatible scraper (Prometheus, VictoriaMetrics,
Grafana Agent, Railway metrics, …) can consume it without extra config.

Thread-safety
─────────────
All mutations go through threading.Lock so the store is safe under Uvicorn's
default multi-threaded request handling.  For async-only workloads the lock
overhead is negligible.
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------
_lock = threading.Lock()

# Counters  ──────────────────────────────────────────────────────────────────
# Keyed by (method, path, status_code) → int
_request_counts: Dict[Tuple[str, str, int], int] = defaultdict(int)
_error_counts: Dict[Tuple[str, str, int], int] = defaultdict(int)

# Latency histogram  ─────────────────────────────────────────────────────────
# Keyed by (method, path) → list[float seconds]
_latency_samples: Dict[Tuple[str, str], List[float]] = defaultdict(list)

# Prometheus histogram bucket upper-bounds (seconds)
_BUCKETS: Tuple[float, ...] = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


# ---------------------------------------------------------------------------
# Public mutation API  (called by MetricsMiddleware)
# ---------------------------------------------------------------------------
def record_request(
    method: str,
    path: str,
    status_code: int,
    latency_seconds: float,
) -> None:
    """Record one completed HTTP request."""
    key = (method.upper(), path, status_code)
    lat_key = (method.upper(), path)
    with _lock:
        _request_counts[key] += 1
        if status_code >= 500:
            _error_counts[key] += 1
        _latency_samples[lat_key].append(latency_seconds)


# ---------------------------------------------------------------------------
# Prometheus text-format rendering
# ---------------------------------------------------------------------------
def _render_counter(
    name: str,
    help_text: str,
    data: Dict[Tuple[str, str, int], int],
) -> List[str]:
    lines: List[str] = [
        f"# HELP {name} {help_text}",
        f"# TYPE {name} counter",
    ]
    for (method, path, status), count in sorted(data.items()):
        labels = f'method="{method}",path="{path}",status="{status}"'
        lines.append(f"{name}{{{labels}}} {count}")
    return lines


def _render_histogram(
    name: str,
    help_text: str,
    data: Dict[Tuple[str, str], List[float]],
) -> List[str]:
    lines: List[str] = [
        f"# HELP {name} {help_text}",
        f"# TYPE {name} histogram",
    ]
    for (method, path), samples in sorted(data.items()):
        labels_base = f'method="{method}",path="{path}"'
        total = sum(samples)
        count = len(samples)

        # Bucket counts (cumulative)
        for le in _BUCKETS:
            bucket_count = sum(1 for s in samples if s <= le)
            lines.append(
                f'{name}_bucket{{{labels_base},le="{le}"}} {bucket_count}'
            )
        lines.append(f'{name}_bucket{{{labels_base},le="+Inf"}} {count}')
        lines.append(f"{name}_sum{{{labels_base}}} {total:.6f}")
        lines.append(f"{name}_count{{{labels_base}}} {count}")
    return lines


def generate_metrics_text() -> str:
    """
    Return a Prometheus-compatible text exposition of all current metrics.
    Safe to call from any thread.
    """
    with _lock:
        req_snapshot = dict(_request_counts)
        err_snapshot = dict(_error_counts)
        lat_snapshot = {k: list(v) for k, v in _latency_samples.items()}

    lines: List[str] = []

    lines += _render_counter(
        "http_requests_total",
        "Total number of HTTP requests processed.",
        req_snapshot,
    )
    lines += _render_counter(
        "http_errors_total",
        "Total number of HTTP 5xx responses.",
        err_snapshot,
    )
    lines += _render_histogram(
        "http_request_duration_seconds",
        "HTTP request latency in seconds.",
        lat_snapshot,
    )

    # Trailing newline required by Prometheus exposition format
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Convenience: total aggregates (used by /health/ready summary)
# ---------------------------------------------------------------------------
def total_requests() -> int:
    with _lock:
        return sum(_request_counts.values())


def total_errors() -> int:
    with _lock:
        return sum(_error_counts.values())


def p99_latency_seconds() -> float:
    """Return the 99th-percentile latency across all paths, or 0.0 if no data."""
    with _lock:
        all_samples: List[float] = []
        for samples in _latency_samples.values():
            all_samples.extend(samples)
    if not all_samples:
        return 0.0
    all_samples.sort()
    idx = max(0, int(len(all_samples) * 0.99) - 1)
    return all_samples[idx]
