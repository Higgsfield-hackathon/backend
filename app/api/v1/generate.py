from __future__ import annotations
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Body, Form
from pydantic import BaseModel, Field
from app.core.security import require_bearer
from app.core.config import settings
from app.core.http import hf_post
from app.services.jobs import store, poll_upstream
import base64, httpx, asyncio

router = APIRouter(dependencies=[Depends(require_bearer)])

class T2IRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    aspect_ratio: str = "4:3"
    model: str | None = None

class T2VRequest(BaseModel):
    prompt: str | None = None
    duration: int = Field(5, ge=1, le=10)
    resolution: str = "720"
    aspect_ratio: str = "16:9"
    camera_fixed: bool = False

class I2VUrlRequest(BaseModel):
    image_url: str
    prompt: str | None = None
    duration: int = Field(5, ge=1, le=10)
    enhance_prompt: bool = True

class I2VJsonRequest(BaseModel):
    file: str | None = None
    prompt: str | None = None
    duration: int = Field(5, ge=1, le=10)
    enhance_prompt: bool = True

def drop_empty(v):
    if isinstance(v, dict):
        return {k: drop_empty(x) for k, x in v.items() if x not in (None, "", [], {})}
    if isinstance(v, list):
        return [drop_empty(x) for x in v if x not in (None, "", [], {})]
    return v

@router.post("/t2i")
async def text_to_image(req: T2IRequest):
    if settings.MOCK_MODE:
        local_id = await store.create("mock-t2i", "nano_banana", req.model_dump())
        asyncio.create_task(_mock_complete(local_id))
        return {"id": local_id, "status": "queued", "mock": True}

    # ✅ Nano Banana expects this exact shape; input_images can be an empty list.
    payload = {
        "params": {
            "aspect_ratio": req.aspect_ratio,
            "input_images": [],
            "prompt": req.prompt,
        }
    }

    try:
        res = await hf_post(settings.MODEL_T2I_ENDPOINT, json=payload)
    except httpx.HTTPStatusError as e:
        body = e.response.text if e.response else str(e)
        raise HTTPException(status_code=502, detail=f"Upstream error creating Nano Banana job-set: {body}")

    jobset = res.json()  # includes top-level "id" and "type": "nano_banana"
    local_id = await store.create(jobset["id"], "nano_banana", payload["params"])
    asyncio.create_task(poll_upstream(local_id))
    return {"id": local_id, "status": "queued"}


@router.post("/t2v")
async def text_to_video(req: T2VRequest):
    if settings.MOCK_MODE:
        local_id = await store.create("mock-t2v", "seedance-v1-lite-t2v", req.model_dump())
        asyncio.create_task(_mock_complete(local_id))
        return {"id": local_id, "status": "queued", "mock": True}

    params = {
        "prompt": req.prompt,
        "duration": req.duration,
        "resolution": req.resolution,
        "aspect_ratio": req.aspect_ratio,
        "camera_fixed": req.camera_fixed,
    }
    if req.prompt:  # include only if provided
        params["prompt"] = req.prompt

    payload = {"params": params}

    try:
        # NOTE: this endpoint is on the platform base, same headers as before
        res = await hf_post(settings.MODEL_T2V_ENDPOINT, json=payload)
    except httpx.HTTPStatusError as e:
        body = e.response.text if e.response else str(e)
        raise HTTPException(status_code=502, detail=f"Upstream error creating Seedance job-set: {body}")

    jobset = res.json()  # contains top-level "id"
    local_id = await store.create(jobset["id"], "seedance-v1-lite-t2v", params)
    asyncio.create_task(poll_upstream(local_id))
    return {"id": local_id, "status": "queued"}

@router.post("/i2v")
async def image_to_video_file(
    file: UploadFile = File(...),
    prompt: str | None = Form(None),
    duration: int = Form(5),
    enhance_prompt: bool = Form(True),
):
    if settings.MOCK_MODE:
        local_id = await store.create("mock-i2v", "kling-2-5",
                                      {"prompt": prompt, "duration": duration, "enhance_prompt": enhance_prompt})
        asyncio.create_task(poll_upstream(local_id))
        return {"id": local_id, "status": "queued", "mock": True}

    data = await file.read()
    encoded = base64.b64encode(data).decode("utf-8")

    params = {
        "model": "kling-v2-5-turbo",
        "duration": duration,
        "enhance_prompt": enhance_prompt,
        # ✅ base64 object form
        "input_image": { "type": "base64", "image": encoded },
    }
    if prompt:
        params["prompt"] = prompt

    res = await hf_post(settings.MODEL_I2V_ENDPOINT, json={"params": params})
    jobset = res.json()
    local_id = await store.create(jobset["id"], "kling-2-5", params)
    asyncio.create_task(poll_upstream(local_id))
    return {"id": local_id, "status": "queued"}

@router.post("/i2v/url")
async def image_to_video_url(req: I2VUrlRequest):
    if settings.MOCK_MODE:
        local_id = await store.create("mock-i2v", "kling-2-5", req.model_dump())
        asyncio.create_task(poll_upstream(local_id))
        return {"id": local_id, "status": "queued", "mock": True}

    params = {
        "model": "kling-v2-5-turbo",
        "duration": req.duration,
        "enhance_prompt": req.enhance_prompt,
        # ✅ exact shape expected by upstream
        "input_image": { "type": "image_url", "image_url": req.image_url },
    }
    if req.prompt:
        params["prompt"] = req.prompt

    res = await hf_post(settings.MODEL_I2V_ENDPOINT, json={"params": params})
    jobset = res.json()
    local_id = await store.create(jobset["id"], "kling-2-5", params)
    asyncio.create_task(poll_upstream(local_id))
    return {"id": local_id, "status": "queued"}


async def _mock_complete(local_id: str):
    import asyncio
    from app.services.jobs import store
    await asyncio.sleep(1.0)
    await store.update(local_id, {
        "id": f"mock-{local_id}",
        "jobs": [{"status": "completed", "results": {
            "min": {"url": "https://picsum.photos/seed/mock/640/360", "type": "image"},
            "raw": {"url": "https://picsum.photos/seed/mock/1920/1080", "type": "image"},
        }}]
    })

