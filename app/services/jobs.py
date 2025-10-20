from __future__ import annotations
import asyncio, uuid, pathlib
from typing import Any, Dict, Optional
import httpx

from app.core.config import settings
from app.core.http import hf_get

DATA_DIR = pathlib.Path("data")
DATA_DIR.mkdir(exist_ok=True)

class JobStatus:
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class JobRecord(Dict[str, Any]):
    """Minimal job record; holds upstream id + last payload."""
    pass

class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._lock = asyncio.Lock()

    async def create(self, upstream_jobset_id: str, kind: str, input_params: dict) -> str:
        local_id = str(uuid.uuid4())
        async with self._lock:
            self._jobs[local_id] = {
                "id": local_id,
                "kind": kind,
                "upstream_id": upstream_jobset_id,
                "status": JobStatus.QUEUED,
                "payload": None,
                "input_params": input_params,
            }
        return local_id

    async def update(self, local_id: str, payload: dict) -> None:
        async with self._lock:
            if local_id in self._jobs:
                self._jobs[local_id]["payload"] = payload
                # try to infer status from upstream payload
                jobs = payload.get("jobs", [])
                if any(j.get("status") == "failed" for j in jobs):
                    self._jobs[local_id]["status"] = JobStatus.FAILED
                elif any(j.get("status") == "completed" for j in jobs):
                    self._jobs[local_id]["status"] = JobStatus.COMPLETED
                elif any(j.get("status") == "running" for j in jobs):
                    self._jobs[local_id]["status"] = JobStatus.RUNNING
                else:
                    self._jobs[local_id]["status"] = JobStatus.QUEUED

    async def get(self, local_id: str) -> Optional[JobRecord]:
        async with self._lock:
            return self._jobs.get(local_id)

store = JobStore()

async def poll_upstream(local_id: str):
    """Poll platform /v1/job-sets/{id} until complete; save assets if enabled."""
    job = await store.get(local_id)
    if not job: return
    upstream_id = job["upstream_id"]

    while True:
        try:
            res = await hf_get(f"/v1/job-sets/{upstream_id}")
            payload = res.json()
            await store.update(local_id, payload)

            status = (await store.get(local_id))["status"]
            if status in ("completed", "failed"):
                if status == "completed" and settings.SAVE_RESULTS:
                    await _download_assets(payload)
                break
            await asyncio.sleep(1.2)
        except httpx.HTTPError:
            await asyncio.sleep(2.0)

async def _download_assets(payload: dict):
    # Downloads 'min' and 'raw' URLs if present
    jobs = payload.get("jobs", [])
    for j in jobs:
        results = j.get("results") or {}
        for name, info in results.items():
            url = info.get("url")
            if not url: continue
            out = DATA_DIR / f"{payload['id']}_{name}.{('webp' if url.endswith('.webp') else url.split('.')[-1])}"
            async with httpx.AsyncClient() as client:
                r = await client.get(url, timeout=60)
                r.raise_for_status()
                out.write_bytes(r.content)
