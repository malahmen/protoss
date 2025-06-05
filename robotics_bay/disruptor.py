from fastapi import FastAPI, File, Request, HTTPException, Depends, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel, Field
import httpx
from typing import List
from datetime import datetime
import time
from robotics_bay.robotics_bay_settings import api_settings
from pylon import settings, output_messages
from pylon.context import ApplicationContext
import os

class ApiService:
    def __init__(self, context: ApplicationContext):
        self.context = context

    async def health_check(self):
        """Health check endpoint"""
        try:
            qdrant_health = self.context.qdrant.health_check()

            async with httpx.AsyncClient(timeout=api_settings.api_timeout) as client:
                ollama_health = await client.get(f"{settings.model_api}{settings.model_health}")
                ollama_health.raise_for_status()

            return {
                "status": output_messages.API_HEALTHY,
                "timestamp": datetime.utcnow(),
                "version": api_settings.api_version,
                "services": {
                    "qdrant": output_messages.API_HEALTHY if qdrant_health else output_messages.API_UNHEALTHY,
                    "ollama": output_messages.API_HEALTHY if ollama_health.status_code == 200 else output_messages.API_UNHEALTHY
                }
            }
        except Exception as e:
            self.context.logger.error(output_messages.API_HEALTH_KO, error=str(e))
            raise HTTPException(status_code=503, detail=output_messages.API_HEALTH_KO_MSG)

    async def handle_question(self, data):
        """Ask chain questions with vector DB context augmentation"""
        try:
            #answer = self.context.ollama.ask_question(data.question, self.context.qdrant)
            answer = self.context.ollama.ask_question(
                question=data.question,
                history=data.history,
                qdrant=self.context.qdrant
            )
        except Exception as e:
            self.context.logger.error(output_messages.API_QUESTION_KO, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
        return answer

    async def handle_question_one_shot(self, data):
        """Ask a one-shot question with vector DB context augmentation"""
        try:
            answer = self.context.ollama.ask_single_question(data.question, self.context.qdrant)
        except Exception as e:
            self.context.logger.error(output_messages.API_QUESTION_KO, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
        return answer

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)

# Initialize FastAPI with middleware
app = FastAPI(
    title=api_settings.api_title,
    description=api_settings.api_description,
    version=api_settings.api_version,
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=[api_settings.allow_origins],
            allow_credentials=api_settings.allow_credentials,
            allow_methods=[api_settings.allow_methods],
            allow_headers=[api_settings.allow_headers],
        )
    ]
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Set up ApplicationContext on startup
@app.on_event("startup")
async def startup_event():
    app.state.context = await ApplicationContext.create()
    app.state.context.logger.info(f"{output_messages.API_INITIALIZATION}")

# Dependency to access context
def get_context(request: Request) -> ApplicationContext:
    return request.app.state.context

# Service initialization
def get_service(request: Request) -> ApiService:
    return ApiService(request.app.state.context)

# Pydantic models
class QARequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    history: List[dict] = Field(default=[]) 
    collection: str = Field(default=settings.collection_name)
    max_context_chunks: int = Field(default=5, ge=1, le=20)
    strict_context: bool = Field(default=True)

class QAResponse(BaseModel):
    answer: str
    context_chunks: List[str]
    model: str
    timestamp: datetime

# Middleware for logging requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    # no DI yet
    context = getattr(request.app.state, "context", None)
    if context and hasattr(context, "logger"):
        context.logger.debug(
            output_messages.API_REQUEST_TAG,
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            duration=duration
        )

    return response

@app.get("/health")
@limiter.limit("5/minute")
async def health_check(request: Request, service: ApiService = Depends(get_service)):
    return await service.health_check()

@app.post("/ask", response_model=QAResponse)
@limiter.limit("10/minute")
async def ask_question(request: Request, data: QARequest, service: ApiService = Depends(get_service)):
    """Ask a question with vector DB context augmentation"""
    return await service.handle_question(data)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Deal with uploaded files and send them to sentry folder for later processing"""
    try:
        upload_dir = api_settings.watch_folder # send the file here to be picked by sentry after
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())

        return {"filename": file.filename, "id": file.filename}
    except Exception as e:
        # output_messages.API_UPLOAD_KO
        context = app.state.context
        context.logger.error("File upload error", error=str(e))
        raise HTTPException(status_code=500, detail="File upload failed")
    
@app.get("/files")
async def list_files():
    upload_dir = api_settings.processed_folder
    try:
        files = []
        for f in os.listdir(upload_dir):
            if os.path.isfile(os.path.join(upload_dir, f)):
                files.append({
                    "name": f,
                    "date": datetime.fromtimestamp(os.path.getmtime(os.path.join(upload_dir, f))).isoformat()
                })
        return files
    except Exception as e:
        # output_messages.API_FILE_LIST_KO
        context = app.state.context
        context.logger.error("File listing error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/sites")
async def list_sites():
    # Replace this with your real gathered site store (Redis, DB, etc.)
    return [
        { "url": "https://example.com/docs", "date": "2023-05-19T11:20:00Z" },
        { "url": "https://knowledge-base.org/articles", "date": "2023-05-17T13:10:00Z" },
        { "url": "https://research-papers.net/ai", "date": "2023-05-14T10:05:00Z" }
    ]