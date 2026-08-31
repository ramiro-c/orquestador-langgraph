"""``_build_graph_with_checkpointer`` debe fallar fuerte, nunca degradar sin HITL."""

from __future__ import annotations

import pytest

import app.main as main_module


class _BoomRedisSaver:
    def __init__(self, *_args, **_kwargs) -> None:
        raise RuntimeError("redis caído")

    def setup(self) -> None:  # pragma: no cover - no debería llegar acá
        pass


def test_build_graph_with_checkpointer_relanza_si_redis_saver_falla():
    with pytest.raises(RuntimeError):
        main_module._build_graph_with_checkpointer(redis_saver_cls=_BoomRedisSaver)


def test_build_graph_with_checkpointer_relanza_si_setup_falla():
    class _SetupBoom:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def setup(self) -> None:
            raise RuntimeError("setup falló")

    with pytest.raises(RuntimeError):
        main_module._build_graph_with_checkpointer(redis_saver_cls=_SetupBoom)


def test_create_app_produccion_falla_al_levantar_si_redis_saver_falla(monkeypatch):
    """Camino de producción (sin jobs/graph inyectados): el lifespan debe fallar,
    nunca servir jobs sin HITL."""
    from fastapi.testclient import TestClient

    monkeypatch.setattr(
        main_module,
        "_build_graph_with_checkpointer",
        lambda: (_ for _ in ()).throw(RuntimeError("redis caído")),
    )

    app = main_module.create_app()

    with pytest.raises(Exception):
        with TestClient(app):
            pass
