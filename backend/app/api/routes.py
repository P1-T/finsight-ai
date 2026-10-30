import asyncio
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.api.schemas import (
    SUPPORTED_STOCKS,
    HealthResponse,
    ResearchRequest,
    ResearchResponse,
    StockInfo,
    StocksResponse,
)
from app.services.research_service import run_research

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@router.get("/stocks", response_model=StocksResponse)
def stocks() -> StocksResponse:
    return StocksResponse(
        stocks=[
            StockInfo(ticker=ticker, name=name)
            for ticker, name in SUPPORTED_STOCKS.items()
        ]
    )


@router.post("/research", response_model=ResearchResponse)
async def research(body: ResearchRequest) -> ResearchResponse | JSONResponse:
    try:
        result = await run_research(body.ticker)
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Research exceeded its time limit. Please try again.") from exc
    except Exception as exc:
        logger.exception("Unexpected research workflow failure for %s", body.ticker.value)
        raise HTTPException(status_code=502, detail="Research providers or analysis workflow are unavailable.") from exc
    if all(agent.status == "failed" for agent in (result.news, result.technical, result.fundamental)):
        return JSONResponse(status_code=502, content=result.model_dump(mode="json"))
    return result
