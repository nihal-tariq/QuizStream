"""
Video Chat Service Module
-------------------------

This module provides functionality to:
- Generate embeddings using Google's Gemini Embedding API.
- Store/retrieve transcript embeddings in ChromaDB.
- Build conversational context-aware prompts for video Q&A.
- Query Gemini 2.5 Flash for responses using vector search.

Dependencies:
    - google.generativeai
    - chromadb
    - langchain-core
    - langchain-community
    - dotenv
    - app.services.prompt_template (for building chat prompts)

Environment Variables:
    GEMINI_FLASH_KEY : API key for Google Generative AI.
    CHROMA_DB_DIR    : Directory to persist ChromaDB collections.
"""

import os
from typing import List

from dotenv import load_dotenv
import google.generativeai as genai

from chromadb.api.types import Documents
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import Chroma

from app.services.prompt_template import build_chat_prompt


# --------------------------------------------------------------------
# Environment and Client Setup
# --------------------------------------------------------------------

load_dotenv()
api_key = os.getenv("GEMINI_FLASH_KEY")
if not api_key:
    raise ValueError("GEMINI_FLASH_KEY not found in .env")

genai.configure(api_key=api_key)

# Chroma persistence directory
PERSIST_DIR = os.getenv("CHROMA_DB_DIR", "chroma_db")


# --------------------------------------------------------------------
# Embedding Class
# --------------------------------------------------------------------

class GeminiEmbedding(Embeddings):
    """
    Adapter class for generating embeddings with Gemini,
    compatible with LangChain and Chroma vector store.

    Implements:
        - embed_documents: for bulk embeddings of transcripts.
        - embed_query: for single query embedding.
        - name: provides identifier for Chroma.

    Uses Google's embedding model: `models/embedding-001`.
    """

    def name(self) -> str:
        """Return embedding function name for Chroma compatibility."""
        return "gemini_embedding"

    def embed_documents(self, texts: Documents) -> List[List[float]]:
        """
        Generate embeddings for multiple text documents.

        Args:
            texts (Documents): List of input texts.

        Returns:
            List[List[float]]: Embedding vectors for each input.
        """
        embeddings = []
        for text in texts:
            if not isinstance(text, str):
                text = str(text)
            resp = genai.embed_content(
                model="models/embedding-001",
                content=text,
                task_type="retrieval_document"
            )
            embeddings.append(resp["embedding"])
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """
        Generate embedding for a single query string.

        Args:
            text (str): Query text.

        Returns:
            List[float]: Embedding vector.
        """
        if not isinstance(text, str):
            text = str(text)
        resp = genai.embed_content(
            model="models/embedding-001",
            content=text,
            task_type="retrieval_query"
        )
        return resp["embedding"]


# --------------------------------------------------------------------
# Chat Service
# --------------------------------------------------------------------

def chat_with_video(video_title: str, user_query: str, session_history: list) -> str:
    """
    Answer user queries about a specific video using context-aware retrieval.

    Process:
        1. Retrieve relevant transcript chunks from Chroma (MMR search).
        2. Build chat prompt with history, context, and query.
        3. Query Gemini 2.5 Flash model for final response.

    Args:
        video_title (str): Title of the video (used as Chroma collection name).
        user_query (str): User's natural language question.
        session_history (list): List of past conversation turns.

    Returns:
        str: Gemini-generated response text.
    """
    collection_name = video_title.replace(" ", "_")
    embedding = GeminiEmbedding()

    # Initialize Chroma vectorstore with persistence
    vectorstore = Chroma(
        collection_name=collection_name,
        embedding_function=embedding,
        persist_directory=PERSIST_DIR
    )

    # Retriever with Maximal Marginal Relevance (MMR)
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 5, "lambda_mult": 0.5}
    )

    # Retrieve context documents
    retrieved_docs = retriever.invoke(user_query)
    context = "\n\n".join([getattr(d, "page_content", str(d)) for d in retrieved_docs])

    # Construct prompt
    prompt = build_chat_prompt(
        video_title=video_title,
        context=context,
        session_history=session_history,
        user_query=user_query
    )

    # Query Gemini model
    model = genai.GenerativeModel("models/gemini-2.5-flash")
    response = model.generate_content(prompt)

    return getattr(response, "text", str(response))
