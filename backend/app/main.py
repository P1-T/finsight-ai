from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings
from app.middleware.rate_limit import RequestRateLimitMiddleware

settings = get_settings()

app = FastAPI(title="FinSight AI", version="0.1.0")
# Add the limiter first so CORS remains the outer middleware and attaches CORS
# headers to 429 responses as well as successful responses.
app.add_middleware(
    RequestRateLimitMiddleware,
    chat_requests_per_minute=settings.chat_requests_per_minute,
    company_search_requests_per_minute=settings.company_search_requests_per_minute,
    trust_proxy_headers=settings.trust_proxy_headers,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["x-vercel-ai-ui-message-stream"],
)
app.include_router(router, prefix="/api")
