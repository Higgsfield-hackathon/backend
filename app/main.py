import time, logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.core.config import settings
from app.api.v1.router import router as v1_router

app = FastAPI(title="Higgsfield Adapter API", version="0.2.0")

# CORS
origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limit
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Simple request log
logger = logging.getLogger("hf.api")
logging.basicConfig(level=logging.INFO)

@app.middleware("http")
async def log_requests(request, call_next):
    t0 = time.perf_counter()
    resp = await call_next(request)
    dt = (time.perf_counter() - t0) * 1000
    logger.info("%s %s -> %s %.1fms", request.method, request.url.path, resp.status_code, dt)
    return resp

# Routes
app.include_router(v1_router, prefix=settings.API_BASE_V1)

@app.get("/")
def root():
    return {"service": "higgsfield-backend", "docs": "/docs", "mock": settings.MOCK_MODE}
