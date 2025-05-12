from .immortal import settings
from .adept import output_messages
import structlog
from langchain_experimental.text_splitter import SemanticChunker
from langchain_ollama import OllamaEmbeddings
import warnings
import logging

class OllamaGateway:

    def __init__(self):
        self._embedder = None
        self._chunker = None
        self._logger = None
        logging.getLogger("pdfminer").setLevel(logging.ERROR)

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
        if not self._chunker:
            self.initialize_client()
        pages = None
        #self._logger.info(f"[Mothership Core] Need to chunk {documents}") # for debug only

        # Execute the document split into chunks
        with warnings.catch_warnings(): # because of the stupid "tfs_z" warning
            warnings.simplefilter("ignore")
            pages = self._chunker.split_documents(documents)
        self._logger.info(f"{output_messages.CHUNKER_DONE}", chunks_count=len(pages))
        return pages
            
    def get_vectors(self, documents):
        if not documents:
            return None
        if not self._embedder:
            self.initialize_client()
        vectors = self._embedder.embed_documents(documents) # will generate embeddings?
        return vectors