from fastapi import FastAPI, File, Request, HTTPException, Depends, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel, Field
import httpx
import structlog
from typing import List
from datetime import datetime
import time
from robotics_bay.robotics_bay_settings import api_settings
from pylon import settings, QdrantGateway, output_messages


# Configure logging
logger = structlog.get_logger()

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)

# Add to Pydantic models
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

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    collections: List[str] = Field(default=[settings.collection_name])

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    services: dict

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

# Add rate limiter error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Initialize Qdrant client
qdrant = QdrantGateway()

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    logger.info(
        output_messages.API_REQUEST_TAG,
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        duration=duration
    )
    
    return response

@app.get("/health", response_model=HealthResponse)
@limiter.limit("5/minute")
async def health_check(request: Request):
    """Health check endpoint"""
    try:
        # Check Qdrant connection
        qdrant_health = qdrant.health_check()
        
        # Check Ollama connection
        async with httpx.AsyncClient(timeout=api_settings.api_timeout) as client:
            ollama_health = await client.get(f"{settings.model_api}{settings.model_health}")
            ollama_health.raise_for_status()
        
        return HealthResponse(
            status=output_messages.API_HEALTHY,
            timestamp=datetime.utcnow(),
            version=api_settings.api_version,
            services={
                "qdrant": output_messages.API_HEALTHY if qdrant_health else output_messages.API_UNHEALTHY,
                "ollama": output_messages.API_HEALTHY if ollama_health.status_code == 200 else output_messages.API_UNHEALTHY
            }
        )
    except Exception as e:
        logger.error(output_messages.API_HEALTH_KO, error=str(e))
        raise HTTPException(status_code=503, detail=output_messages.API_HEALTH_KO_MSG)

@app.post("/ask", response_model=QAResponse)
@limiter.limit("10/minute")
async def ask_question(request: Request,
    data: QARequest
):
    """Ask a question with vector DB context augmentation"""
    try:
        # 1. Get relevant context
        context_chunks = await get_context_chunks(data.question, [data.collection], data.max_context_chunks)
        
        # 2. Build augmented prompt
        prompt = build_augmented_prompt(data.question, context_chunks, data.strict_context)
        
        # 3. Get LLM response
        answer = await get_response(prompt)
        
        return QAResponse(
            answer=answer,
            context_chunks=context_chunks,
            model=settings.model_name,
            timestamp=datetime.utcnow()
        )

    except Exception as e:
        logger.error(output_messages.API_QUESTION_KO, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

async def get_context_chunks(question: str, collections: list[str]) -> List[str]:
    """Retrieve relevant context chunks from vector DB"""
    try:
        logger.debug(f"{output_messages.API_QUESTION} {question}")
        query_vector = generate_embeddings([question])[0]
        all_matches = []

        for collection in collections:
            results = qdrant.search( query_vector=query_vector, collection_name=collection)
            all_matches.extend([hit.payload[settings.index_field] for hit in results if settings.index_field in hit.payload])
        
        return all_matches
    except Exception as e:
        logger.error(f"{output_messages.API_CONTEXT_KO}", error=str(e))
        return []

def build_augmented_prompt(question: str, context_chunks: List[str], strict: bool = True) -> str:
    """Build context-aware prompt"""
    context = "\n\n".join(context_chunks)
    
    prompt = f"""
{api_settings.prompt_rules}

Context:
{context}

Question:
{question}

Answer:"""
    
    logger.debug(f"{output_messages.API_PROMPT} {prompt}")
    return prompt

async def get_response(prompt: str) -> str:
    """Get LLM response with error handling"""
    try:
        async with httpx.AsyncClient(timeout=api_settings.api_timeout) as client:
            response = await client.post(
                f"{settings.model_api}{settings.model_generate}",
                json={
                    "model": settings.model_name,
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            return response.json().get(api_settings.prompt_response_field, output_messages.API_PROMPT_EMPTY_MSG)
            
    except Exception as e:
        logger.error(output_messages.API_PROMPT_EXCEPTION, error=str(e))
        return output_messages.API_PROMPT_EXCEPTION_MSG
    
def generate_embeddings(texts: list[str]) -> list[list[float]]:
    embeddings = []
    total_texts = len(texts)

    logger.info(
        output_messages.API_EMBEDDINGS_START,
        total_texts=total_texts,
        model=settings.model_name
    )

    for idx, text in enumerate(texts):
        try:
            logger.debug(f"{output_messages.API_EMBEDDINGS_STARTED}", index=idx, text_preview=text[:100])

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
                logger.debug(f"{output_messages.API_EMBEDDINGS_OK}", index=idx, embedding_length=len(embedding))
            else:
                # Fallback if embedding isn't returned (simulate or log)
                #embedding = np.random.rand(settings.VECTOR_DIMENSION).tolist()
                #status = output_messages.API_FALLBACK
                logger.warning(f"{output_messages.API_EMBEDDINGS_MISS} {settings.embed_field} ", index=idx, text_preview=text[:100])

            # Calculate progress
            progress = (idx + 1) / total_texts * 100
            logger.info(
                output_messages.API_EMBEDDINGS_PROGRESS,
                current=idx + 1,
                total=total_texts,
                progress=f"{progress:.1f}%",
                status=status
            )

        except Exception as e:
            #embeddings.append(np.random.rand(settings.VECTOR_DIMENSION).tolist())
            logger.error(
                output_messages.API_EMBEDDINGS_PROGRESS,
                error=str(e),
                current=idx + 1,
                total=total_texts
            )

    logger.info(
        output_messages.API_EMBEDDINGS_ENDED,
        succeeded=len([e for e in embeddings if not isinstance(e, list)]),
        failed=len(texts) - len(embeddings),
        total=total_texts
    )

    return embeddings