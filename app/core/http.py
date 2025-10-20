import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.config import settings

DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)

def hf_headers() -> dict[str, str]:
    return {
        "hf-api-key": settings.HIGGSFIELD_API_KEY,
        "hf-secret": settings.HIGGSFIELD_API_SECRET,
        "Content-Type": "application/json",
    }

_client = httpx.AsyncClient(http2=True, timeout=DEFAULT_TIMEOUT)

@retry(
    reraise=True,
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
    retry=retry_if_exception_type((httpx.ReadTimeout, httpx.ConnectError, httpx.HTTPStatusError)),
)
async def hf_post(path: str, json: dict) -> httpx.Response:
    url = f"{settings.HF_PLATFORM_BASE}{path}"
    res = await _client.post(url, headers=hf_headers(), json=json)
    # If it fails, include body in the exception for easier debugging
    try:
        res.raise_for_status()
    except httpx.HTTPStatusError as e:
        body = None
        try:
            body = res.text
        except Exception:
            pass
        raise httpx.HTTPStatusError(
            f"{e} :: body={body}", request=e.request, response=e.response
        )
    return res

async def hf_get(path: str) -> httpx.Response:
    url = f"{settings.HF_PLATFORM_BASE}{path}"
    res = await _client.get(url, headers=hf_headers())
    res.raise_for_status()
    return res
