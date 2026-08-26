"""Factory multi-proveedor (mismo wiring que pre-entrega-5).

Con ``LLM_PROVIDER=openrouter`` cada rol del grafo usa un modelo distinto:
supervisor rutea, researcher busca, analyst razona. Los otros providers
comparten un solo modelo (``DEFAULT_MODELS``).
"""

from __future__ import annotations

from typing import cast

from langchain_core.language_models import BaseChatModel

from config import (
    ANTHROPIC_API_KEY,
    GEMINI_API_KEY,
    LLM_PROVIDER,
    OPENAI_API_KEY,
)
from schemas import ProviderName, RoleName

DEFAULT_MODELS: dict[str, str] = {
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-latest",
    "openrouter": "nvidia/nemotron-3-ultra-550b-a55b:free",
}

# OpenRouter :free — un modelo por rol.
# Laguna S 2.1 no tiene response_format, así que no
# rutea (el supervisor usa with_structured_output).
# supervisor: Nemotron 3 Ultra. Ruteo corto; el más rápido; structured output.
# researcher: Laguna S 2.1. Agentic + tools (Tavily); 256K ctx.
# analyst: MiniMax M3. Mejor razonamiento/IF para contar evidencia.
OPENROUTER_ROLE_MODELS: dict[RoleName, str] = {
    "supervisor": "nvidia/nemotron-3-ultra-550b-a55b:free",
    "researcher": "poolside/laguna-s-2.1:free",
    "analyst": "minimax/minimax-m3:free",
}

ROLE_TEMPERATURE: dict[RoleName, float] = {
    "supervisor": 0.0,
    "researcher": 0.2,
    "analyst": 0.0,
}


def _normalize_provider(provider: str) -> ProviderName:
    value = provider.strip().lower()
    if value not in {"gemini", "openai", "anthropic", "openrouter"}:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")
    return cast(ProviderName, value)


def _openrouter_model(role: RoleName | None, model: str | None) -> str:
    if model:
        return model
    if role:
        return OPENROUTER_ROLE_MODELS[role]
    return DEFAULT_MODELS["openrouter"]


def build_chat_model(
    provider: str | None = None,
    temperature: float | None = None,
    *,
    role: RoleName | None = None,
    model: str | None = None,
) -> BaseChatModel:
    resolved = _normalize_provider(provider or LLM_PROVIDER)
    if temperature is None:
        temperature = ROLE_TEMPERATURE.get(role, 0.2) if role else 0.2

    if resolved == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            api_key=OPENAI_API_KEY,
            model=model or DEFAULT_MODELS["openai"],
            temperature=temperature,
        )

    if resolved == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            api_key=ANTHROPIC_API_KEY,
            model=model or DEFAULT_MODELS["anthropic"],
            temperature=temperature,
        )

    if resolved == "gemini":
        from google.genai.types import AutomaticFunctionCallingConfig
        from langchain_google_genai import ChatGoogleGenerativeAI

        # create_agent ya ejecuta las tools. El AFC de Gemini avisa (y puede
        # pelearse con el ReAct) si Models.generate_content auto-llama funciones.
        class _GeminiChat(ChatGoogleGenerativeAI):
            def _prepare_request(self, *args, **kwargs):
                request = super()._prepare_request(*args, **kwargs)
                config = request.get("config")
                if config is not None:
                    config.automatic_function_calling = AutomaticFunctionCallingConfig(
                        disable=True
                    )
                return request

        return _GeminiChat(
            api_key=GEMINI_API_KEY,
            model=model or DEFAULT_MODELS["gemini"],
            temperature=temperature,
        )

    if resolved == "openrouter":
        from langchain_openrouter import ChatOpenRouter

        return ChatOpenRouter(
            model=_openrouter_model(role, model),
            temperature=temperature,
        )

    raise ValueError(f"Unsupported provider: {resolved}")


def build_role_models(
    provider: str | None = None,
) -> dict[RoleName, BaseChatModel]:
    """Tres LLMs listos para el grafo. OpenRouter los diferencia; el resto no."""
    resolved = _normalize_provider(provider or LLM_PROVIDER)
    if resolved == "openrouter":
        return {
            "supervisor": build_chat_model(provider="openrouter", role="supervisor"),
            "researcher": build_chat_model(provider="openrouter", role="researcher"),
            "analyst": build_chat_model(provider="openrouter", role="analyst"),
        }
    llm = build_chat_model(provider=resolved)
    return {"supervisor": llm, "researcher": llm, "analyst": llm}
