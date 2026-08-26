"""OpenRouter: un modelo por rol. El resto de providers no se toca acá."""

from __future__ import annotations

import sys
import types

from clients.factory import (
    DEFAULT_MODELS,
    OPENROUTER_ROLE_MODELS,
    ROLE_TEMPERATURE,
    _openrouter_model,
    build_chat_model,
    build_role_models,
)


def _inyectar_openrouter(monkeypatch, fake):
    modulo = types.ModuleType("langchain_openrouter")
    modulo.ChatOpenRouter = fake
    monkeypatch.setitem(sys.modules, "langchain_openrouter", modulo)


def _fake_chat():
    llamadas: list[dict] = []

    class _ChatFake:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            llamadas.append(kwargs)

    return _ChatFake, llamadas


def test_openrouter_asigna_modelo_por_rol(monkeypatch):
    fake, llamadas = _fake_chat()
    _inyectar_openrouter(monkeypatch, fake)

    build_chat_model(provider="openrouter", role="supervisor")
    build_chat_model(provider="openrouter", role="researcher")
    build_chat_model(provider="openrouter", role="analyst")

    assert llamadas[0]["model"] == OPENROUTER_ROLE_MODELS["supervisor"]
    assert llamadas[1]["model"] == OPENROUTER_ROLE_MODELS["researcher"]
    assert llamadas[2]["model"] == OPENROUTER_ROLE_MODELS["analyst"]
    assert llamadas[0]["model"] == "nvidia/nemotron-3-ultra-550b-a55b:free"
    assert llamadas[1]["model"] == "poolside/laguna-s-2.1:free"
    assert llamadas[2]["model"] == "minimax/minimax-m3:free"


def test_openrouter_temperatura_por_rol(monkeypatch):
    fake, llamadas = _fake_chat()
    _inyectar_openrouter(monkeypatch, fake)

    build_chat_model(provider="openrouter", role="supervisor")
    build_chat_model(provider="openrouter", role="researcher")
    build_chat_model(provider="openrouter", role="analyst")

    assert llamadas[0]["temperature"] == ROLE_TEMPERATURE["supervisor"] == 0.0
    assert llamadas[1]["temperature"] == ROLE_TEMPERATURE["researcher"] == 0.2
    assert llamadas[2]["temperature"] == ROLE_TEMPERATURE["analyst"] == 0.0


def test_openrouter_sin_rol_usa_default_supervisor(monkeypatch):
    fake, llamadas = _fake_chat()
    _inyectar_openrouter(monkeypatch, fake)

    build_chat_model(provider="openrouter")

    assert llamadas[0]["model"] == "nvidia/nemotron-3-ultra-550b-a55b:free"


def test_openrouter_model_explicito_pisa_el_rol(monkeypatch):
    fake, llamadas = _fake_chat()
    _inyectar_openrouter(monkeypatch, fake)

    build_chat_model(
        provider="openrouter",
        role="analyst",
        model="minimax/minimax-m3:free",
    )
    assert llamadas[0]["model"] == "minimax/minimax-m3:free"


def test_build_role_models_openrouter_son_tres_instancias(monkeypatch):
    fake, llamadas = _fake_chat()
    _inyectar_openrouter(monkeypatch, fake)

    models = build_role_models(provider="openrouter")

    assert set(models) == {"supervisor", "researcher", "analyst"}
    assert [c["model"] for c in llamadas] == [
        OPENROUTER_ROLE_MODELS["supervisor"],
        OPENROUTER_ROLE_MODELS["researcher"],
        OPENROUTER_ROLE_MODELS["analyst"],
    ]


def test_openrouter_model_helper():
    assert _openrouter_model("researcher", None) == "poolside/laguna-s-2.1:free"
    assert _openrouter_model("analyst", "otro") == "otro"


def test_gemini_envuelve_chat_para_apagar_afc(monkeypatch):
    fake, llamadas = _fake_chat()
    modulo = types.ModuleType("langchain_google_genai")
    modulo.ChatGoogleGenerativeAI = fake
    monkeypatch.setitem(sys.modules, "langchain_google_genai", modulo)

    modelo = build_chat_model(provider="gemini")

    assert type(modelo).__name__ == "_GeminiChat"
    assert isinstance(modelo, fake)
    assert llamadas[0]["model"] == DEFAULT_MODELS["gemini"]
