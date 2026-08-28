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
