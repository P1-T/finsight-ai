import asyncio
import json
import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.api.schemas import ChatRequest, CompanyIdentity, CompanySearchResponse, HealthResponse
from app.config import get_settings
from app.graph.chat_graph import run_chat_graph
from app.providers.company_directory import company_directory
from app.utils.errors import AgentError

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@router.get("/companies/search", response_model=CompanySearchResponse)
def search_companies(q: str = Query(min_length=2, max_length=80)) -> CompanySearchResponse:
    try:
        matches = company_directory.search(q, limit=8)
    except Exception as exc:
        logger.warning("Company autocomplete lookup failed: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Company search is temporarily unavailable.") from exc
    return CompanySearchResponse(companies=[CompanyIdentity(ticker=item.ticker, name=item.name, exchange=item.exchange) for item in matches])


@router.post("/chat/stream")
async def chat_stream(body: ChatRequest) -> StreamingResponse:
    """Stream progress, a typed research response, and its text representation to AI SDK UI."""
    async def events():
        message_id, text_id = str(uuid4()), str(uuid4())

        def emit(part: dict) -> str:
            return f"data: {json.dumps(part, separators=(',', ':'), default=str)}\n\n"

        yield emit({"type": "start", "messageId": message_id})
        yield emit({"type": "data-research-stage", "data": {"stage": "planning", "label": "Understanding your question"}})
        settings = get_settings()
        graph_task: asyncio.Task | None = None
        try:
            async with asyncio.timeout(settings.research_timeout_seconds):
                progress_queue: asyncio.Queue[dict] = asyncio.Queue()
                graph_task = asyncio.create_task(run_chat_graph(body, progress_queue))
                while not graph_task.done() or not progress_queue.empty():
                    try:
                        progress = await asyncio.wait_for(progress_queue.get(), timeout=0.15)
                    except TimeoutError:
                        continue
                    event_type = progress.get("event")
                    if event_type == "plan":
                        yield emit({"type": "data-research-stage", "data": {"stage": "research", "label": "Gathering selected sources" if progress["tool_count"] else "Preparing a general answer"}})
                    elif event_type == "layout":
                        yield emit({"type": "data-research-layout", "data": {"template": progress["template"], "components": progress["components"]}})
                    elif event_type == "stage":
                        yield emit({"type": "data-research-stage", "data": {"stage": progress["stage"], "label": progress["label"]}})
                    elif event_type == "tool_status":
                        yield emit({"type": "data-tool-status", "data": {"tool": progress["tool"], "status": progress["status"], "detail": progress.get("detail")}})
                    elif event_type == "final_response":
                        yield emit({"type": "data-research-response", "data": progress["response"]})
                        yield emit({"type": "text-start", "id": text_id})
                        yield emit({"type": "text-delta", "id": text_id, "delta": progress["answer"]})
                        yield emit({"type": "text-end", "id": text_id})
                await graph_task
            yield emit({"type": "finish"})
        except TimeoutError:
            if graph_task and not graph_task.done():
                graph_task.cancel()
            logger.warning("Chat research request timed out")
            yield emit({"type": "error", "errorText": "This request took too long. Try narrowing the research question."})
            yield emit({"type": "finish"})
        except AgentError as exc:
            if graph_task and not graph_task.done():
                graph_task.cancel()
            logger.warning("Claude request could not be completed: %s", str(exc))
            yield emit({"type": "error", "errorText": str(exc)})
            yield emit({"type": "finish"})
        except Exception:
            if graph_task and not graph_task.done():
                graph_task.cancel()
            logger.exception("Chat workflow failed")
            yield emit({"type": "error", "errorText": "The research workflow is temporarily unavailable. Please try again."})
            yield emit({"type": "finish"})
        finally:
            if graph_task and not graph_task.done():
                graph_task.cancel()
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "Connection": "keep-alive", "x-vercel-ai-ui-message-stream": "v1"},
    )
