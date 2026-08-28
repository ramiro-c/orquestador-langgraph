"""API HTTP: POST/GET /tasks y approve, con JobStore fake y worker mockeado."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient

from app.jobs import JobStore
from app.main import create_app


def _wait_until(predicate, *, timeout: float = 1.0, interval: float = 0.01) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(interval)
    raise AssertionError("condición no se cumplió a tiempo")


@pytest.fixture
def jobs():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    return JobStore(redis)


@pytest.fixture
def run_job_mock():
    return AsyncMock()


@pytest.fixture
def resume_job_mock():
    return AsyncMock()


@pytest.fixture
def client(jobs, run_job_mock, resume_job_mock):
    app = create_app(
        jobs=jobs,
        graph=object(),
        run_job_fn=run_job_mock,
        resume_job_fn=resume_job_mock,
    )
    with TestClient(app) as test_client:
        yield test_client


def test_post_tasks_devuelve_201_con_job_id_y_pending_sin_esperar_al_worker(
    client, run_job_mock
):
    async def _lento(*_args, **_kwargs):
        import asyncio

        await asyncio.sleep(0.3)

    run_job_mock.side_effect = _lento

    start = time.monotonic()
    response = client.post("/tasks", json={"query": "¿Qué se dice de LangGraph?"})
    elapsed = time.monotonic() - start

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["job_id"]
    assert elapsed < 0.3


def test_get_tasks_devuelve_404_si_no_existe(client):
    response = client.get("/tasks/no-existe")
    assert response.status_code == 404


def test_get_tasks_devuelve_200_despues_de_crear(client):
    created = client.post("/tasks", json={"query": "Redis vs Kafka"})
    job_id = created.json()["job_id"]

    response = client.get(f"/tasks/{job_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["query"] == "Redis vs Kafka"


def test_approve_devuelve_409_si_no_esta_awaiting_approval(client):
    created = client.post("/tasks", json={"query": "Redis vs Kafka"})
    job_id = created.json()["job_id"]

    response = client.post(f"/tasks/{job_id}/approve")

    assert response.status_code == 409


def test_approve_devuelve_404_si_no_existe(client):
    response = client.post("/tasks/no-existe/approve")

    assert response.status_code == 404


def test_approve_devuelve_200_y_dispara_resume_job_si_esta_awaiting_approval(
    client, jobs, run_job_mock, resume_job_mock
):
    async def _pausar(job_id, *, jobs, graph):
        await jobs.set_status(job_id, "AWAITING_APPROVAL")

    run_job_mock.side_effect = _pausar
    created = client.post("/tasks", json={"query": "Redis vs Kafka"})
    job_id = created.json()["job_id"]
    _wait_until(lambda: client.get(f"/tasks/{job_id}").json()["status"] == "AWAITING_APPROVAL")

    response = client.post(f"/tasks/{job_id}/approve")

    assert response.status_code == 200
    _wait_until(lambda: resume_job_mock.called)
    assert resume_job_mock.call_args.args[0] == job_id
