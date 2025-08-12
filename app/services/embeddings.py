import os
from dotenv import load_dotenv
from chromadb import PersistentClient
from chromadb.utils.embedding_functions import EmbeddingFunction
from langchain.text_splitter import SentenceTransformersTokenTextSplitter
import google.generativeai as genai

# Load environment variables
load_dotenv()
api_key = os.getenv("EMBEDDING_KEY")

if not api_key:
    raise ValueError("GOOGLE_API_KEY is not set in the .env file")

# Configure the generative AI client
genai.configure(api_key=api_key)

# Initialize Chroma persistent client
persist_directory = "chroma_db"
os.makedirs(persist_directory, exist_ok=True)
chroma_client = PersistentClient(path=persist_directory)


class GeminiEmbedding(EmbeddingFunction):
    def __call__(self, texts):
        embeddings = []
        for text in texts:
            response = genai.embed_content(
                model="models/embedding-001",
                content=text,
                task_type="retrieval_document"
            )
            embeddings.append(response["embedding"])
        return embeddings


def embed_and_store_transcript(transcript: str, video_title: str):
    splitter = SentenceTransformersTokenTextSplitter(chunk_size=1000, chunk_overlap=50)
    chunks = splitter.split_text(transcript)

    embedding_fn = GeminiEmbedding()
    collection = chroma_client.get_or_create_collection(
        name=video_title.replace(" ", "_"),
        embedding_function=embedding_fn
    )

    collection.add(
        documents=chunks,
        ids=[f"{video_title}_{i}" for i in range(len(chunks))]
    )
