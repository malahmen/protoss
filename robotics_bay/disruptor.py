from fastapi import FastAPI, File, Request, HTTPException, Depends, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel, Field
import requests
import httpx
import aiohttp
import json
from typing import List
from datetime import datetime
import time
from robotics_bay.robotics_bay_settings import api_settings
from pylon import settings, output_messages
from pylon.context import ApplicationContext

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
        """Ask a question with vector DB context augmentation"""
        try:
            chunks = await self.get_context_chunks(data.question, [data.collection], data.max_context_chunks)
            prompt = self.build_augmented_prompt(data.question, chunks, data.strict_context)
            answer = await self.get_response(prompt)

            self.context.logger.warning("  ", answer=str(answer["response"]))
        except Exception as e:
            self.context.logger.error(output_messages.API_QUESTION_KO, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
        
        return {
                "answer": answer["response"],
                "answer_context": answer["context"],
                "context_chunks": chunks,
                "model": settings.model_name,
                "timestamp": datetime.utcnow()
            }

    async def get_context_chunks(self, question: str, collections: list[str], max_context_chunks: int) -> List[str]:
        """Retrieve relevant context chunks from vector DB"""
        try:
            self.context.logger.debug(f"{output_messages.API_QUESTION} {question}")
            query_vector = self.generate_embeddings([question])[0]
            all_matches = []

            for collection in collections:
                results = self.context.qdrant.search(query_vector=query_vector, collection=collection)
                all_matches.extend([hit.payload[settings.index_field] for hit in results if settings.index_field in hit.payload])

            return all_matches
        except Exception as e:
            self.context.logger.error(f"{output_messages.API_CONTEXT_KO}", error=str(e))
            return []

    def build_augmented_prompt(self, question: str, chunks: List[str], strict: bool = True) -> str:
        """Build context-aware prompt"""
        prompt_context = "\n\n".join(chunks)

        prompt = f"""
{api_settings.prompt_rules}

Context:
{prompt_context}

Question:
{question}

Answer:"""

        self.context.logger.debug(f"{output_messages.API_PROMPT} {prompt}")
        return prompt

    async def get_response(self, prompt: str) -> str:
        """Get LLM response with error handling"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{settings.model_api}{settings.model_generate}",
                    headers={"Content-Type": "application/json"},
                    data=json.dumps({
                        "model": settings.model_name,
                        "prompt": prompt,
                        "stream": False
                    })
                ) as response:
                    response_text = await response.text()
                    print(response_text)
                    response_json = json.loads(response_text)
                    print(response_json)
                    return response_json
        except Exception as e:
            self.context.logger.error(output_messages.API_PROMPT_EXCEPTION, error=str(e))
            return output_messages.API_PROMPT_EXCEPTION_MSG

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        embeddings = []
        total_texts = len(texts)

        self.context.logger.info(
            output_messages.API_EMBEDDINGS_START,
            total_texts=total_texts,
            model=settings.model_name
        )

        for idx, text in enumerate(texts):
            try:
                self.context.logger.debug(f"{output_messages.API_EMBEDDINGS_STARTED}", index=idx, text_preview=text[:100])

                response = requests.post(f"{settings.model_api}{settings.model_embeddings}", json={
                    "model": settings.model_name,
                    "prompt": text
                })
                response.raise_for_status()
                data = response.json()

                if settings.embed_field in data:
                    embedding = data[settings.embed_field]
                    embeddings.append(embedding)
                    status = output_messages.API_SUCCESS
                    self.context.logger.debug(f"{output_messages.API_EMBEDDINGS_OK}", index=idx, embedding_length=len(embedding))
                else:
                    self.context.logger.warning(f"{output_messages.API_EMBEDDINGS_MISS} {settings.embed_field} ", index=idx, text_preview=text[:100])

                progress = f"{(idx + 1) / total_texts * 100:.1f}%"
                self.context.logger.info(
                    output_messages.API_EMBEDDINGS_PROGRESS,
                    current=idx + 1,
                    total=total_texts,
                    progress=progress,
                    status=status
                )

            except Exception as e:
                self.context.logger.error(
                    output_messages.API_EMBEDDINGS_PROGRESS,
                    error=str(e),
                    current=idx + 1,
                    total=total_texts
                )

        self.context.logger.info(
            output_messages.API_EMBEDDINGS_ENDED,
            succeeded=len(embeddings),
            failed=total_texts - len(embeddings),
            total=total_texts
        )

        return embeddings

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
        context.logger.info(
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