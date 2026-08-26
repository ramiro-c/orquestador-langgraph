"""Factory multi-proveedor de modelos de chat (mismo patrón que pre-entrega-5)."""

from clients.factory import build_chat_model, build_role_models

__all__ = ["build_chat_model", "build_role_models"]
