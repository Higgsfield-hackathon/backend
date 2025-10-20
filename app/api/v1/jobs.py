from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from app.core.security import require_bearer
from app.services.jobs import store

router = APIRouter(dependencies=[Depends(require_bearer)])

@router.get("/jobs/{id}")
async def get_job(id: str):
    job = await store.get(id)
    if not job:
        raise HTTPException(404, "job not found")
    return job

@router.get("/jobs/{id}/result")
async def job_result(id: str):
    job = await store.get(id)
    if not job:
        raise HTTPException(404, "job not found")
    if job["status"] != "completed":
        # 425 Too Early is nice for “not ready yet”
        raise HTTPException(425, "job not completed yet")
    payload = job.get("payload") or {}
    jobs = (payload.get("jobs") or [])
    results = (jobs[0].get("results") if jobs else {}) or {}
    out = {
        "min": results.get("min", {}).get("url"),
        "raw": results.get("raw", {}).get("url"),
        "type": results.get("raw", {}).get("type") or results.get("min", {}).get("type"),
        "upstream_id": payload.get("id"),
        "kind": job.get("kind"),
    }
    if not out["min"] and not out["raw"]:
        raise HTTPException(502, "no result URLs in upstream payload")
    return out

@router.get("/jobs/{id}/result/min")
async def job_result_min(id: str):
    job = await store.get(id)
    if not job:
        raise HTTPException(404, "job not found")
    if job["status"] != "completed":
        raise HTTPException(425, "job not completed yet")
    results = (job["payload"].get("jobs") or [{}])[0].get("results") or {}
    url = results.get("min", {}).get("url") or results.get("raw", {}).get("url")
    if not url:
        raise HTTPException(502, "no min/raw url")
    return RedirectResponse(url)

@router.get("/jobs/{id}/result/raw")
async def job_result_raw(id: str):
    job = await store.get(id)
    if not job:
        raise HTTPException(404, "job not found")
    if job["status"] != "completed":
        raise HTTPException(425, "job not completed yet")
    results = (job["payload"].get("jobs") or [{}])[0].get("results") or {}
    url = results.get("raw", {}).get("url") or results.get("min", {}).get("url")
    if not url:
        raise HTTPException(502, "no min/raw url")
    return RedirectResponse(url)

@router.get("/jobs/{id}/result/video")
async def job_result_video(id: str):
    job = await store.get(id)
    if not job: raise HTTPException(404, "job not found")
    if job["status"] != "completed": raise HTTPException(425, "job not completed yet")
    results = (job["payload"].get("jobs") or [{}])[0].get("results") or {}
    url = results.get("raw", {}).get("url")
    if not url: raise HTTPException(502, "no video url")
    return RedirectResponse(url)

