"""Runner de background: invoca el grafo en un hilo y actualiza el job en Redis."""

from __future__ import annotations

import asyncio

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agents.writer import output_path_for
from app.jobs import JobStore
from graph import invoke_config
from state import initial_fields


def _config(job_id: str) -> dict:
    return {**invoke_config(), "configurable": {"thread_id": job_id}}


async def _apply_result(job_id: str, query: str, jobs: JobStore, result: dict) -> None:
    if "__interrupt__" in result:
        await jobs.set_status(
            job_id,
            "AWAITING_APPROVAL",
            research_notes=result.get("research_notes") or "",
            analysis=result.get("analysis") or "",
        )
        return
    output_path = result.get("output_path") or str(output_path_for(query))
    await jobs.set_status(
        job_id,
        "DONE",
        research_notes=result.get("research_notes") or "",
        analysis=result.get("analysis") or "",
        output_path=output_path,
    )


async def run_job(job_id: str, *, jobs: JobStore, graph) -> None:
    """PENDING→RUNNING, invoca el grafo, y refleja pausa/fin/error en el job."""
    job = await jobs.get(job_id)
    query = (job or {}).get("query", "")
    await jobs.set_status(job_id, "RUNNING")
    try:
        result = await asyncio.to_thread(
            graph.invoke,
            {**initial_fields(), "messages": [HumanMessage(content=query)]},
            _config(job_id),
        )
    except Exception as exc:  # noqa: BLE001 - cualquier falla del grafo marca FAILED
        await jobs.set_failed(job_id, str(exc))
        return
    await _apply_result(job_id, query, jobs, result)


async def resume_job(job_id: str, *, jobs: JobStore, graph) -> None:
    """Retoma un job pausado en ``approval`` con ``Command(resume=True)``."""
    job = await jobs.get(job_id)
    query = (job or {}).get("query", "")
    await jobs.set_status(job_id, "RUNNING")
    try:
        result = await asyncio.to_thread(graph.invoke, Command(resume=True), _config(job_id))
    except Exception as exc:  # noqa: BLE001
        await jobs.set_failed(job_id, str(exc))
        return
    await _apply_result(job_id, query, jobs, result)
