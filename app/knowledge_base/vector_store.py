import json
from typing import List, Dict, Any, Optional
import numpy as np
from app.config import settings
from app.embeddings.sentence_transformer import EmbeddingService

class VectorStoreManager:
    """
    Knowledge base vector store supporting ChromaDB with multi-representation
    indexing for both table documentation and question-SQL examples.
    Includes an in-memory cosine fallback for lightweight testing.
    """
    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = persist_dir or settings.CHROMA_PERSIST_DIRECTORY
        self.embedding_service = EmbeddingService()
        self._chroma_client = None
        self._table_collection = None
        self._examples_collection = None
        self._in_memory_docs: Dict[str, Dict[str, Any]] = {}
        self._in_memory_examples: Dict[str, Dict[str, Any]] = {}

    def _init_chroma(self):
        if self._chroma_client is None:
            try:
                import chromadb
                self._chroma_client = chromadb.PersistentClient(path=self.persist_dir)
                self._table_collection = self._chroma_client.get_or_create_collection(
                    name="table_docs",
                    metadata={"hnsw:space": "cosine"}
                )
                self._examples_collection = self._chroma_client.get_or_create_collection(
                    name="query_examples",
                    metadata={"hnsw:space": "cosine"}
                )
            except Exception:
                self._chroma_client = None

    def upsert_table_documentation(
        self,
        doc_id: str,
        text: str,
        metadata: Dict[str, Any]
    ):
        """
        Stores an embedding entry for table documentation with category metadata.
        Categories: description, connected_tables, table_name, entity
        """
        self._init_chroma()
        embedding = self.embedding_service.embed_query(text)
        # Chroma requires string/int/float/bool in metadata
        flat_meta = {}
        for k, v in metadata.items():
            if isinstance(v, (list, dict)):
                flat_meta[k] = json.dumps(v)
            else:
                flat_meta[k] = str(v) if v is not None else ""

        if self._table_collection is not None:
            self._table_collection.upsert(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[flat_meta]
            )
        else:
            self._in_memory_docs[doc_id] = {
                "text": text,
                "embedding": embedding,
                "metadata": flat_meta
            }

    def upsert_query_example(
        self,
        entry_id: str,
        text: str,
        metadata: Dict[str, Any]
    ):
        """
        Stores an embedding representation for a question-SQL example.
        Representations: initial_question, variation_1/2/3, normalized_question, main_clause, entities
        """
        self._init_chroma()
        embedding = self.embedding_service.embed_query(text)
        flat_meta = {}
        for k, v in metadata.items():
            if isinstance(v, (list, dict)):
                flat_meta[k] = json.dumps(v)
            else:
                flat_meta[k] = str(v) if v is not None else ""

        if self._examples_collection is not None:
            self._examples_collection.upsert(
                ids=[entry_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[flat_meta]
            )
        else:
            self._in_memory_examples[entry_id] = {
                "text": text,
                "embedding": embedding,
                "metadata": flat_meta
            }

    def query_table_docs(
        self,
        query_text: str,
        category_filter: Optional[List[str]] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Queries table documentation with category filter."""
        self._init_chroma()
        query_vec = self.embedding_service.embed_query(query_text)

        if self._table_collection is not None:
            where_clause = None
            if category_filter:
                if len(category_filter) == 1:
                    where_clause = {"category": category_filter[0]}
                else:
                    where_clause = {"category": {"$in": category_filter}}

            results = self._table_collection.query(
                query_embeddings=[query_vec],
                n_results=top_k,
                where=where_clause
            )
            parsed = []
            if results and results["ids"] and len(results["ids"][0]) > 0:
                for idx in range(len(results["ids"][0])):
                    doc_id = results["ids"][0][idx]
                    doc_text = results["documents"][0][idx]
                    meta = results["metadatas"][0][idx]
                    dist = results["distances"][0][idx] if "distances" in results and results["distances"] else 0.0
                    # Convert cosine distance to paper similarity: Sim = (cos_sim + 1) / 2
                    # Chroma cosine distance is (1 - cos_sim)
                    cos_sim = 1.0 - dist
                    paper_sim = (cos_sim + 1.0) / 2.0
                    parsed.append({
                        "id": doc_id,
                        "text": doc_text,
                        "metadata": meta,
                        "similarity": paper_sim
                    })
            return parsed
        else:
            # In-memory search fallback
            scored = []
            for doc_id, data in self._in_memory_docs.items():
                cat = data["metadata"].get("category", "")
                if category_filter and cat not in category_filter:
                    continue
                sim = EmbeddingService.paper_similarity(query_vec, data["embedding"])
                scored.append({
                    "id": doc_id,
                    "text": data["text"],
                    "metadata": data["metadata"],
                    "similarity": sim
                })
            scored.sort(key=lambda x: x["similarity"], reverse=True)
            return scored[:top_k]

    def query_examples(
        self,
        query_text: str,
        representation_filter: Optional[List[str]] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Queries question-SQL examples with representation filter."""
        self._init_chroma()
        query_vec = self.embedding_service.embed_query(query_text)

        if self._examples_collection is not None:
            where_clause = None
            if representation_filter:
                if len(representation_filter) == 1:
                    where_clause = {"representation_type": representation_filter[0]}
                else:
                    where_clause = {"representation_type": {"$in": representation_filter}}

            results = self._examples_collection.query(
                query_embeddings=[query_vec],
                n_results=top_k,
                where=where_clause
            )
            parsed = []
            if results and results["ids"] and len(results["ids"][0]) > 0:
                for idx in range(len(results["ids"][0])):
                    entry_id = results["ids"][0][idx]
                    doc_text = results["documents"][0][idx]
                    meta = results["metadatas"][0][idx]
                    dist = results["distances"][0][idx] if "distances" in results and results["distances"] else 0.0
                    cos_sim = 1.0 - dist
                    paper_sim = (cos_sim + 1.0) / 2.0
                    parsed.append({
                        "id": entry_id,
                        "text": doc_text,
                        "metadata": meta,
                        "similarity": paper_sim
                    })
            return parsed
        else:
            scored = []
            for entry_id, data in self._in_memory_examples.items():
                rep = data["metadata"].get("representation_type", "")
                if representation_filter and rep not in representation_filter:
                    continue
                sim = EmbeddingService.paper_similarity(query_vec, data["embedding"])
                scored.append({
                    "id": entry_id,
                    "text": data["text"],
                    "metadata": data["metadata"],
                    "similarity": sim
                })
            scored.sort(key=lambda x: x["similarity"], reverse=True)
            return scored[:top_k]
