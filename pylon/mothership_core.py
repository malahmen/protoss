from .immortal import settings
from .adept import output_messages
from .void_ray import suppress_stderr
import structlog
from langchain_experimental.text_splitter import SemanticChunker
from langchain_ollama import OllamaEmbeddings

class OllamaGateway:

    def __init__(self):
        self._embedder = None
        self._chunker = None
        self._logger = None

    def initialize_client(self):
        self._logger = structlog.get_logger()
        self._embedder = OllamaEmbeddings(model=settings.model_name, base_url=settings.base_url)
        self._chunker = SemanticChunker(self._embedder)

    def get_embedder(self):
        return self._embedder

    def get_chunker(self):
        return self._chunker

    def split_into_chunks(self, documents):
        if not documents:
            return None
        pages = None
        self._logger.info(f"[Stalker] Need to chunk {documents}") # for debug only

        # Execute the document split into chunks
        with suppress_stderr(): # because of the stupid "tfs_z" warning
            pages = self._chunker.split_documents(documents)
        self._logger.info(f"{output_messages.CHUNKER_DONE}", chunks_count=len(pages))
        
    def get_vectors(self, documents):
        if not documents:
            return None
        vectors = self._embedder.embed_documents(documents) # will generate embeddings?
        return vectors