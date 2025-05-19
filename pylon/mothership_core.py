from .immortal import settings
from .adept import output_messages
import structlog
from langchain_experimental.text_splitter import SemanticChunker
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import OllamaEmbeddings
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
#from langchain.chains.llm import LLMChain
#from langchain.chains.combine_documents.stuff import StuffDocumentsChain
#from langchain.chains import RetrievalQA
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain_core.documents import Document
from dataclasses import dataclass
from typing import List, Any
from datetime import datetime
import warnings
import logging
from langchain.schema import BaseRetriever
from pydantic import BaseModel

# Minimal wrapper to make gateway compatible with LangChain
class QdrantRetriever(BaseRetriever, BaseModel):
    qdrant: Any
    embedder: Any

    def get_relevant_documents(self, query: str) -> List[Document]:
        vector = self.embedder.embed_query(query)
        results = self.qdrant.get_relevant_documents(vector, query)
        return [Document(page_content=hit.payload[settings.index_field]) for hit in results]

# Embedder factory as an attempt to support multiple embedders
class EmbedderFactory:
    def __init__(self):
        self._logger = None
        logging.getLogger("pdfminer").setLevel(logging.ERROR)

    def get_embedder(self, embedder_name):
        if not embedder_name:
            return None
        
        if embedder_name == settings.embedder_ollama:
            return OllamaEmbeddings(model=settings.model_name, base_url=settings.base_url)
        
        if embedder_name == settings.embedder_huggingface:
            return HuggingFaceEmbeddings(model_name=settings.embedder_model_name)

# The reasoning class to hold RAG logic
class OllamaGateway:

    def __init__(self):
        self._logger = None
        self._embedder_factory = None
        self._embedder = None
        self._splitter = None
        self._llm = None
        logging.getLogger("pdfminer").setLevel(logging.ERROR)

    def initialize_client(self):
        self._logger = structlog.get_logger()
        self._embedder_factory = EmbedderFactory()
        self._embedder = self._embedder_factory.get_embedder(settings.current_embedder_name)
        self._splitter = SemanticChunker(self._embedder)
        self._llm = OllamaLLM(model=settings.model_name, base_url=settings.base_url)

    # the usual getters
    def get_embedder(self):
        return self._embedder

    def get_splitter(self):
        return self._splitter

    def get_llm(self):
        return self._llm

    # Common methods
    def split_into_chunks(self, documents):
        try:
            if not documents:
                return None
            if not self._splitter:
                self.initialize_client()
            # Execute the document split into chunks
            with warnings.catch_warnings(): # because of the stupid "tfs_z" warning
                warnings.simplefilter("ignore")
                return self._splitter.split_documents(documents)
        except Exception as e:
            self._logger.error(output_messages.CHUNKER_DONE, error=str(e))
            raise

    def generate_embeddings(self, texts):
        try:
            if not texts:
                return None
            if not self._embedder:
                self.initialize_client()
            return self._embedder.embed_documents(texts)
        except Exception as e:
            self._logger.error(output_messages.EMBEDDER_EXCEPTION, error=str(e))
            raise
    
    def get_vectors(self, documents):
        try:
            if not documents:
                return None
            if not self._embedder:
                self.initialize_client()
            return self._embedder.embed_documents(documents)
        except Exception as e:
            self._logger.error(output_messages.EMBEDDER_EXCEPTION, error=str(e))
            raise

    # chained questions functions
    def get_retriever(self, qdrant):
        if not qdrant or not self._embedder:
            return None
        return QdrantRetriever(qdrant=qdrant, embedder=self._embedder)

    def get_prompt_template(self):
        return f"""
        {settings.prompt_rules} \n
        Context: \n
        {{context}} \n
        Question: \n
        {{input}} \n
        Answer:"""

    def build_qa_chain(self, retriever, prompt_template):
        """Builds a RetrievalQA chain with Ollama and prompt template."""
        if not self._llm:
            self.initialize_client()

        prompt = PromptTemplate.from_template(prompt_template)
        self._logger.error("[Mothership] DEBUG PROMPT ", prompt=prompt)
        #llm_chain = LLMChain(llm=self._llm, prompt=prompt)
        combine_documents_chain = create_stuff_documents_chain(self._llm, prompt)

        qa_chain = create_retrieval_chain(retriever, combine_documents_chain)

        return qa_chain

    def ask_question(self, question, qdrant):
        if not self._llm or not self._embedder:
            self.initialize_client()
        # Build retriever with inited embedder for qdrant
        retriever = self.get_retriever(qdrant=qdrant)
        if not retriever:
            raise ValueError("Retriever could not be initialized")
        # Build QA chain using custom prompt
        prompt_template = self.get_prompt_template()

        qa_chain = self.build_qa_chain(retriever, prompt_template=prompt_template)

        # Run chain
        try:
            result = qa_chain.invoke({"input": question})
        except Exception as e:
            self._logger.error("[Mothership] DEBUG ", error=str(e))
        self._logger.error("[Mothership] DEBUG ", result=result)

        context_chunks = [doc.page_content for doc in result.get("context", [])]
        self._logger.error("[Mothership] DEBUG ", context_chunks=context_chunks)

        answer = result.get("answer", "").strip();
        self._logger.error("[Mothership] DEBUG ", answer=answer)

        return {
            "answer": answer,
            "context_chunks": context_chunks,
            "model": settings.model_name,
            "timestamp": datetime.utcnow()
        }

    # single shot question functions
    def generate_query_vector(self, query_text):
        return self._splitter_embedder.embed_query(query_text)

    def build_augmented_prompt(self, question: str, chunks: List[str]) -> str:
        """Build context-aware prompt"""
        # Step 3: Combine document chunks into context string
        #context = "\n".join([doc.page_content for doc in chunks if doc.page_content.strip()])
        context = "\n".join([doc.page_content if hasattr(doc, "page_content") else doc for doc in chunks if str(doc).strip()])

        # Step 4: Build prompt manually
        prompt = f"""
        {settings.prompt_rules} \n
        Context: \n
        {context} \n
        Question: \n
        {question} \n
        Answer:"""

        return prompt

    def ask_single_question(self, question: str, qdrant):
        try:
            # Step 1: Get vector
            query_vector = self.generate_query_vector(question)

            # Step 2: Get relevant documents using Qdrant
            results = qdrant.get_relevant_documents(query_vector, question)
            relevant_docs = [Document(page_content=hit.payload[settings.index_field]) for hit in results]

            # Step 3: Build prompt from retrieved context
            prompt = self.build_augmented_prompt(question, relevant_docs)

            # Step 4: Generate answer
            response = self.get_llm().invoke(prompt)

            return {
                "answer": response.strip(),
                "answer_context": query_vector,
                "context_chunks": relevant_docs,
                "model": settings.model_name,
                "timestamp": datetime.utcnow()
            }

        except Exception as e:
            self._logger.error(output_messages.API_QUESTION_KO, error=str(e))
            raise
