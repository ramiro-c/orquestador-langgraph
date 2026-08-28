"""API HTTP: POST/GET /tasks y approve, con JobStore fake y worker mockeado."""

from __future__ import annotations

import asyncio
import logging
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
        init_observability_fn=lambda: None,
    )
    with TestClient(app) as test_client:
        yield test_client


def test_create_app_usa_init_observability_fn_inyectada(jobs):
    """create_app debe permitir inyectar init_observability_fn para que los
    tests no registren un tracer OTEL global real (default: init_observability)."""
    calls: list[bool] = []

    app = create_app(
        jobs=jobs,
        graph=object(),
        init_observability_fn=lambda: calls.append(True),
    )

    with TestClient(app):
        pass

    assert calls == [True]


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


def test_create_task_mantiene_referencia_fuerte_a_la_background_task(client, run_job_mock):
    """No debe hacerse create_task sin guardar la referencia (el GC podría
    cancelar la tarea a mitad de camino)."""
    import app.main as main_module

    async def _lento(*_args, **_kwargs):
        await asyncio.sleep(0.2)

    run_job_mock.side_effect = _lento

    response = client.post("/tasks", json={"query": "Redis vs Kafka"})
    assert response.status_code == 201

    assert len(main_module._BACKGROUND_TASKS) >= 1
    _wait_until(lambda: len(main_module._BACKGROUND_TASKS) == 0, timeout=1.0)


def test_background_task_que_lanza_excepcion_no_capturada_se_loguea(
    client, run_job_mock, caplog
):
    """Si un run_job "crudo" (sin el try/except de C2) explota igual, el
    done_callback propio de app.main debe loguearlo en vez de perderlo en
    silencio (y no debe tumbar el proceso)."""
    run_job_mock.side_effect = RuntimeError("explota sin capturar")

    with caplog.at_level(logging.ERROR, logger="app.main"):
        response = client.post("/tasks", json={"query": "Redis vs Kafka"})
        assert response.status_code == 201
        _wait_until(
            lambda: any(
                r.name == "app.main" and "explota sin capturar" in r.getMessage()
                for r in caplog.records
            )
        )


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


def test_approve_devuelve_409_si_ya_fue_reclamado_por_otro_approve(
    client, run_job_mock, resume_job_mock
):
    """Double-approve race: la segunda llamada (aunque el job siga viéndose
    AWAITING_APPROVAL un instante) no debe disparar un segundo resume_job."""

    async def _pausar(job_id, *, jobs, graph):
        await jobs.set_status(job_id, "AWAITING_APPROVAL")

    run_job_mock.side_effect = _pausar
    created = client.post("/tasks", json={"query": "Redis vs Kafka"})
    job_id = created.json()["job_id"]
    _wait_until(lambda: client.get(f"/tasks/{job_id}").json()["status"] == "AWAITING_APPROVAL")

    first = client.post(f"/tasks/{job_id}/approve")
    second = client.post(f"/tasks/{job_id}/approve")

    assert first.status_code == 200
    assert second.status_code == 409
    _wait_until(lambda: resume_job_mock.call_count >= 1)
    assert resume_job_mock.call_count == 1
