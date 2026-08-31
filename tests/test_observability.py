"""init_observability no debe tumbar la API si Phoenix está caído."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import app.observability as observability


def test_init_observability_loguea_warning_y_no_lanza_si_phoenix_falla(monkeypatch, caplog):
    def _boom(**_kwargs):
        raise RuntimeError("phoenix caído")

    monkeypatch.setattr(observability, "register", _boom)

    with caplog.at_level(logging.WARNING):
        observability.init_observability()  # no debe lanzar

    assert any("phoenix" in record.message.lower() for record in caplog.records)


def test_init_observability_usa_batch_span_processor_en_produccion(monkeypatch):
    """SimpleSpanProcessor exporta síncrono por span: en producción hace falta
    BatchSpanProcessor (register(batch=True)) para no bloquear cada request."""
    register_mock = MagicMock()
    monkeypatch.setattr(observability, "register", register_mock)
    monkeypatch.setattr(observability, "LangChainInstrumentor", MagicMock())

    observability.init_observability()

    assert register_mock.call_args.kwargs.get("batch") is True
