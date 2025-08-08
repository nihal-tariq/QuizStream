# app/services/chatbot.py

import os
from dotenv import load_dotenv
import google.generativeai as genai

from chromadb import PersistentClient
from chromadb.api.types import Documents

from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import Chroma

from app.services.prompt_template import build_chat_prompt

# Load env
load_dotenv()
api_key = os.getenv("EMBEDDING_KEY")
if not api_key:
    raise ValueError("EMBEDDING_KEY not found in .env")

# Configure Gemini (Google) API
genai.configure(api_key=api_key)

# Chroma client (persistent)
persist_directory = "chroma_db"
chroma_client = PersistentClient(path=persist_directory)


class GeminiEmbedding(Embeddings):
    """
    Minimal embedding adapter compatible with:
      - langchain Embeddings interface (embed_documents, embed_query)
      - chromadb expectation for embedding_function.name()
    """

    def name(self) -> str:
        # chromadb calls embedding_function.name() in some code paths
        return "gemini_embedding"

    def embed_documents(self, texts: Documents) -> list[list[float]]:
        """Embed multiple documents (for storing)."""
        embeddings = []
        for text in texts:
            # If text is bytes or not str, ensure conversion
            if not isinstance(text, str):
                text = str(text)
            resp = genai.embed_content(
                model="models/embedding-001",
                content=text,
                task_type="retrieval_document"
            )
            embeddings.append(resp["embedding"])
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        """Embed single query string (for searching)."""
        if not isinstance(text, str):
            text = str(text)
        resp = genai.embed_content(
            model="models/embedding-001",
            content=text,
            task_type="retrieval_query"
        )
        return resp["embedding"]


def chat_with_video(video_title: str, user_query: str, session_history: list):
    """
    Retrieve relevant chunks from Chroma for `video_title`, build prompt
    using session_history and context, then call Gemini to generate an answer.
    """

    collection_name = video_title.replace(" ", "_")
    embedding = GeminiEmbedding()

    # Ensure collection exists. Do NOT pass a bare method to chroma_client.
    # It's okay to create without specifying embedding_function here.
    # chroma_client stores collections metadata and may later require consistent embedding.
    try:
        chroma_client.get_or_create_collection(name=collection_name)
    except Exception:
        # If something unexpected happens, try to create without checking
        chroma_client.create_collection(name=collection_name)

    # Wrap with LangChain's Chroma so we can use .as_retriever(...)
    vectorstore = Chroma(
        client=chroma_client,
        collection_name=collection_name,
        embedding_function=embedding  # pass object that implements embed_documents/embed_query/name
    )

    # Use MMR retriever
    retriever = vectorstore.as_retriever(search_type="mmr", search_kwargs={"k": 5, "lambda_mult": 0.5})

    # Retrieve relevant documents
    retrieved_docs = retriever.invoke(user_query)
    context = "\n\n".join([getattr(d, "page_content", str(d)) for d in retrieved_docs])

    # Build prompt with context + session
    prompt = build_chat_prompt(
        video_title=video_title,
        context=context,
        session_history=session_history,
        user_query=user_query
    )

    # Call Gemini generative model
    model = genai.GenerativeModel("models/gemini-1.5-flash")
    response = model.generate_content(prompt)

    # response may be a complex object; the textual contents are in response.text
    return getattr(response, "text", str(response))
