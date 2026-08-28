"""JobStore: hashes Redis job:{id} con fakeredis async."""

from __future__ import annotations

from datetime import datetime

import fakeredis.aioredis
import pytest

from app.jobs import JobStore


@pytest.fixture
async def store():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield JobStore(redis)
    await redis.aclose()


@pytest.mark.anyio
async def test_create_sets_pending_with_empty_fields(store):
    job = await store.create("job-1", "Redis vs Kafka")

    assert job["status"] == "PENDING"
    assert job["query"] == "Redis vs Kafka"
    assert job["error"] == ""
    assert job["research_notes"] == ""
    assert job["analysis"] == ""
    assert job["output_path"] == ""
    datetime.fromisoformat(job["created_at"])
    datetime.fromisoformat(job["updated_at"])


@pytest.mark.anyio
async def test_get_missing_returns_none(store):
    assert await store.get("missing") is None


@pytest.mark.anyio
async def test_set_status_updates_status_and_optional_fields(store):
    await store.create("job-2", "LangGraph overview")
    created = await store.get("job-2")

    await store.set_status(
        "job-2",
        "RUNNING",
        research_notes="notes",
        analysis="positive",
        output_path="outputs/langgraph.md",
    )
    updated = await store.get("job-2")

    assert updated["status"] == "RUNNING"
    assert updated["research_notes"] == "notes"
    assert updated["analysis"] == "positive"
    assert updated["output_path"] == "outputs/langgraph.md"
    assert updated["query"] == "LangGraph overview"
    assert updated["created_at"] == created["created_at"]
    assert updated["updated_at"] >= created["updated_at"]


@pytest.mark.anyio
async def test_set_failed_after_create_simulates_worker_exception(store):
    await store.create("job-3", "¿Qué se dice de LangGraph?")

    await store.set_failed("job-3", "RuntimeError: Provider returned error")

    job = await store.get("job-3")
    assert job is not None
    assert job["status"] == "FAILED"
    assert job["error"] == "RuntimeError: Provider returned error"
    assert job["query"] == "¿Qué se dice de LangGraph?"


@pytest.mark.anyio
async def test_set_failed_writes_hash_even_when_job_missing(store):
    await store.set_failed("orphan", "boom")

    job = await store.get("orphan")
    assert job is not None
    assert job["status"] == "FAILED"
    assert job["error"] == "boom"


@pytest.mark.anyio
async def test_claim_approval_transiciona_a_running_y_devuelve_true(store):
    await store.create("job-claim-1", "Redis vs Kafka")
    await store.set_status("job-claim-1", "AWAITING_APPROVAL")

    claimed = await store.claim_approval("job-claim-1")

    assert claimed is True
    job = await store.get("job-claim-1")
    assert job["status"] == "RUNNING"


@pytest.mark.anyio
async def test_claim_approval_devuelve_false_si_no_esta_awaiting_approval(store):
    await store.create("job-claim-2", "Redis vs Kafka")

    claimed = await store.claim_approval("job-claim-2")

    assert claimed is False
    job = await store.get("job-claim-2")
    assert job["status"] == "PENDING"


@pytest.mark.anyio
async def test_claim_approval_doble_approve_solo_uno_gana(store):
    """Simula el double-approve race: solo la primera llamada debe ganar."""
    await store.create("job-claim-3", "Redis vs Kafka")
    await store.set_status("job-claim-3", "AWAITING_APPROVAL")

    primero = await store.claim_approval("job-claim-3")
    segundo = await store.claim_approval("job-claim-3")

    assert primero is True
    assert segundo is False
