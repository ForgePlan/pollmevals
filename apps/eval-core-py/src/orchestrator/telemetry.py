"""OTel bootstrap for the POLLMEVALS orchestrator.

Phase 2C — provides a single ``init_tracing`` entry point that configures a
``BatchSpanProcessor`` exporting to the OTel collector via OTLP/HTTP and
returns a ready-to-use ``Tracer``.

Usage::

    from src.orchestrator.telemetry import init_tracing
    tracer = init_tracing("pollmevals-orchestrator")

Idempotency guarantee: calling ``init_tracing`` multiple times with the same
service name returns a new ``Tracer`` handle but does NOT register a second
``TracerProvider``.  The global provider is set exactly once per process; all
subsequent calls just return ``trace.get_tracer(service_name)``.

Environment overrides (12-factor):
- ``OTEL_EXPORTER_OTLP_ENDPOINT``  — OTLP HTTP endpoint (default: http://localhost:4318)
- ``OTEL_SERVICE_NAME``            — service name override (overrides the argument)
"""

from __future__ import annotations

import logging
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)

_DEFAULT_OTLP_ENDPOINT = "http://localhost:4318"
_SERVICE_VERSION = "0.0.0"  # mirrors pyproject.toml [project].version

# Guard: flag set to True after the global provider is first configured.
_PROVIDER_INSTALLED = False


def init_tracing(
    service_name: str = "pollmevals-orchestrator",
    otlp_endpoint: str | None = None,
) -> trace.Tracer:
    """Configure the global OTel TracerProvider and return a named Tracer.

    Args:
        service_name: Logical service name embedded in every span's resource.
            Overridden by ``OTEL_SERVICE_NAME`` env var when set.
        otlp_endpoint: OTLP/HTTP collector endpoint.  Overridden by
            ``OTEL_EXPORTER_OTLP_ENDPOINT`` env var when set.  Defaults to
            ``http://localhost:4318`` (the Phase 2B collector config).

    Returns:
        An ``opentelemetry.trace.Tracer`` instance scoped to *service_name*.
    """
    global _PROVIDER_INSTALLED

    # Env var overrides (12-factor — env > explicit arg > built-in default).
    effective_name = os.environ.get("OTEL_SERVICE_NAME", service_name)
    effective_endpoint = (
        os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") or otlp_endpoint or _DEFAULT_OTLP_ENDPOINT
    )

    if not _PROVIDER_INSTALLED:
        resource = Resource.create(
            {
                "service.name": effective_name,
                "service.version": _SERVICE_VERSION,
                "service.namespace": "pollmevals",
            }
        )
        provider = TracerProvider(resource=resource)

        exporter = OTLPSpanExporter(
            endpoint=f"{effective_endpoint.rstrip('/')}/v1/traces",
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))

        trace.set_tracer_provider(provider)
        _PROVIDER_INSTALLED = True
        logger.debug(
            "OTel TracerProvider initialised: service=%s endpoint=%s",
            effective_name,
            effective_endpoint,
        )
    else:
        logger.debug(
            "OTel TracerProvider already installed — returning tracer for %s",
            effective_name,
        )

    return trace.get_tracer(effective_name)
