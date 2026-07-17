"""RAG-enabled chat module for ENOLA.

Provides conversational Q&A backed by ChromaDB retrieval (knowledge
base + human-validated corrections) and the full taxonomy/glossary
prompt blocks used by the classifier.
"""

from src.chat.rag_chat import ChatResponse, RAGChat

__all__ = ["ChatResponse", "RAGChat"]
