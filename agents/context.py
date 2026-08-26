"""Helpers para aislar el contexto que ve cada especialista."""

from __future__ import annotations

from typing import Any


def message_text(message: Any) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
        return "\n".join(p for p in parts if p)
    return str(content)


def user_query(messages: list) -> str:
    """Primera pregunta humana: la consulta original, no el ruido del grafo."""
    for message in messages:
        if getattr(message, "type", None) == "human":
            return message_text(message)
    if messages:
        return message_text(messages[0])
    return ""


def last_ai_text(messages: list) -> str:
    """Última respuesta del LLM sin tool_calls (el brief final del ReAct)."""
    for message in reversed(messages):
        if getattr(message, "type", None) != "ai":
            continue
        if getattr(message, "tool_calls", None):
            continue
        return message_text(message)
    return message_text(messages[-1]) if messages else ""
