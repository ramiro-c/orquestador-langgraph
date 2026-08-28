"""Worker: invoca el grafo en un hilo y refleja el progreso en Redis."""

from __future__ import annotations

import uuid

import fakeredis.aioredis
import pytest
from langgraph.checkpoint.memory import InMemorySaver

from agents.writer import output_path_for
from app.jobs import JobStore
from app.worker import resume_job, run_job
from graph import build_graph

QUERY = "¿Qué se dice de LangGraph?"


@pytest.fixture
async def jobs():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield JobStore(redis)
    await redis.aclose()


def _job_id() -> str:
    return str(uuid.uuid4())


def _dummy_nodes(writer_calls: list, *, writer_output_path: str | None = None):
    def supervisor(_state):
        return {
            "next_agent": "FINISH",
            "last_agent": "supervisor",
            "research_notes": "notas-x",
            "analysis": "analisis-y",
        }

    def researcher(_state):
        return {}

    def analyst(_state):
        return {}

    def writer(state):
        writer_calls.append(state)
        result = {"last_agent": "writer"}
        if writer_output_path is not None:
            result["output_path"] = writer_output_path
        return result

    return supervisor, researcher, analyst, writer


@pytest.mark.anyio
async def test_run_job_exito_usa_output_path_for_cuando_el_estado_no_lo_trae(jobs):
    job_id = _job_id()
    supervisor, researcher, analyst, writer = _dummy_nodes([])
    graph = build_graph(
        supervisor=supervisor,
        researcher=researcher,
        analyst=analyst,
        writer=writer,
        retry_policy=None,
    )
    await jobs.create(job_id, QUERY)

    await run_job(job_id, jobs=jobs, graph=graph)

    job = await jobs.get(job_id)
    assert job["status"] == "DONE"
    assert job["output_path"] == str(output_path_for(QUERY))
    assert job["research_notes"] == "notas-x"
    assert job["analysis"] == "analisis-y"


@pytest.mark.anyio
async def test_run_job_fallo_marca_failed_con_el_error(jobs):
    job_id = _job_id()

    def supervisor(_state):
        raise RuntimeError("boom")

    graph = build_graph(
        supervisor=supervisor,
        researcher=lambda s: {},
        analyst=lambda s: {},
        writer=lambda s: {"last_agent": "writer"},
        retry_policy=None,
    )
    await jobs.create(job_id, QUERY)

    await run_job(job_id, jobs=jobs, graph=graph)

    job = await jobs.get(job_id)
    assert job["status"] == "FAILED"
    assert "boom" in job["error"]


@pytest.mark.anyio
async def test_run_job_pausa_awaiting_approval_y_resume_job_marca_done(jobs, tmp_path):
    job_id = _job_id()
    writer_calls: list = []
    custom_output = str(tmp_path / "custom.md")
    supervisor, researcher, analyst, writer = _dummy_nodes(
        writer_calls, writer_output_path=custom_output
    )
    graph = build_graph(
        supervisor=supervisor,
        researcher=researcher,
        analyst=analyst,
        writer=writer,
        retry_policy=None,
        checkpointer=InMemorySaver(),
        enable_hitl=True,
    )
    await jobs.create(job_id, QUERY)

    await run_job(job_id, jobs=jobs, graph=graph)

    paused = await jobs.get(job_id)
    assert paused["status"] == "AWAITING_APPROVAL"
    assert paused["research_notes"] == "notas-x"
    assert paused["analysis"] == "analisis-y"
    assert writer_calls == []

    await resume_job(job_id, jobs=jobs, graph=graph)

    done = await jobs.get(job_id)
    assert done["status"] == "DONE"
    assert done["output_path"] == custom_output
    assert writer_calls != []
