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


class TaskCreate(BaseModel):
    query: str


def _build_graph_with_checkpointer() -> Any:
    """Compila el grafo con RedisSaver si hay Redis disponible; si no, sin HITL persistente."""
    try:
        from langgraph.checkpoint.redis import RedisSaver

        checkpointer = RedisSaver(redis_url=REDIS_URL)
        checkpointer.setup()
        return build_graph(checkpointer=checkpointer, enable_hitl=True)
    except Exception as exc:  # noqa: BLE001 - Redis caído no debe tumbar la API
        logger.warning("RedisSaver no disponible (%s); el grafo corre sin HITL persistente.", exc)
        return build_graph()


def create_app(
    *,
    jobs: JobStore | None = None,
    graph: Any | None = None,
    run_job_fn: JobRunner = run_job,
    resume_job_fn: JobRunner = resume_job,
) -> FastAPI:
    """Fábrica de la app: en tests se inyectan ``jobs``/``graph`` fake y workers mockeados."""

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
        init_observability()
        yield

    app = FastAPI(lifespan=lifespan)

    @app.post("/tasks", status_code=201)
    async def create_task(payload: TaskCreate) -> dict:
        job_id = str(uuid4())
        await app.state.jobs.create(job_id, payload.query)
        asyncio.create_task(
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
        if job.get("status") != "AWAITING_APPROVAL":
            raise HTTPException(status_code=409, detail="job is not awaiting approval")
        asyncio.create_task(
            app.state.resume_job_fn(job_id, jobs=app.state.jobs, graph=app.state.graph)
        )
        return job

    return app


app = create_app()
