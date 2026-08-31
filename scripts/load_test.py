#!/usr/bin/env python3
"""Cinco POST /tasks concurrentes con temas distintos; poll GET hasta estado terminal."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time

import httpx

TERMINAL_STATUSES = frozenset({"DONE", "FAILED", "AWAITING_APPROVAL"})

QUERIES = (
    "¿Qué es LangGraph y para qué sirve en producción?",
    "Comparativa entre CrewAI y LangGraph para equipos chicos",
    "Tendencias de agentes multi-agente en 2026",
    "Sentimiento de la comunidad sobre RAG con LangChain",
    "Casos de uso de human-in-the-loop en pipelines de research",
)


async def _create_task(client: httpx.AsyncClient, query: str) -> str:
    response = await client.post("/tasks", json={"query": query})
    response.raise_for_status()
    payload = response.json()
    return payload["job_id"]


async def _poll_until_terminal(
    client: httpx.AsyncClient,
    job_id: str,
    *,
    timeout: float,
    interval: float,
) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = await client.get(f"/tasks/{job_id}")
        response.raise_for_status()
        job = response.json()
        status = job.get("status", "")
        print(f"{job_id}  {status}", flush=True)
        if status in TERMINAL_STATUSES:
            return job
        await asyncio.sleep(interval)
    raise TimeoutError(f"timeout after {timeout}s")


async def _run_query(
    client: httpx.AsyncClient,
    query: str,
    *,
    timeout: float,
    interval: float,
) -> None:
    job_id = await _create_task(client, query)
    print(f"{job_id}  PENDING  ({query[:48]}…)", flush=True)
    try:
        await _poll_until_terminal(client, job_id, timeout=timeout, interval=interval)
    except TimeoutError:
        print(f"{job_id}  TIMEOUT", flush=True)


async def _main_async(base_url: str, timeout: float, interval: float) -> int:
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        await asyncio.gather(
            *(
                _run_query(client, query, timeout=timeout, interval=interval)
                for query in QUERIES
            )
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load test de POST /tasks concurrentes.")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("API_BASE_URL", "http://127.0.0.1:8000"),
        help="URL base de la API (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Segundos máximos de poll por job (default: 300)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Segundos entre polls (default: 2)",
    )
    args = parser.parse_args(argv)

    try:
        return asyncio.run(_main_async(args.base_url, args.timeout, args.interval))
    except httpx.HTTPError as exc:
        print(f"HTTP error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
