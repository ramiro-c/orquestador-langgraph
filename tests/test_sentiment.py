"""Tests del cómputo de sentimiento (sin LLM ni red)."""

from __future__ import annotations

from agents.analyst_agent import compute_sentiment_score


def test_sin_menciones_es_neutral_con_error():
    out = compute_sentiment_score(0, 0, 0)
    assert out["label"] == "neutral"
    assert out["score"] == 0.0
    assert out["error"] == "sin evidencia"


def test_mayoria_positiva():
    out = compute_sentiment_score(8, 1, 1)
    assert out["label"] == "positivo"
    assert out["score"] == 0.7


def test_mayoria_negativa():
    out = compute_sentiment_score(1, 8, 1)
    assert out["label"] == "negativo"
    assert out["score"] == -0.7


def test_empate_es_neutral():
    out = compute_sentiment_score(3, 3, 4)
    assert out["label"] == "neutral"
    assert out["score"] == 0.0


def test_conteos_negativos_error():
    out = compute_sentiment_score(-1, 0, 0)
    assert "error" in out
