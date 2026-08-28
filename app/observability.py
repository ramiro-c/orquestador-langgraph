"""Tracing OTEL de LangChain vía Phoenix, sin bloquear el arranque de la API."""

from __future__ import annotations

import logging

from openinference.instrumentation.langchain import LangChainInstrumentor
from phoenix.otel import register

from config import PHOENIX_COLLECTOR_ENDPOINT

logger = logging.getLogger(__name__)


def init_observability() -> None:
    """Registra el tracer de Phoenix e instrumenta LangChain.

    Si Phoenix está caído o falla el registro, se loguea un warning y se
    continúa: la API no debe morir por falta de observabilidad.
    """
    try:
        register(project_name="orquestador-langgraph", endpoint=PHOENIX_COLLECTOR_ENDPOINT)
        LangChainInstrumentor().instrument()
    except Exception as exc:  # noqa: BLE001 - Phoenix caído no debe tumbar la API
        logger.warning("No se pudo inicializar Phoenix (%s); continuando sin tracing.", exc)
