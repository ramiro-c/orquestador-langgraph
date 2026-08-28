"""Persistencia de jobs en hashes Redis job:{id}."""

from __future__ import annotations

from datetime import datetime, timezone

JOB_KEY_PREFIX = "job:"

_EMPTY_FIELDS = {
    "error": "",
    "research_notes": "",
    "analysis": "",
    "output_path": "",
}


def _job_key(job_id: str) -> str:
    return f"{JOB_KEY_PREFIX}{job_id}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    def __init__(self, redis) -> None:
        self._redis = redis

    async def create(self, job_id: str, query: str) -> dict:
        """status=PENDING, empty error/notes/analysis/output_path, timestamps ISO."""
        now = _now_iso()
        data = {
            "status": "PENDING",
            "query": query,
            **_EMPTY_FIELDS,
            "created_at": now,
            "updated_at": now,
        }
        await self._redis.hset(_job_key(job_id), mapping=data)
        return dict(data)

    async def set_status(self, job_id: str, status: str, **fields) -> None:
        """Update status + optional fields; always refresh updated_at."""
        update = {"status": status, "updated_at": _now_iso(), **fields}
        await self._redis.hset(_job_key(job_id), mapping=update)

    async def set_failed(self, job_id: str, error: str) -> None:
        """ALWAYS writes status=FAILED and error (even if job missing? write the hash)."""
        await self._redis.hset(
            _job_key(job_id),
            mapping={"status": "FAILED", "error": error, "updated_at": _now_iso()},
        )

    async def get(self, job_id: str) -> dict | None:
        """None if missing."""
        data = await self._redis.hgetall(_job_key(job_id))
        if not data:
            return None
        return dict(data)
