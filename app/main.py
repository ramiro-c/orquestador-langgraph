"""API HTTP: crea jobs, los corre en background y expone su estado."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

import redis.asyncio as redis_asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.jobs import JobStore
from app.observability import init_observability
from app.worker import resume_job, run_job
from config import REDIS_URL
from graph import build_graph

logger = logging.getLogger(__name__)

JobRunner = Callable[..., Awaitable[None]]

# asyncio solo garantiza que una task sigue viva mientras algo la referencia;
# asyncio.create_task(...) sin guardar el valor devuelto deja la task
# elegible para el GC en medio del run ("fire-and-forget" real). Guardamos
# una referencia fuerte acá y la soltamos en el done_callback.
_BACKGROUND_TASKS: set[asyncio.Task[Any]] = set()


def _on_background_task_done(task: asyncio.Task[Any]) -> None:
    _BACKGROUND_TASKS.discard(task)
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.error("Excepción no capturada en tarea de background: %s", exc, exc_info=exc)


def _spawn_background_task(coro: Awaitable[None]) -> asyncio.Task[Any]:
    task = asyncio.create_task(coro)
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_on_background_task_done)
    return task


class TaskCreate(BaseModel):
    query: str


def _build_graph_with_checkpointer(redis_saver_cls: type | None = None) -> Any:
    """Compila el grafo con RedisSaver.

    HITL depende de que el checkpoint persista en Redis: si RedisSaver no
    está disponible o falla su setup, la app NO debe degradar a un grafo sin
    HITL en silencio (eso escribiría ``outputs/`` sin aprobación humana).
    En su lugar, se relanza para que el lifespan falle rápido.
    """
    if redis_saver_cls is None:
        from langgraph.checkpoint.redis import RedisSaver

        redis_saver_cls = RedisSaver
    try:
        checkpointer = redis_saver_cls(redis_url=REDIS_URL)
        checkpointer.setup()
    except Exception as exc:
        raise RuntimeError(
            f"No se pudo inicializar RedisSaver para HITL persistente: {exc}"
        ) from exc
    return build_graph(checkpointer=checkpointer, enable_hitl=True)


def create_app(
    *,
    jobs: JobStore | None = None,
    graph: Any | None = None,
    run_job_fn: JobRunner = run_job,
    resume_job_fn: JobRunner = resume_job,
    init_observability_fn: Callable[[], None] = init_observability,
) -> FastAPI:
    """Fábrica de la app: en tests se inyectan ``jobs``/``graph`` fake, workers
    mockeados y un ``init_observability_fn`` no-op para que el TestClient no
    registre un tracer OTEL global real en cada test."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if jobs is not None:
            app.state.jobs = jobs
        else:
            redis = redis_asyncio.from_url(REDIS_URL, decode_responses=True)
            app.state.jobs = JobStore(redis)
        app.state.graph = graph if graph is not None else _build_graph_with_checkpointer()
        app.state.run_job_fn = run_job_fn
        app.state.resume_job_fn = resume_job_fn
        init_observability_fn()
        yield

    app = FastAPI(lifespan=lifespan)

    @app.post("/tasks", status_code=201)
    async def create_task(payload: TaskCreate) -> dict:
        job_id = str(uuid4())
        await app.state.jobs.create(job_id, payload.query)
        _spawn_background_task(
            app.state.run_job_fn(job_id, jobs=app.state.jobs, graph=app.state.graph)
        )
        return {"job_id": job_id, "status": "PENDING"}

    @app.get("/tasks/{job_id}")
    async def get_task(job_id: str) -> dict:
        job = await app.state.jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        return job

    @app.post("/tasks/{job_id}/approve")
    async def approve_task(job_id: str) -> dict:
        job = await app.state.jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        # claim_approval hace la transición AWAITING_APPROVAL -> RUNNING de
        # forma atómica: si dos approvals llegan concurrentes, solo uno
        # dispara resume_job (evita correr el grafo dos veces para el mismo
        # thread_id).
        claimed = await app.state.jobs.claim_approval(job_id)
        if not claimed:
            raise HTTPException(status_code=409, detail="job is not awaiting approval")
        _spawn_background_task(
            app.state.resume_job_fn(job_id, jobs=app.state.jobs, graph=app.state.graph)
        )
        return await app.state.jobs.get(job_id)

    return app


app = create_app()
