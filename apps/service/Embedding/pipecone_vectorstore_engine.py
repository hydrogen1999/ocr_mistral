from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document
from pinecone import Pinecone
from apps.config.logging import logger
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter
from typing import List
from apps.config.settings import PINECONE_INDEX_NAME, PINECONE_API_KEY, OPENAI_API_KEY


class PipeconeVectorStoreEngine:
    def __init__(self, index_name: str = None, embedding_model: str = None, **kwargs):
        try:
            self._index_name = index_name or PINECONE_INDEX_NAME
            self.embedding_model = embedding_model or "text-embedding-3-large"

            _client = Pinecone(
                api_key=kwargs.get("pinecone_api_key", None) or PINECONE_API_KEY
            )
            _index = _client.Index(self._index_name)
            _embedding = OpenAIEmbeddings(
                model=self.embedding_model,
                api_key=kwargs.get("openai_api_key", None) or OPENAI_API_KEY,
            )

            self._vector_store = PineconeVectorStore(index=_index, embedding=_embedding)
        except Exception as e:
            logger.error(f"Error initializing PineconeVectorStoreEngine: {e}")
            raise e

    @property
    def vector_store(self):
        return self._vector_store

    @property
    def index_name(self):
        return self._index_name

    async def aadd_documents(self, documents: List[Document], **kwargs):
        return await self.vector_store.aadd_documents(documents, **kwargs)

    async def aembed_content(self, content: str, file_name: str, **kwargs):
        try:
            headers_to_split_on = [
                ("##", "Second-level heading"),
                ("#", "First-level heading"),
                ("###", "Third-level heading"),
            ]  # split on headers
            docs = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
            docs = docs.split_text(content)

            for doc in docs:
                doc.metadata["source"] = file_name

            await self.aadd_documents(documents=docs)
            logger.info(f"Embedding {len(docs)} documents")
        except Exception as e:
            logger.error(f"Error embedding content: {e}")
            raise e
