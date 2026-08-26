"""Configuración de la pre-entrega 6: orquestador multi-agente.

Patrón de pre-entrega-5: load_dotenv() al importar. El LLM se elige con
LLM_PROVIDER (default gemini / Vertex). Tavily lee TAVILY_API_KEY.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


def _env_str(name: str, default: str) -> str:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip()


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

LLM_PROVIDER = _env_str("LLM_PROVIDER", "gemini")

GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")

# Supersteps del grafo padre (supervisor + especialistas). El ReAct interno
# de cada create_agent no consume este límite.
RECURSION_LIMIT = 20
